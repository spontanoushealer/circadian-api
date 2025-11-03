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

    return jsonify({
        'brightness': brightness,
        'color_temp_mired': mired,
        'kelvin': kelvin,
        'local_time': now.strftime("%Y-%m-%d %H:%M:%S")
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
