from flask import Flask, request, jsonify
from datetime import datetime
from zoneinfo import ZoneInfo
import math
import colorsys
from astral import LocationInfo

app = Flask(__name__)

class CircadianLighting:
    def __init__(self, min_temp=2700, max_temp=6500, min_brightness=1, max_brightness=254):
        self.min_temp = min_temp
        self.max_temp = max_temp
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness

    def calculate(self, elevation):
        ratio = max(0, min((elevation + 6) / 96, 1))
        brightness = self.min_brightness + ratio * (self.max_brightness - self.min_brightness)
        kelvin = self.min_temp + ratio * (self.max_temp - self.min_temp)
        return round(brightness), round(kelvin)

    def kelvin_to_rgb(self, temp_k):
        temp = temp_k / 100
        if temp <= 66:
            r = 255
        else:
            r = 329.698727446 * ((temp - 60) ** -0.1332047592)
            r = max(0, min(r, 255))
        if temp <= 66:
            g = 99.4708025861 * math.log(temp) - 161.1195681661
        else:
            g = 288.1221695283 * ((temp - 60) ** -0.0755148492)
        g = max(0, min(g, 255))
        if temp >= 66:
            b = 255
        elif temp <= 19:
            b = 0
        else:
            b = 138.5177312231 * math.log(temp - 10) - 305.0447927307
        b = max(0, min(b, 255))
        return int(r), int(g), int(b)

    def rgb_to_hsv(self, r, g, b):
        h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        return {
            'hue': round(h * 360, 2),
            'saturation': round(s * 100, 2),
            'value': round(v * 100, 2)
        }

    def hsv_to_hue_format(self, hsv, brightness):
        hue_value = int((hsv['hue'] / 360) * 65535)
        sat_value = int((hsv['saturation'] / 100) * 254)
        bri_value = int(brightness)
        return {
            'hue': hue_value,
            'sat': sat_value,
            'bri': bri_value
        }

def get_solar_elevation(latitude, longitude, tz="Europe/Oslo"):
    city = LocationInfo(latitude=latitude, longitude=longitude)
    now = datetime.now(ZoneInfo(tz))
    return city.solar_elevation(now)

@app.route('/circadian', methods=['GET'])
def circadian():
    latitude = request.args.get('latitude', default=59.6689, type=float)
    longitude = request.args.get('longitude', default=9.6502, type=float)
    tz = request.args.get('tz', default="Europe/Oslo", type=str)

    elevation = get_solar_elevation(latitude, longitude, tz)
    circadian = CircadianLighting()
    brightness, kelvin = circadian.calculate(elevation)
    r, g, b = circadian.kelvin_to_rgb(kelvin)
    hsv = circadian.rgb_to_hsv(r, g, b)
    hue_format = circadian.hsv_to_hue_format(hsv, brightness)

    return jsonify({
        'solhoyde': round(elevation, 2),
        'lysstyrke': brightness,
        'kelvin': kelvin,
        'rgb': {'r': r, 'g': g, 'b': b},
        'hue': hsv['hue'],
        'saturation': hsv['saturation'],
        'value': hsv['value'],
        'hue_format': hue_format,
        'local_time': datetime.now(ZoneInfo(tz)).strftime("%Y-%m-%d %H:%M:%S"),
        'timezone': tz
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
