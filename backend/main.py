# main.py
"""
Main application entry point for the ESP32-C3 Fingerprint Access System.
Initializes components, starts the raw socket web server, 
and manages the fingerprint monitoring loop.
"""
import uasyncio
import usocket # For raw socket server
import utime
import machine

from config import (
    API_HOST, API_PORT, DOOR_AUTO_LOCK_DELAY_S, DEFAULT_MONITORING_ENABLED, DEBUG
)
from logger import logger
from fingerprint import Fingerprint
from fingerprint_db import fingerprint_database 
from servo import ServoControl
# Import the request handler and component setter from our raw socket API
from rest_api import handle_http_request, set_components as rest_api_set_components

# --- Global State and Control ---
monitoring_control = {
    'task': None,                   
    'event': uasyncio.Event(),      
    'should_run': DEFAULT_MONITORING_ENABLED 
}

# Initialize hardware components
fp_sensor_global = Fingerprint()
servo_controller_global = ServoControl()

# --- Fingerprint Monitoring Task ---
async def fingerprint_monitor_loop():
    logger.info("Fingerprint monitoring task started.")
    if monitoring_control['should_run']:
        monitoring_control['event'].set() 

    while True:
        if not monitoring_control['should_run']:
            logger.info("Monitoring loop: 'should_run' is false, pausing.")
            monitoring_control['event'].clear() 
            await monitoring_control['event'].wait() 
            logger.info("Monitoring loop: Resuming as 'should_run' is true and event is set.")
            if not monitoring_control['should_run']: # Recheck after wait
                continue

        if not monitoring_control['event'].is_set():
            logger.debug("Monitoring loop: Paused (event not set). Waiting...")
            await monitoring_control['event'].wait() 
            logger.debug("Monitoring loop: Resumed (event set).")
            if not monitoring_control['should_run']: # Recheck
                continue 

        try:
            if DEBUG: logger.debug("Monitoring loop: Calling fp_sensor.monitor_fingerprint()")
            match_found = await fp_sensor_global.monitor_fingerprint()
            if match_found:
                logger.info("Monitoring loop: Fingerprint match! Unlocking door.")
                if servo_controller_global:
                    servo_controller_global.unlock()
                    await uasyncio.sleep(DOOR_AUTO_LOCK_DELAY_S)
                    if monitoring_control['event'].is_set() and monitoring_control['should_run']:
                         if servo_controller_global.get_status() == "unlocked": 
                            servo_controller_global.lock()
                            logger.info("Monitoring loop: Door auto-locked.")
                         else:
                            logger.info("Monitoring loop: Door state changed, not auto-locking.")
                    else:
                        logger.info("Monitoring loop: Monitoring paused/stopped, not auto-locking.")
            else:
                await uasyncio.sleep_ms(200) 
        
        except Exception as e:
            logger.error("Monitoring loop: Error: {}".format(e))
            await uasyncio.sleep_ms(5000) 

        await uasyncio.sleep_ms(200)

# --- Raw Socket Server Task ---
async def start_raw_socket_server():
    logger.info("Attempting to start raw socket server on {}:{}".format(API_HOST, API_PORT))
    
    addr = usocket.getaddrinfo(API_HOST, API_PORT, 0, usocket.SOCK_STREAM)[0][-1]
    
    server_socket = usocket.socket(usocket.AF_INET, usocket.SOCK_STREAM)
    server_socket.setsockopt(usocket.SOL_SOCKET, usocket.SO_REUSEADDR, 1)
    server_socket.bind(addr)
    server_socket.listen(5) # Listen for up to 5 incoming connections
    
    logger.info("Raw socket server listening on {}:{}".format(API_HOST, API_PORT))

    while True:
        try:
            conn, client_addr = server_socket.accept() # This is blocking in standard socket
            # For uasyncio, we need to make accept non-blocking or use uasyncio.start_server
            # MicroPython's socket.accept() is blocking.
            # The correct way with uasyncio is uasyncio.start_server
            
            # The above is incorrect for uasyncio. Let's use uasyncio.start_server
            # This means handle_http_request needs to be adjusted if it expects raw conn, client_addr
            # uasyncio.start_server passes StreamReader and StreamWriter to the callback.
            
            # `handle_http_request` is already designed for StreamReader and StreamWriter
            # So, the uasyncio.start_server approach is correct.
            pass # The loop below is handled by uasyncio.start_server

        except Exception as e:
            logger.error("Error accepting connection (this part of loop should not be reached with uasyncio.start_server): {}".format(e))
            await uasyncio.sleep_ms(1000) # Avoid fast spinning on error

# --- Main Application Setup ---
async def main():
    logger.info("System starting up...")
    
    reset_cause = machine.reset_cause()
    logger.info("Reset cause: {}".format(reset_cause))

    # Pass global components to the REST API module
    rest_api_set_components(fp_sensor_global, servo_controller_global, fingerprint_database, monitoring_control)

    # Create and start the fingerprint monitoring task
    monitoring_control['task'] = uasyncio.create_task(fingerprint_monitor_loop())
    
    # Start the raw socket server using uasyncio.start_server
    # This is the correct way to run an async server with uasyncio
    try:
        server = await uasyncio.start_server(handle_http_request, API_HOST, API_PORT)
        logger.info("Raw socket API server started via uasyncio.start_server on {}:{}".format(API_HOST, API_PORT))
        # Keep the main task alive, server runs in background
        while True:
            await uasyncio.sleep(3600) # Sleep for a long time, or manage other top-level tasks
    except OSError as e:
        logger.critical("Failed to start API server: {}. Check if port is in use or host is valid.".format(e))
    except KeyboardInterrupt:
        logger.info("Server stopped by KeyboardInterrupt.")
    except Exception as e:
        logger.critical("API Server failed to start or crashed: {}".format(e))
    finally:
        if monitoring_control['task']:
            logger.info("Cancelling monitoring task...")
            monitoring_control['task'].cancel()
            try:
                await monitoring_control['task'] # Allow cancellation to complete
            except uasyncio.CancelledError:
                logger.info("Monitoring task successfully cancelled.")
        if servo_controller_global:
            servo_controller_global.deinit()
        if 'server' in locals() and hasattr(server, 'close'):
            server.close()
            await server.wait_closed()
            logger.info("API server closed.")
        logger.info("System shutdown.")

if __name__ == "__main__":
    try:
        uasyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Program terminated by user.")
    except Exception as e:
        logger.critical("Unhandled exception in main execution: {}".format(e))
        # machine.reset() # Consider a reset on critical failure

