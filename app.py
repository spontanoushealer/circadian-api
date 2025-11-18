#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from astral.location import Location
import colorsys
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

def kelvin_to_rgb(kelvin: int) -> tuple:
    # Enkel konvertering fra Kelvin til RGB (tilnærming)
    temp = kelvin / 100.0
    # Rød
    if temp <= 66:
        r = 255
    else:
        r = 329.698727446 * ((temp - 60) ** -0.1332047592)
        r = max(0, min(255, r))
    # Grønn
    if temp <= 66:
        g = 99.4708025861 * (temp) - 161.1195681661
        g = max(0, min(255, g))
    else:
        g = 288.1221695283 * ((temp - 60) ** -0.0755148492)
        g = max(0, min(255, g))
    # Blå
    if temp >= 66:
        b = 255
    elif temp <= 19:
        b = 0
    else:
        b = 138.5177312231 * (temp - 10) ** -0.0546820456
        b = max(0, min(255, b))
    return (r / 255.0, g / 255.0, b / 255.0)

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

        # Konverter Kelvin til RGB og deretter til HSV (0–1)
        r, g, b = kelvin_to_rgb(kelvin)
        h, s, v = colorsys.rgb_to_hsv(r, g, b)

        return jsonify({
            "kelvin": kelvin,
            "elevation": round(elev, 3),
            "datetime": dt_local.isoformat(),
            "location": f"{lat},{lon}",
            "hsv": {"h": round(h, 3), "s": round(s, 3), "v": round(v, 3)}
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
