import requests
from requests.exceptions import RequestException

class WeatherEngine:
    BASE_URL = "https://wttr.in/?format=%C+%t"

    @staticmethod
    def get_weather():
        """
        Fetches the current weather condition and temperature using wttr.in.
        Returns a string, e.g., "Clear +25°C".
        """
        try:
            # Setting a timeout to prevent hanging if the service is slow
            response = requests.get(WeatherEngine.BASE_URL, timeout=5)
            if response.status_code == 200:
                print(f"Weather fetched: {response.text.strip()}")
                return response.text.strip()
            else:
                return "Weather Unavailable"
        except RequestException as e:
            print(f"Weather error: {e}")
            return "Offline"

if __name__ == "__main__":
    print(WeatherEngine.get_weather())
