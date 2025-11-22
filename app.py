
from flask import Flask, request, jsonify
from datetime import datetime
import math
import pytz
from pysolar.solar import get_altitude  # PySolar function for solar elevation

app = Flask(__name__)

# Kelvin range
MIN_KELVIN = 2500
MAX_KELVIN = 5500

def normalize_kelvin_reverse(kelvin, min_k=MIN_KELVIN, max_k=MAX_KELVIN):
    """Normalise Kelvin to 0–1 with reversed scale (higher Kelvin gives lower value)."""
    return (max_k - kelvin) / (max_k - min_k)

def get_kelvin_based_on_sun(latitude, longitude, timezone):
    """Calculate Kelvin based on solar elevation using a curved (sinus) model via PySolar."""
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)

    # Get solar elevation (altitude) from PySolar
    elevation = get_altitude(latitude, longitude, now)

    if elevation <= 0:  # Night
        kelvin = MIN_KELVIN
    else:
        # Curved model: sinus for smoother transition
        kelvin = MIN_KELVIN + (MAX_KELVIN - MIN_KELVIN) * math.sin(math.radians(elevation))
    return kelvin

@app.route("/circadian", methods=["GET"])
def circadian():
    """API endpoint that returns Kelvin and normalised Kelvin."""
    latitude = float(request.args.get("latitude", 59.6689))  # Default: Kongsberg
    longitude = float(request.args.get("longitude", 9.6502))
    timezone = request.args.get("timezone", "Europe/Oslo")

    kelvin = get_kelvin_based_on_sun(latitude, longitude, timezone)
    normalized_kelvin = normalize_kelvin_reverse(kelvin)

    return jsonify({
        "kelvin": round(kelvin, 2),
        "normalized_kelvin": round(normalized_kelvin, 4)
    })

if __name__ == "__main__":
    # Local testing
    app.run(host="0.0.0.0", port=5000)
