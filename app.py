from flask import Flask, jsonify
from datetime import datetime
from zoneinfo import ZoneInfo
import math
import os

app = Flask(__name__)

@app.route('/circadian', methods=['GET'])
def get_value():
    now = datetime.now(ZoneInfo("Europe/Oslo"))
    hour = now.hour + now.minute / 60

    # Lysstyrke for Hue (0–254)
    brightness = int((math.sin((hour - 6) / 12 * math.pi) + 1) / 2 * 254)

    # Kelvin (2700–6500), deretter konvertert til mired (153–500)
    kelvin = int(2700 + (brightness / 254) * (6500 - 2700))
    mired = int(1000000 / kelvin)
    mired = max(153, min(mired, 500))  # Begrens til Hue-området

        # Konverter Kelvin til RGB (forenklet formel)
    def kelvin_to_rgb(temp_k):
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

    r, g, b = kelvin_to_rgb(kelvin)
    hex_color = "#{:02X}{:02X}{:02X}".format(r, g, b)

    return jsonify({
        'brightness': brightness,
        'color_temp_mired': mired,
        'kelvin': kelvin,
        'hex_color': hex_color,
        'local_time': now.strftime("%Y-%m-%d %H:%M:%S")
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)



