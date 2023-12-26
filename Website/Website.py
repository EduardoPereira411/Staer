from flask import Flask, render_template, abort, jsonify, request
import sqlite3
from login import USERNAME,PASSWORD
from openSky_Lib import OpenSkyApi

app = Flask(__name__)

@app.route('/')
def map():
    return render_template('map.html')


@app.route('/get_Countries')
def get_Countries():
    connect = sqlite3.connect('FlightRadarTest.db')
    cur = connect.cursor()
    data = cur.execute('''SELECT * FROM countries ORDER BY country ASC''')

    formatted_data = [{'country': row[0]} for row in data]

    connect.close()
    return jsonify(formatted_data)

@app.route('/get_FlightsData')
def get_FlightsData():
    connect = sqlite3.connect('FlightRadarTest.db')
    cur = connect.cursor()

    # Example: Retrieve parameters from the request
    country = request.args.get('origin_country')
    on_ground = request.args.get('on_ground')
    baro_altitude = request.args.get('baro_altitude')

    # Build the SQL query dynamically based on the parameters
    query = '''SELECT * FROM flights 
               WHERE latitude IS NOT NULL 
               AND longitude IS NOT NULL'''

    if country:
        query += f" AND origin_country = '{country}'"

    if on_ground is not None:
        query += f" AND on_ground = {on_ground}"

    if baro_altitude:
        query += f" AND baro_altitude >= {baro_altitude}"

    data = cur.execute(query)

    formatted_data = [{'icao24': row[1], 'latitude': row[7], 'longitude': row[6], 'true_track': row[10]} for row in data]

    connect.close()
    return jsonify(formatted_data)



@app.route('/getPlaneDetails/<icao24>')
def getFlightDetails(icao24):
    connect = sqlite3.connect('FlightRadarTest.db')
    cur = connect.cursor()

    query = '''SELECT * FROM flights 
               WHERE latitude IS NOT NULL 
               AND longitude IS NOT NULL 
               AND icao24 = ?'''

    data = cur.execute(query,(icao24,))
    
    columns = [col[0] for col in cur.description]
    
    formatted_data = [dict(zip(columns, row)) for row in data]
    
    print(formatted_data)
    connect.close()

    return jsonify(formatted_data)

@app.route('/updateAircrafts')
def updateAircrafts():
    try:
        api = OpenSkyApi(USERNAME,PASSWORD)
        flightStates = api.get_states()

        connect = sqlite3.connect('FlightRadarTest.db')
        cur = connect.cursor()

        cur.execute('''
        CREATE TABLE IF NOT EXISTS flights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                icao24 TEXT,
                callsign TEXT,
                origin_country TEXT,
                time_position INTEGER,
                last_contact INTEGER,
                longitude REAL,
                latitude REAL,
                on_ground BOOLEAN,
                velocity REAL,
                true_track REAL,
                vertical_rate REAL,
                sensors TEXT,
                baro_altitude REAL,
                squawk TEXT,
                spi BOOLEAN,
                position_source INTEGER
            )
        ''')

        cur.execute('''CREATE TABLE IF NOT EXISTS countries (
                country TEXT PRIMARY KEY   
        )''')

        # Check if states are received
        if not flightStates or not flightStates.states:
            raise ValueError("No flight states received")
        cur.execute('DELETE FROM flights')
        cur.execute('DELETE FROM countries')
        
        for state_vector in flightStates.states:
            #values = state_vector.dict_values

            # Create a dictionary to map column names to their corresponding values
            state_data = {
                'icao24': state_vector.icao24,
                'callsign': state_vector.callsign,
                'origin_country': state_vector.origin_country,
                'time_position': state_vector.time_position,
                'last_contact': state_vector.last_contact,
                'longitude': state_vector.longitude,
                'latitude': state_vector.latitude,
                'on_ground': state_vector.on_ground,
                'velocity': state_vector.velocity,
                'true_track': state_vector.true_track,
                'vertical_rate': state_vector.vertical_rate,
                'sensors': str(state_vector.sensors),  # Assuming sensors is a list, convert it to a string
                'baro_altitude': state_vector.baro_altitude,
                'squawk': state_vector.squawk,
                'spi': state_vector.spi,
                'position_source': state_vector.position_source
            }

            # Now you can use state_data to insert into your SQLite database or perform other operations
            cur.execute('''
                INSERT INTO flights (
                    icao24, callsign, origin_country, time_position, last_contact,
                    longitude, latitude, on_ground, velocity, true_track,
                    vertical_rate, sensors, baro_altitude, squawk, spi, position_source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', tuple(state_data.values()))

            connect.commit()

        cur.execute('''INSERT OR REPLACE INTO countries (country)
                SELECT DISTINCT origin_country FROM flights
        ''')

        connect.commit()

        data = cur.execute('''SELECT * FROM flights 
                            WHERE latitude IS NOT NULL 
                            AND longitude IS NOT NULL''')

        formatted_data = [{'icao24': row[1], 'latitude': row[7], 'longitude': row[6], 'true_track': row[10]} for row in data]

        connect.close()
        return jsonify(formatted_data)

    except Exception as e:
        error_message = f"Error: {str(e)}"
        print(error_message)
        return jsonify({"status": "error", "message": error_message}), 500

if __name__ == '__main__':
    app.run(debug=True)