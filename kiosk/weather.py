import requests
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, NumericProperty
from kivy.clock import Clock
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.logger import Logger
from kivy.uix.gridlayout import GridLayout
import os

class WeatherWidget(BoxLayout):
    city = StringProperty("London")      # kept for compatibility
    api_key = StringProperty("")         # kept for compatibility
    temperature = NumericProperty(0)
    icon_url = StringProperty("")
    temperature_font_size = NumericProperty(120)

    # NEW (coords for Open-Meteo)
    lat = NumericProperty(40.694045)
    lon = NumericProperty(-73.985684)

    def __init__(self, **kwargs):
        super(WeatherWidget, self).__init__(**kwargs)
        
        # IMPORTANT: Make this widget invisible since it's only used for data fetching
        # This prevents a black box from appearing on screen
        self.size_hint = (None, None)
        self.size = (0, 0)
        self.opacity = 0
        
        self.orientation = "horizontal"
        self.padding = 0
        self.spacing = 0

        # Create label but keep it minimal
        self.label = Label(
            text="", 
            size_hint=(None, None), 
            size=(0, 0),
            opacity=0
        )
        
        # Create icon but keep it minimal and invisible
        self.icon = Image(
            size_hint=(None, None),
            size=(0, 0),
            opacity=0
        )

        # Don't add visual elements - this widget is only for data fetching
        # The actual display is handled by app.kv using app.weather_icon_source

        self.fetch_weather()
        Clock.schedule_interval(lambda dt: self.fetch_weather(), 600)

    def on_api_key(self, instance, value):
        Logger.info(f"API Key updated to: {value}")
        self.fetch_weather()

    def on_city(self, instance, value):
        Logger.info(f"City updated to: {value}")
        self.fetch_weather()

    def fetch_weather(self):
        """Fetch current weather data from Open-Meteo using lat/lon."""
        try:
            url = (
                "https://api.open-meteo.com/v1/forecast"
                f"?latitude={self.lat}&longitude={self.lon}&current=temperature_2m,weather_code"
                "&temperature_unit=fahrenheit"
            )
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.temperature = round(float(data["current"]["temperature_2m"]), 1)
                code = int(data["current"]["weather_code"])

                # Minimal icon mapping -> reuse OpenWeather icon CDN for convenience
                code_map = {
                    0:"01d", 1:"02d", 2:"03d", 3:"04d", 45:"50d", 48:"50d",
                    51:"09d", 53:"09d", 55:"09d", 61:"10d", 63:"10d", 65:"10d",
                    71:"13d", 73:"13d", 75:"13d", 95:"11d", 96:"11d", 99:"11d"
                }
                icon_code = code_map.get(code, "03d")
                self.icon_url = f"http://openweathermap.org/img/wn/{icon_code}@2x.png"

                self.update_ui()
            else:
                Logger.error(f"WeatherWidget: Failed to fetch weather data - {response.status_code}")
                self.label.text = "Error"
        except Exception as e:
            Logger.error(f"WeatherWidget: Exception occurred - {e}")
            self.label.text = "Error"

    def update_ui(self):
        """Update internal data and download icon file"""
        self.label.text = f"{self.temperature}°F"

        icon_filename = "weather_icon.png"
        try:
            response = requests.get(self.icon_url, stream=True, timeout=10)
            if response.status_code == 200:
                with open(icon_filename, "wb") as file:
                    for chunk in response.iter_content(1024):
                        file.write(chunk)
                self.icon.source = icon_filename
            else:
                Logger.error(f"WeatherWidget: Failed to fetch weather icon - {response.status_code}")
                self.icon.source = ""
        except Exception as e:
            Logger.error(f"WeatherWidget: Exception occurred while fetching icon - {e}")
            self.icon.source = ""

    def update_temp_size(self, *args):
        # Not needed since widget is invisible, but keep for compatibility
        pass
