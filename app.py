from flask import Flask, jsonify
from datetime import datetime
from zoneinfo import ZoneInfo
import math
import os

app = Flask(__name__)

def circadian_value():
    # Bruk norsk lokal tid
    now = datetime.now(ZoneInfo("Europe/Oslo"))
    hour = now.hour + now.minute / 60

    # Lysstyrke: skaler til Philips Hue (0–254)
    brightness = int((math.sin((hour - 6) / 12 * math.pi) + 1) / 2 * 254)

    # Fargetemperatur: skaler til Hue mired (153–500)
    # Mired = 1.000.000 / Kelvin, så vi simulerer Kelvin først
    kelvin = int(2700 + (brightness / 254) * (6500 - 2700))
    mired = int(1000000 / kelvin)
    mired = max(153, min(mired, 500))  # Begrens til Hue-området

    return {
        'brightness': brightness,
        'color_temp_mired': mired,
        'kelvin': kelvin,
        'local_time': now.strftime("%Y-%m-%d %H:%M:%S")
    }

@app.route('/circadian', methods=['GET'])
def get_value():
    return jsonify(circadian_value())

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
``
