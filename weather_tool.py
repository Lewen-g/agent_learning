import requests

def get_weather(latitude: float, longitude: float) -> str:
    """Return a short natural language weather summary for given coordinates."""
    r = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,wind_speed_10m",
        },
        timeout=10,
    )
    c = r.json().get("current", {})
    temp = c.get("temperature_2m")
    wind = c.get("wind_speed_10m")
    if temp is None:
        return "Weather data unavailable."
    return f"当前气温 {temp}°C，风速 {wind} m/s。"