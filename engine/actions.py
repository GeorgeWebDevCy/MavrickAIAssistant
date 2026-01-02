import os
import datetime
import webbrowser
import psutil
import platform

class MavrickActions:
    @staticmethod
    def get_time():
        return datetime.datetime.now().strftime("%H:%M")

    @staticmethod
    def get_date():
        return datetime.datetime.now().strftime("%A, %B %d, %Y")

    @staticmethod
    def open_app(app_name):
        # Basic mapping for Windows
        apps = {
            "browser": "start chrome",
            "notepad": "calc",
            "calculator": "calc",
            "code": "code"
        }
        try:
            os.system(apps.get(app_name.lower(), app_name))
            return f"Opening {app_name}."
        except Exception:
            return f"I could not find {app_name} in my protocols."

    @staticmethod
    def search_web(query):
        url = f"https://www.google.com/search?q={query}"
        webbrowser.open(url)
        return f"Searching the web for {query}."

    @staticmethod
    def run_protocol(protocol_name):
        protocols = {
            "work mode": ["start chrome https://github.com", "code", "calc"],
            "entertainment": ["start chrome https://youtube.com", "calc"],
            "security": ["calc"], # Placeholder for security suite
            "focus": ["calc"]     # Placeholder for focus tools
        }
        
        commands = protocols.get(protocol_name.lower())
        if commands:
            for cmd in commands:
                os.system(cmd)
            return f"Initiating {protocol_name} protocol. All systems authorized."
        return f"Protocol {protocol_name} not found in my database."

    @staticmethod
    def media_control(action):
        # Using PowerShell to simulate key presses for media
        actions = {
            "volume up": "175",
            "volume down": "174",
            "mute": "173",
            "play pause": "179",
            "next": "176",
            "previous": "177"
        }
        key_code = actions.get(action.lower())
        if key_code:
            cmd = f'powershell -Command "$obj = New-Object -ComObject WScript.Shell; $obj.SendKeys([char]{key_code})"'
            os.system(cmd)
            return f"Executing {action}."
        return f"Unknown media action: {action}."

    @staticmethod
    def get_system_stats():
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        battery = psutil.sensors_battery()
        bat_str = f"{battery.percent}%" if battery else "N/A"
        return f"CPU: {cpu}%, RAM: {ram}%, Battery: {bat_str}"

if __name__ == "__main__":
    print(MavrickActions.get_system_stats())
