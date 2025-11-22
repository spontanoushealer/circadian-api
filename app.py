from flask import Flask, request, jsonify
from pysolar.solar import get_altitude
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)

# --- CONSTANTS ---------------------------------------------------------------
MIN_KELVIN = 2500
MAX_KELVIN = 5500


# --- HELPER FUNCTIONS --------------------------------------------------------
def clamp(value, min_val, max_val):
    """Limit a value between min and max."""
    return max(min_val, min(max_val, value))


def solar_kelvin(latitude, longitude, dt):
    """
    Compute Kelvin color temperature based on the sun's altitude.
    Higher sun = cooler white light (5500K).
    Lower sun = warmer light (2500K).
    """
    altitude = get_altitude(latitude, longitude, dt)  # solar altitude in degrees

    # Normalize altitude: -10° -> 0, 60° -> 1
    norm = (altitude + 10) / 70
    norm = clamp(norm, 0, 1)

    # Convert normalized solar factor into Kelvin temperature range
    kelvin = MIN_KELVIN + norm * (MAX_KELVIN - MIN_KELVIN)
    kelvin = clamp(kelvin, MIN_KELVIN, MAX_KELVIN)

    # Normalized values for Homey (0–1)
    kelvin_norm = (kelvin - MIN_KELVIN) / (MAX_KELVIN - MIN_KELVIN)
    kelvin_rev = 1 - kelvin_norm

    return kelvin, kelvin_norm, kelvin_rev


def get_solar_times(latitude, longitude, tz):
    """
    Compute approximate sunrise and sunset by scanning 24 hours and detecting
    when the solar altitude crosses 0 degrees.
    """
    sunrise = None
    sunset = None

    dt = datetime.now(pytz.timezone(tz)).replace(hour=0, minute=0, second=0, microsecond=0)
    prev_alt = get_altitude(latitude, longitude, dt)

    for i in range(1, 1440):  # 1440 minutes in 24 h
        dt_new = dt + timedelta(minutes=i)
        alt = get_altitude(latitude, longitude, dt_new)

        if prev_alt < 0 and alt >= 0 and sunrise is None:
            sunrise = dt_new

        if prev_alt >= 0 and alt < 0 and sunset is None:
            sunset = dt_new

        prev_alt = alt

    return sunrise, sunset


# --- API ENDPOINT ------------------------------------------------------------
@app.route("/circadian", methods=["GET"])
def kelvin_api():
    """
    API Endpoint:
    /kelvin?latitude=..&longitude=..&timezone=Europe/Oslo
    """
    try:
        # --- Validate parameters ---
        lat_raw = request.args.get("latitude")
        lon_raw = request.args.get("longitude")
        tz = request.args.get("timezone")

        if lat_raw is None or lon_raw is None or tz is None:
            return jsonify({
                "error": "Missing parameters. Required: latitude, longitude, timezone",
                "example": "/kelvin?latitude=59.91&longitude=10.75&timezone=Europe/Oslo"
            }), 400

        # Convert input parameters
        latitude = float(lat_raw)
        longitude = float(lon_raw)

        # Compute sunrise and sunset
        sunrise, sunset = get_solar_times(latitude, longitude, tz)

        # Compute current Kelvin
        now = datetime.now(pytz.timezone(tz))
        kelvin, norm, rev = solar_kelvin(latitude, longitude, now)

        # Response WITHOUT table
        return jsonify({
            "latitude": latitude,
            "longitude": longitude,
            "timezone": tz,
            "sunrise": sunrise.isoformat() if sunrise else None,
            "sunset": sunset.isoformat() if sunset else None,
            "current_kelvin": round(kelvin),
            "normalized_kelvin": round(norm, 4),
            "reversed_kelvin": round(rev, 4)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 400


# --- MAIN SERVER --------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)

