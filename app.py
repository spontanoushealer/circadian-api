import os
from flask import Flask, request, jsonify
from datetime import datetime
import pytz
from pysolar.solar import get_altitude
import math

app = Flask(__name__)

MIN_KELVIN = 2500
MAX_KELVIN = 5500

# -------------------------------
# FUNCTIONS (same as before)
# -------------------------------
def kelvin_to_rgb(kelvin):
    temp = kelvin / 100
    if temp <= 66:
        red = 255
        green = 99.4708025861 * math.log(temp) - 161.1195681661
        green = max(0, min(255, green))
        if temp <= 19:
            blue = 0
        else:
            blue = 138.5177312231 * math.log(temp - 10) - 305.0447927307
            blue = max(0, min(255, blue))
    else:
        red = 329.698727446 * ((temp - 60) ** -0.1332047592)
        green = 288.1221695283 * ((temp - 60) ** -0.0755148492)
        blue = 255
        red = max(0, min(255, red))
        green = max(0, min(255, green))
    return int(red), int(green), int(blue)

def rgb_to_hsv(r, g, b):
    r_, g_, b_ = r / 255, g / 255, b / 255
    mx, mn = max(r_, g_, b_), min(r_, g_, b_)
    diff = mx - mn
    if diff == 0:
        h = 0
    elif mx == r_:
        h = (60 * ((g_ - b_) / diff) + 360) % 360
    elif mx == g_:
        h = (60 * ((b_ - r_) / diff) + 120) % 360
    else:
        h = (60 * ((r_ - g_) / diff) + 240) % 360
    s = 0 if mx == 0 else diff / mx
    v = mx
    return h / 360, s, v

def kelvin_from_altitude(altitude):
    if altitude <= -12:
        return MIN_KELVIN
    elif altitude >= 10:
        return MAX_KELVIN
    else:
        return MIN_KELVIN + (MAX_KELVIN - MIN_KELVIN) * ((altitude + 12) / 22)

def rgb_to_hex(r, g, b):
    return "#{:02X}{:02X}{:02X}".format(r, g, b)

# -------------------------------
# REST ENDPOINT
# -------------------------------
@app.route('/circadian', methods=['GET'])
def solarcolor():
    try:
        latitude = float(request.args.get('latitude'))
        longitude = float(request.args.get('longitude'))
        timezone_str = request.args.get('timezone')
        if not timezone_str:
            return jsonify({"error": "Missing timezone parameter"}), 400
    except Exception:
        return jsonify({"error": "Invalid input parameters"}), 400

    tz = pytz.timezone(timezone_str)
    now = datetime.now(tz)
    altitude = get_altitude(latitude, longitude, now)
    kelvin = kelvin_from_altitude(altitude)
    r, g, b = kelvin_to_rgb(kelvin)
    h, s, v = rgb_to_hsv(r, g, b)
    hex_color = rgb_to_hex(r, g, b)

    return jsonify({
        "kelvin": round(kelvin, 2),
        "hue": round(h, 3),
        "saturation": round(s, 3),
        "value": round(v, 3),
        "rgb": {"r": r, "g": g, "b": b},
        "hex": hex_color,
        "solar_altitude": round(altitude, 2)
    })

# -------------------------------
# RUN ON RENDER
# -------------------------------
if __name__ == '__main__':
    # Render sets the port in the PORT environment variable
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
