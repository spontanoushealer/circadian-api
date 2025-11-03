from flask import Flask, jsonify
from datetime import datetime
import math
import os

app = Flask(__name__)

def circadian_value():
    now = datetime.now()
    hour = now.hour + now.minute / 60
    brightness = int((math.sin((hour - 6) / 12 * math.pi) + 1) / 2 * 100)
    color_temp = int(2700 + (brightness / 100) * (6500 - 2700))
    return {'brightness': brightness, 'color_temp': color_temp}

@app.route('/circadian', methods=['GET'])
def get_value():
    return jsonify(circadian_value())

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
