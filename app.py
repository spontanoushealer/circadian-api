#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from astral.location import Location
import os

app = Flask(__name__)

# Konfigurasjon
MIN_K = 2000
MAX_K = 6500
MIN_DEG = -6.0
MAX_DEG = 90.0

def parse_dt(dt_text: str | None, tz_name: str) -> datetime:
    tz = ZoneInfo(tz_name)
    if not dt_text:
        return datetime.now(tz)
    if dt_text.endswith("Z"):
        dt = datetime.fromisoformat(dt_text[:-1]).replace(tzinfo=timezone.utc)
    else:
        dt = datetime.fromisoformat(dt_text)
    return dt.astimezone(tz)

def solar_elev(dt_local: datetime, lat: float, lon: float) -> float:
    loc = Location()
    loc.latitude = lat
    loc.longitude = lon
    loc.name = "Site"
    loc.region = "NO"
    return float(loc.solar_elevation(dt_local))

def kelvin_from_elev(elev: float) -> int:
    pct = 0.0 if MAX_DEG == MIN_DEG else (elev - MIN_DEG) / (MAX_DEG - MIN_DEG)
    pct = max(0.0, min(1.0, pct))
    return int(round(MIN_K + pct * (MAX_K - MIN_K)))

def kelvin_to_hue(kelvin: int) -> float:
    # Homey hue: 0 (rød) til 1 (blå). Vi mappe Kelvin til hue:
    # 2000K (varmt) -> hue nær 0.1, 6500K (kaldt) -> hue nær 0.7
    min_hue, max_hue = 0.1, 0.7
    pct = (kelvin - MIN_K) / (MAX_K - MIN_K)
    return round(min_hue + pct * (max_hue - min_hue), 3)

@app.route("/kelvin", methods=["GET"])
def get_kelvin():
    try:
        lat = float(request.args.get("lat"))
        lon = float(request.args.get("lon"))
        tz = request.args.get("tz", "Europe/Oslo")
        dt = request.args.get("dt", None)

        dt_local = parse_dt(dt, tz)
        elev = solar_elev(dt_local, lat, lon)
        kelvin = kelvin_from_elev(elev)
        hue = kelvin_to_hue(kelvin)

        hsv = {
            "hue": hue,
            "saturation": 0.0,  # hvitt lys
            "value": 1.0        # full lysstyrke
        }

        return jsonify({
            "kelvin": kelvin,
            "elevation": round(elev, 3),
            "datetime": dt_local.isoformat(),
            "location": f"{lat},{lon}",
            "hsv": hsv
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
