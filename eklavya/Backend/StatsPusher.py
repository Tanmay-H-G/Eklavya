"""
Backend/StatsPusher.py
Background thread to push system statistics (CPU, RAM, Battery) to the Eel frontend.
"""

import psutil
import time
import eel

def get_system_stats():
    """Fetch current system performance data."""
    try:
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        
        # Battery stats
        battery = psutil.sensors_battery()
        bat_percent = battery.percent if battery else None
        plugged = battery.power_plugged if battery else False
        
        return {
            'cpu': cpu,
            'ram': ram,
            'battery': bat_percent,
            'plugged': plugged
        }
    except Exception as e:
        print(f"[Stats] Error fetching stats: {e}")
        return {}

def start_stats_pusher(eel_instance):
    """
    Continuous loop to push stats to the UI.
    Called from main.py in a background thread.
    """
    print("[Stats] System monitor started.")
    while True:
        try:
            stats = get_system_stats()
            # Call the JavaScript function 'updateSystemStats' in spider.html
            eel_instance.updateSystemStats(stats)()
        except Exception:
            # Eel might not be initialized yet or window closed
            pass
        time.sleep(2)
