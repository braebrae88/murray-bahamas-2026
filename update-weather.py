#!/usr/bin/env python3
"""Fetch Nassau weather forecast and update the Bahamas app with per-day weather data."""
import json, urllib.request, re, os

def fetch_weather():
    url = "https://wttr.in/Nassau,Bahamas?format=j1"
    req = urllib.request.Request(url, headers={"User-Agent": "curl/7.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())

def build_weather_js(data):
    days = {}
    for w in data.get("weather", []):
        date = w["date"]  # YYYY-MM-DD
        high_c = w.get("maxtempC", "?")
        low_c = w.get("mintempC", "?")
        # Calculate feels-like from hourly data (midday)
        hourly = w.get("hourly", [])
        feels_like = "?"
        desc = "Sunny"
        humidity = "?"
        for h in hourly:
            if h.get("time") in ("1200", "1500"):
                feels_like = h.get("FeelsLikeC", h.get("HeatIndexC", "?"))
                descs = h.get("weatherDesc", [{}])
                if descs:
                    desc = descs[0].get("value", "Sunny").strip()
                humidity = h.get("humidity", "?")
                break
        sunset = ""
        astro = w.get("astronomy", [{}])
        if astro:
            sunset = astro[0].get("sunset", "5:50 PM")
        days[date] = {
            "high": high_c, "low": low_c, "feels": feels_like,
            "desc": desc, "humidity": humidity, "sunset": sunset
        }
    return days

def update_html(weather_days):
    path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(path, "r") as f:
        html = f.read()
    
    js_data = json.dumps(weather_days)
    
    # Check if WEATHER_DATA already exists
    if "var WEATHER_DATA" in html:
        html = re.sub(r"var WEATHER_DATA\s*=\s*\{[^;]*\};", f"var WEATHER_DATA = {js_data};", html)
    else:
        # Insert before var DAYS
        html = html.replace("var DAYS = [", f"var WEATHER_DATA = {js_data};\n\nvar DAYS = [")
    
    # Update the weather rendering function if not present
    if "function getWeather" not in html:
        weather_fn = """
function getWeather(dayDate) {
  // dayDate like "Feb 3" -> need to match to YYYY-MM-DD
  var monthMap = {Jan:'01',Feb:'02',Mar:'03',Apr:'04',May:'05',Jun:'06',Jul:'07',Aug:'08',Sep:'09',Oct:'10',Nov:'11',Dec:'12'};
  var parts = dayDate.split(' ');
  var mm = monthMap[parts[0]] || '02';
  var dd = parts[1].padStart(2,'0');
  var key = '2026-' + mm + '-' + dd;
  var w = WEATHER_DATA[key];
  if (!w) return '<div class="weather"><div class="temp">26°C</div><div class="wx-info"><strong>Mostly Sunny</strong><br>Feels like 30°C+ with humidity<br>Water: 24°C · Trust us, it\\'s warm! ☀️</div></div>';
  var emoji = '☀️';
  var d = w.desc.toLowerCase();
  if (d.indexOf('rain')>-1||d.indexOf('shower')>-1) emoji = '🌧️';
  else if (d.indexOf('cloud')>-1||d.indexOf('overcast')>-1) emoji = '⛅';
  else if (d.indexOf('thunder')>-1) emoji = '⛈️';
  else if (d.indexOf('partly')>-1) emoji = '🌤️';
  var feelsNote = parseInt(w.feels) > parseInt(w.high) ? ' (Humidity makes it feel even warmer!)' : ' with the tropical humidity';
  return '<div class="weather"><div class="temp">' + w.high + '°C</div><div class="wx-info"><strong>' + emoji + ' ' + w.desc + '</strong><br>High ' + w.high + '°C / Low ' + w.low + '°C · Feels like <strong>' + w.feels + '°C</strong>' + feelsNote + '<br>Water: 24°C · Sunset ' + w.sunset + ' 🌅</div></div>';
}
"""
        html = html.replace("renderDay(DAYS[0]);", weather_fn + "\nrenderDay(DAYS[0]);")
    
    # Update renderDay to use dynamic weather
    if "getWeather(day.date)" not in html:
        html = html.replace(
            """var html = '<div class="section-head"><span class="icon">📍</span><h2>' + esc(day.date) + ' — ' + day.name + '</h2></div>';""",
            """var html = getWeather(day.date) + '<div class="section-head"><span class="icon">📍</span><h2>' + esc(day.date) + ' — ' + day.name + '</h2></div>';"""
        )
    
    with open(path, "w") as f:
        f.write(html)
    print("Updated weather data in HTML")

# Remove the static weather div
def remove_static_weather(path=None):
    if not path:
        path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(path, "r") as f:
        html = f.read()
    # Remove the static weather block in the schedule tab
    static = '''<div class="weather">
      <div class="temp">78°</div>
      <div class="wx-info"><strong>Mostly Sunny All Week</strong><br>Water: 75°F · Sunset ~5:50 PM<br>Pack the sunscreen, it's paradise time ☀️</div>
    </div>'''
    html = html.replace(static, '')
    with open(path, "w") as f:
        f.write(html)

if __name__ == "__main__":
    data = fetch_weather()
    weather = build_weather_js(data)
    remove_static_weather()
    update_html(weather)
    print(json.dumps(weather, indent=2))
