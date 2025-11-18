# circadian-api
Implementing an easy to use circadian color values for homey bridge. 

Values for hue, saturation and value can be used directly in homey flows. 
Inputs latitude, longitude and timezone (in IANA format) 

Code inspired by https://github.com/claytonjn/hass-circadian_lighting

**Example**: 
curl "https://circadian-api.onrender.com/solar?latitude=59.6689&longitude=9.6500&timezone=Europe/Oslo"
