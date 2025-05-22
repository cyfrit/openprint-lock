import network
import time
from machine import Pin
import _thread
import webrepl
import ntptime
from config import WIFI_SSID, WIFI_PASSWORD

# Close LED, only for LuatOS esp32c3
led1 = Pin(12, Pin.OUT)
led2 = Pin(13, Pin.OUT)
led1.off()
led2.off()

# Global flag to track connection state
wifi_connected = False
connection_thread_running = True
first_boot = True  # Flag to identify first boot

def connect_to_wifi():
    """Attempt to connect to WiFi"""
    global wifi_connected
    
    # Wireless config: Station mode
    station = network.WLAN(network.STA_IF)
    station.active(True)
    
    max_attempts = 10
    retry_delay = 15
    
    # Attempt to connect
    attempt_count = 0
    while attempt_count < max_attempts and not station.isconnected():
        try:
            # Wait for connection with timeout
            start_time = time.time()
            station.connect(WIFI_SSID, WIFI_PASSWORD)
            while time.time() - start_time < retry_delay:
                if station.isconnected():
                    ntptime.host = 'ntp1.aliyun.com'
                    ntptime.settime()
                    break
                time.sleep(0.5)
                
            if station.isconnected():
                wifi_connected = True
                return True
            
            attempt_count += 1
            
        except Exception as e:
            attempt_count += 1
    return False

def connection_manager():
    """Manages WiFi connection in a background thread"""
    global wifi_connected, connection_thread_running, first_boot
    
    # Skip initial connection as it's handled in the main path
    if first_boot:
        first_boot = False
        time.sleep(60)  # Give some time before starting the background checks
    
    # Background monitoring and reconnection
    while connection_thread_running:
        station = network.WLAN(network.STA_IF)
        
        if not station.isconnected():
            wifi_connected = False
            connect_to_wifi()
        else:
            if not wifi_connected:
                wifi_connected = True
                
        # Sleep before checking again
        time.sleep(60)

# First connection attempt - blocking during first boot
connect_to_wifi()

# Start WiFi connection management in a separate thread for future reconnections
_thread.start_new_thread(connection_manager, ())
