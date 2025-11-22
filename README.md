# circadian-api
Implementing an easy to use circadian color values for homey bridge. 

NOAA algorithm ensures accurate solar position without external dependencies.
Cosine-eased curve mimics natural circadian light progression (warm edges, cool midday).
Homey compatibility: Normalised values (0–1) for Kelvin and dimming.

Provides one endpoint /circadian → current values.

**Example**: 
Command: curl -X GET "https://circadian-api.onrender.com/circadian?latitude=59.6689&longitude=9.6502&timezone=Europe/Oslo"

Output:
{"dimming_percent":10,"kelvin":2500.0,"kelvin_normalized_reversed":1.0,"max_kelvin":5500.0,"min_kelvin":2500.0,"model":"cosine-eased by solar altitude (NOAA)","sunrise_local":"2025-11-22T08:32+01:00","sunset_local":"2025-11-22T15:42+01:00","threshold_altitude_deg":-0.833,"timestamp_local":"2025-11-22T22:02:07+01:00"}

**Work in progress** :-)

Code inspired by https://github.com/claytonjn/hass-circadian_lighting

