
from flask import Flask, request, jsonify
from datetime import datetime
import math
import pytz
from pysolar.solar import get_altitude
from astral import LocationInfo
from astral.sun import sun

app = Flask(__name__)

# Kelvin range
MIN_KELVIN = 2500
MAX_KELVIN = 5500

def normalize_kelvin_reverse(kelvin, min_k=MIN_KELVIN, max_k=MAX_KELVIN):
    """
    Normalise Kelvin to 0–1 with reversed scale.
    Higher Kelvin -> lower value.
    """
    return (max_k - kelvin) / (max_k - min_k)

def calculate_kelvin(elevation):
    """
    Calculate Kelvin based on solar elevation using sinus curve.
    Elevation <= 0 means night -> minimum Kelvin.
    """
    if elevation <= 0:
        return MIN_KELVIN
    return MIN_KELVIN + (MAX_KELVIN - MIN_KELVIN) * math.sin(math.radians(elevation))

@app.route("/circadian", methods=["GET"])
def circadian():
    """
    API endpoint:
    Input: latitude, longitude, timezone
    Output: Kelvin and reversed normalised Kelvin (0–1)
    """
    latitude = float(request.args.get("latitude", 59.6689))  # Default: Kongsberg
    longitude = float(request.args.get("longitude", 9.6502))
    timezone = request.args.get("timezone", "Europe/Oslo")

    tz = pytz.timezone(timezone)
    now = datetime.now(tz)

    # Step 1: Calculate sunrise and sunset using Astral
    city = LocationInfo(latitude=latitude, longitude=longitude, timezone=timezone)
    s = sun(city.observer, date=now, tzinfo=tz)
    sunrise = s["sunrise"]
    sunset = s["sunset"]

    # Step 2: Determine Kelvin based on time and solar elevation
    if now < sunrise or now > sunset:
        kelvin = MIN_KELVIN  # Night time
    else:
        elevation = get_altitude(latitude, longitude, now)
        kelvin = calculate_kelvin(elevation)

    normalized_kelvin = normalize_kelvin_reverse(kelvin)

    return jsonify({
        "sunrise": sunrise.strftime("%Y-%m-%d %H:%M"),
        "sunset": sunset.strftime("%Y-%m-%d %H:%M"),
        "kelvin": round(kelvin, 2),
        "normalized_kelvin": round(normalized_kelvin, 4)
    })

if __name__ == "__main__":
    # Local testing
    app.run(host="0.0.0.0", port=5000)
