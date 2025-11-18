import os
from flask import Flask, request, jsonify
from astral import LocationInfo
from astral.sun import sun
from astral import Observer
from datetime import datetime
import pytz

app = Flask(__name__)

# Helper: Calculate Kelvin based on solar elevation
def calculate_kelvin(elevation):
    elevation = max(min(elevation, 90), -6)
    min_kelvin = 2000
    max_kelvin = 6500
    kelvin = min_kelvin + ((elevation + 6) / (90 + 6)) * (max_kelvin - min_kelvin)
    return round(kelvin)

# Helper: Convert Kelvin to Homey-compatible HSV
def kelvin_to_homey_hsv(kelvin):
    hue_deg = 240 - ((kelvin - 2000) / (6500 - 2000)) * 240
    hue = hue_deg / 360.0
    saturation = 0.7
    value = 1.0
    return round(hue, 3), saturation, value

@app.route('/solar', methods=['GET'])
def solar_info():
    latitude = request.args.get('latitude', type=float)
    longitude = request.args.get('longitude', type=float)
    timezone = request.args.get('timezone')

    if latitude is None or longitude is None or timezone is None:
        return jsonify({"error": "Missing latitude, longitude or timezone"}), 400

    try:
        tz = pytz.timezone(timezone)
    except pytz.UnknownTimeZoneError:
        return jsonify({"error": "Invalid timezone"}), 400

    now = datetime.now(tz)

    # Use Observer for calculations
    observer = Observer(latitude=latitude, longitude=longitude)
    azimuth = observer.azimuth(now)
    elevation = observer.elevation(now)

    kelvin = calculate_kelvin(elevation)
    hue, saturation, value = kelvin_to_homey_hsv(kelvin)

    return jsonify({
        "azimuth": round(azimuth, 2),
        "elevation": round(elevation, 2),
        "kelvin": kelvin,
        "hue": hue,
        "saturation": saturation,
        "value": value
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
