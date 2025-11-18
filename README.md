# circadian-api
Implementing an easy to use circadian color values for homey bridge. 

**Work in progress** :-)

Values for hue, saturation and value can be used directly in homey flows. 
Inputs latitude, longitude and timezone (in IANA format) 

Code inspired by https://github.com/claytonjn/hass-circadian_lighting

**Example**: 
curl "https://circadian-api.onrender.com/solar?latitude=50&longitude=9.1&timezone=Europe/Oslo"
