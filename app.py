
import os
import math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, Tuple, List, Dict, Any
from flask import Flask, request, jsonify

app = Flask(__name__)

# ---------------- Configuration ----------------
MIN_KELVIN = 2500.0
MAX_KELVIN = 5500.0
# Sunrise/sunset threshold including refraction (~ -0.833°)
SUN_EDGE_ALT_DEG = -0.833

# ---------------- NOAA solar elevation (no external libs) ----------------

def day_of_year(dt: datetime) -> int:
    return int(dt.strftime('%j'))

def fractional_year(dt: datetime) -> float:
    # gamma in radians
    n = day_of_year(dt)
    return 2.0 * math.pi / 365.0 * (n - 1 + (dt.hour - 12) / 24.0)

def equation_of_time_minutes(gamma: float) -> float:
    # NOAA approximation
    return 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )

def declination_radians(gamma: float) -> float:
    return (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.00148 * math.sin(3 * gamma)
    )

def true_solar_time_minutes(dt: datetime, longitude_deg: float, tz_offset_hours: float) -> float:
    gamma = fractional_year(dt)
    eot = equation_of_time_minutes(gamma)
    time_offset = eot + 4.0 * longitude_deg - 60.0 * tz_offset_hours
    return dt.hour * 60.0 + dt.minute + dt.second / 60.0 + time_offset

def hour_angle_degrees(tst_minutes: float) -> float:
    ha = tst_minutes / 4.0 - 180.0
    # normalize to [-180, 180]
    while ha < -180.0:
        ha += 360.0
    while ha > 180.0:
        ha -= 360.0
    return ha

def solar_elevation_degrees(dt: datetime, lat_deg: float, lon_deg: float, tz_offset_hours: float) -> float:
    """
    Solar elevation angle (degrees) using NOAA algorithm + refraction correction.
    dt: timezone-aware local datetime
    tz_offset_hours: dt.utcoffset() converted to hours
    """
    gamma = fractional_year(dt)
    decl = declination_radians(gamma)
    tst = true_solar_time_minutes(dt, lon_deg, tz_offset_hours)
    ha_deg = hour_angle_degrees(tst)
    ha = math.radians(ha_deg)
    lat = math.radians(lat_deg)

    # Solar zenith angle
    cos_zenith = math.sin(lat) * math.sin(decl) + math.cos(lat) * math.cos(decl) * math.cos(ha)
    cos_zenith = max(-1.0, min(1.0, cos_zenith))
    zenith = math.degrees(math.acos(cos_zenith))
    elevation = 90.0 - zenith

    # Atmospheric refraction correction (approx) for elevation > -0.575°
    if elevation > -0.575:
        refraction = (1.02 / math.tan(math.radians(elevation + 10.3 / (elevation + 5.11)))) / 60.0
    else:
        refraction = 0.0
    return elevation + refraction

# ---------------- Sunrise/Sunset + circadian mapping ----------------

def find_sunrise_sunset_for_date(lat: float, lon: float, tz: ZoneInfo, date_local: datetime) -> Tuple[Optional[datetime], Optional[datetime], Optional[float]]:
    """
    Scan the day at 2-minute resolution to find threshold crossings at SUN_EDGE_ALT_DEG.
    Returns local datetimes for sunrise and sunset, and max elevation (deg).
    Linear interpolation within the 2-minute brackets improves accuracy.
    """
    day_start = datetime(date_local.year, date_local.month, date_local.day, 0, 0, tzinfo=tz)
    day_end = day_start + timedelta(days=1)
    step = timedelta(minutes=2)

    t = day_start
    prev_t = t
    tz_offset_hours = tz.utcoffset(t).total_seconds() / 3600.0
    prev_alt = solar_elevation_degrees(t, lat, lon, tz_offset_hours)
    sunrise = None
    sunset = None
    max_alt = -90.0

    while t <= day_end:
        tz_offset_hours = tz.utcoffset(t).total_seconds() / 3600.0
        alt = solar_elevation_degrees(t, lat, lon, tz_offset_hours)
        if alt > max_alt:
            max_alt = alt

        # Rising through threshold -> sunrise
        if prev_alt < SUN_EDGE_ALT_DEG and alt >= SUN_EDGE_ALT_DEG and sunrise is None:
            frac = (SUN_EDGE_ALT_DEG - prev_alt) / (alt - prev_alt + 1e-12)
            sunrise = prev_t + (t - prev_t) * frac

        # Falling through threshold -> sunset
        if prev_alt >= SUN_EDGE_ALT_DEG and alt < SUN_EDGE_ALT_DEG and sunset is None:
            frac = (SUN_EDGE_ALT_DEG - prev_alt) / (alt - prev_alt + 1e-12)
            sunset = prev_t + (t - prev_t) * frac

        prev_t = t
        prev_alt = alt
        t += step

    return sunrise, sunset, (max_alt if max_alt > -90.0 else None)

def cosine_eased_kelvin(alt_now: float, max_alt: float) -> float:
    """
    Kelvin follows a cosine-eased curve of normalized altitude:
    warm (2500K) near edges, cooler (up to 5500K) near midday.
    """
    alt_norm = (alt_now - SUN_EDGE_ALT_DEG) / (max_alt - SUN_EDGE_ALT_DEG)
    alt_norm = max(0.0, min(1.0, alt_norm))
    f = 0.5 * (1.0 - math.cos(math.pi * alt_norm))
    return MIN_KELVIN + (MAX_KELVIN - MIN_KELVIN) * f

def circadian_values(lat: float, lon: float, tzname: str, when_local: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Compute Kelvin, reversed normalized Kelvin (0–1; 1=warmest), and dimming (0–100%) + normalized dimming (0–1).
    """
    tz = ZoneInfo(tzname)
    if when_local is None:
        when_local = datetime.now(tz)

    sr, ss, max_alt = find_sunrise_sunset_for_date(lat, lon, tz, when_local)
    is_day = bool(sr and ss and sr < when_local < ss and max_alt and max_alt > SUN_EDGE_ALT_DEG)

    if not is_day:
        kelvin = MIN_KELVIN
        kelvin_rev_norm = (MAX_KELVIN - kelvin) / (MAX_KELVIN - MIN_KELVIN)  # 1.0 at night (warmest scale)
        dimming_norm = 0.10
        dimming_pct = int(round(dimming_norm * 100))
    else:
        tz_offset_hours = tz.utcoffset(when_local).total_seconds() / 3600.0
        alt_now = solar_elevation_degrees(when_local, lat, lon, tz_offset_hours)
        kelvin = cosine_eased_kelvin(alt_now, max_alt)
        kelvin_rev_norm = (MAX_KELVIN - kelvin) / (MAX_KELVIN - MIN_KELVIN)

        # Dimming: smooth progression (gamma 0.7), highest near max altitude
        alt_norm = (alt_now - SUN_EDGE_ALT_DEG) / (max_alt - SUN_EDGE_ALT_DEG)
        alt_norm = max(0.0, min(1.0, alt_norm))
        dimming_norm = alt_norm ** 0.7
        dimming_pct = int(round(100.0 * dimming_norm))

    return {
        "timestamp_local": when_local.isoformat(timespec="seconds"),
        "sunrise_local": sr.isoformat(timespec="minutes") if sr else None,
        "sunset_local": ss.isoformat(timespec="minutes") if ss else None,
        "kelvin": round(kelvin, 2),
        "kelvin_normalized_reversed": round(kelvin_rev_norm, 6),  # Homey 0–1 (1=warmest)
        "dimming_percent": dimming_pct,                           # 0–100 %
        "dimming_normalized": round(dimming_norm, 6),             # 0–1
        "min_kelvin": MIN_KELVIN,
        "max_kelvin": MAX_KELVIN,
        "model": "cosine-eased by solar altitude (NOAA)",
        "threshold_altitude_deg": SUN_EDGE_ALT_DEG
    }

# ---------------- Flask routes ----------------

@app.get("/circadian")
def circadian_endpoint():
    """
    Query:
      latitude (float), longitude (float), timezone (IANA tz string, e.g., 'Europe/Oslo')
      timestamp (optional; ISO-8601 local time in given timezone, e.g., '2025-11-23T09:00:00')
    """
    try:
        latitude = float(request.args.get("latitude", "").strip())
        longitude = float(request.args.get("longitude", "").strip())
        tzname = request.args.get("timezone", "").strip()
        if not tzname:
            return jsonify({"error": "Missing 'timezone' (IANA name, e.g., Europe/Oslo)"}), 400

        ts = request.args.get("timestamp")
        when_local = None
        if ts:
            # Interpret as local wall time string; attach tz
            when_naive = datetime.fromisoformat(ts)
            when_local = when_naive.replace(tzinfo=ZoneInfo(tzname))

        result = circadian_values(latitude, longitude, tzname, when_local)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.get("/table")
def table_endpoint():
    """
    Produce an hourly table for the next N hours (default 48).
    Query:
      latitude (float), longitude (float), timezone (IANA tz string)
      hours (int, default 48), start (optional ISO-8601 local time)
    """
    try:
        latitude = float(request.args.get("latitude", "").strip())
        longitude = float(request.args.get("longitude", "").strip())
        tzname = request.args.get("timezone", "").strip()
        if not tzname:
            return jsonify({"error": "Missing 'timezone' (IANA name, e.g., Europe/Oslo)"}), 400

        tz = ZoneInfo(tzname)
        hours = int(request.args.get("hours", "48"))
        start_arg = request.args.get("start")
        if start_arg:
            start_local = datetime.fromisoformat(start_arg).replace(tzinfo=tz)
        else:
            start_local = datetime.now(tz)

        rows: List[Dict[str, Any]] = []
        # Precompute sunrise/sunset per day
        sr_today, ss_today, max_today = find_sunrise_sunset_for_date(latitude, longitude, tz, start_local)
        tomorrow = datetime(start_local.year, start_local.month, start_local.day, 0, 0, tzinfo=tz) + timedelta(days=1)
        sr_tom, ss_tom, max_tom = find_sunrise_sunset_for_date(latitude, longitude, tz, tomorrow)

        for h in range(hours):
            when = start_local + timedelta(hours=h)
            if when.date() == start_local.date():
                sr, ss, ma = sr_today, ss_today, max_today
            else:
                sr, ss, ma = sr_tom, ss_tom, max_tom

            tz_offset_hours = tz.utcoffset(when).total_seconds() / 3600.0
            alt_now = solar_elevation_degrees(when, latitude, longitude, tz_offset_hours)
            if sr and ss and sr < when < ss and ma and ma > SUN_EDGE_ALT_DEG:
                kelvin = cosine_eased_kelvin(alt_now, ma)
                kelvin_rev_norm = (MAX_KELVIN - kelvin) / (MAX_KELVIN - MIN_KELVIN)
                alt_norm = (alt_now - SUN_EDGE_ALT_DEG) / (ma - SUN_EDGE_ALT_DEG)
                alt_norm = max(0.0, min(1.0, alt_norm))
                dimming_norm = alt_norm ** 0.7
                dimming_pct = int(round(100.0 * dimming_norm))
            else:
                kelvin = MIN_KELVIN
                kelvin_rev_norm = (MAX_KELVIN - kelvin) / (MAX_KELVIN - MIN_KELVIN)
                dimming_norm = 0.10
                dimming_pct = int(round(100.0 * dimming_norm))

            rows.append({
                "time_local": when.isoformat(timespec="minutes"),
                "kelvin": round(kelvin, 2),
                "kelvin_normalized_reversed": round(kelvin_rev_norm, 6),
                "dimming_percent": dimming_pct,
                "dimming_normalized": round(dimming_norm, 6)
            })

        return jsonify({"timezone": tzname, "latitude": latitude, "longitude": longitude, "rows": rows})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200

# ---------------- Render / local run ----------------
if __name__ == "__main__":
    # Render sets PORT; fallback 10000 for local dev
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
