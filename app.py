from flask import Flask, request, jsonify
from astral import LocationInfo
from astral.sun import sun
from datetime import datetime
import pytz

app = Flask(__name__)

# Helper: Calculate Kelvin based on solar elevation
def calculate_kelvin(elevation):
    """
    Calculate colour temperature (Kelvin) based on solar elevation.
    Inspired by Circadian Lighting logic.
    Elevation is clamped between -6° and 90°.
    """
    elevation = max(min(elevation, 90), -6)
    min_kelvin = 2000
    max_kelvin = 6500
    kelvin = min_kelvin + ((elevation + 6) / (90 + 6)) * (max_kelvin - min_kelvin)
    return round(kelvin)

# Helper: Convert Kelvin to Homey-compatible HSV
def kelvin_to_homey_hsv(kelvin):
    """
    Convert Kelvin to Homey-compatible HSV values.
    Homey expects:
      - Hue: 0.0 to 1.0
      - Saturation: 0.0 to 1.0
      - Value (brightness): 0.0 to 1.0
    """
    # Map Kelvin to Hue (warm = ~0.05, cool = ~0.66)
    hue_deg = 240 - ((kelvin - 2000) / (6500 - 2000)) * 240
    hue = hue_deg / 360.0  # normalise to 0.0 - 1.0
    saturation = 0.7       # fixed saturation for simplicity
    value = 1.0            # full brightness
    return round(hue, 3), saturation, value

@app.route('/solar', methods=['GET'])
def solar_info():
    """
    REST endpoint to calculate solar position and colour values.
    Input: latitude, longitude, timezone as query parameters
    Output: JSON with azimuth, elevation, Kelvin, Hue, Saturation, Value
    """
    latitude = request.args.get('latitude', type=float)
    longitude = request.args.get('longitude', type=float)
    timezone = request.args.get('timezone')

    # Validate input
    if latitude is None or longitude is None or timezone is None:
        return jsonify({"error": "Missing latitude, longitude or timezone"}), 400

    try:
        tz = pytz.timezone(timezone)
    except pytz.UnknownTimeZoneError:
        return jsonify({"error": "Invalid timezone"}), 400

    # Current time in given timezone
    now = datetime.now(tz)

    # Create location and calculate sun position
    location = LocationInfo(latitude=latitude, longitude=longitude)
    s = sun(location.observer, date=now, tzinfo=tz)

    # Calculate azimuth and elevation
    azimuth = location.solar_azimuth(now)
    elevation = location.solar_elevation(now)

    # Calculate Kelvin and Homey HSV
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
    app.run(debug=True)
