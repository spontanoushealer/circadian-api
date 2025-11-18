from flask import Flask, request, jsonify
from astral import Observer
from astral.sun import zenith
from datetime import datetime
import pytz
import colorsys

# Constants
MIN_KELVIN = 2500
MAX_KELVIN = 6500

app = Flask(__name__)

def calculate_circadian_angle(observer, dt):
    z = zenith(observer, dt)
    return (z - 90) * -1

def calculate_percent(angle):
    percent = angle / 180.0
    return max(0.0, min(1.0, percent))

def calculate_kelvin(percent):
    return round(MIN_KELVIN + (MAX_KELVIN - MIN_KELVIN) * (percent ** 0.5))

def kelvin_to_rgb(kelvin):
    temp = kelvin / 100.0
    if temp <= 66:
        red = 255
    else:
        red = 329.698727446 * ((temp - 60) ** -0.1332047592)
        red = max(0, min(255, red))
    if temp <= 66:
        green = 99.4708025861 * (temp ** 0.1332047592)
    else:
        green = 288.1221695283 * ((temp - 60) ** -0.0755148492)
    green = max(0, min(255, green))
    if temp >= 66:
        blue = 255
    elif temp <= 19:
        blue = 0
    else:
        blue = 138.5177312231 * ((temp - 10) ** 0.055)
    blue = max(0, min(255, blue))
    return round(red), round(green), round(blue)

def rgb_to_hsv_normalized(r, g, b):
    r_norm, g_norm, b_norm = r / 255.0, g / 255.0, b / 255.0
    h, s, v = colorsys.rgb_to_hsv(r_norm, g_norm, b_norm)
    return round(h, 4), round(s, 4), round(v, 4)

@app.route('/circadian', methods=['GET'])
def circadian():
    try:
        latitude = float(request.args.get('latitude'))
        longitude = float(request.args.get('longitude'))
        timezone = request.args.get('timezone')

        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        observer = Observer(latitude=latitude, longitude=longitude)

        angle = calculate_circadian_angle(observer, now)
        percent = calculate_percent(angle)
        kelvin = calculate_kelvin(percent)

        r, g, b = kelvin_to_rgb(kelvin)
        h, s, v = rgb_to_hsv_normalized(r, g, b)

        return jsonify({
            "kelvin": kelvin,
            "hue": h,
            "saturation": s,
            "value": v
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
