from flask import Flask, request, jsonify
from datetime import datetime
from zoneinfo import ZoneInfo
import math
import colorsys
from astral import LocationInfo
from astral.sun import elevation
from astral.location import Observer


app = Flask(__name__)

class CircadianLighting:
    def __init__(self, min_temp=2700, max_temp=6500):
        self.min_temp = min_temp
        self.max_temp = max_temp

    def calculate_kelvin(self, elevation):
        # Interpoler mellom min og maks kelvin basert på solens elevation
        # Elevation: -6 (natt) til 90 (sol rett over)
        ratio = max(0, min((elevation + 6) / 96, 1))
        kelvin = self.min_temp + ratio * (self.max_temp - self.min_temp)
        return round(kelvin)

    def kelvin_to_rgb(self, temp_k):
        temp = temp_k / 100
        # Rød
        if temp <= 66:
            r = 255
        else:
            r = 329.698727446 * ((temp - 60) ** -0.1332047592)
            r = max(0, min(r, 255))
        # Grønn
        if temp <= 66:
            g = 99.4708025861 * math.log(temp) - 161.1195681661
        else:
            g = 288.1221695283 * ((temp - 60) ** -0.0755148492)
        g = max(0, min(g, 255))
        # Blå
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


def get_solar_elevation(latitude, longitude, tz):
    now = datetime.now(ZoneInfo(tz))
    observer = Observer(latitude=latitude, longitude=longitude)
    return elevation(observer, now)


@app.route('/circadian', methods=['GET'])
def circadian():
    latitude = request.args.get('latitude', type=float)
    longitude = request.args.get('longitude', type=float)
    timezone = request.args.get('timezone', type=str)

    # Sjekk at alle parametre er satt
    if latitude is None or longitude is None or timezone is None:
        return jsonify({'error': 'latitude, longitude og timezone må oppgis'}), 400

    elevation = get_solar_elevation(latitude, longitude, timezone)
    circadian = CircadianLighting()
    kelvin = circadian.calculate_kelvin(elevation)
    r, g, b = circadian.kelvin_to_rgb(kelvin)
    hsv = circadian.rgb_to_hsv(r, g, b)

    return jsonify({
        'hue': hsv['hue'],
        'saturation': hsv['saturation'],
        'value': hsv['value']
    })

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

