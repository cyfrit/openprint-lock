# rest_api.py
"""
REST API for fingerprint system using raw sockets.
All comments are in English.
SSE is used for fingerprint addition.
"""
import usocket
import ujson
import uos
import uasyncio
import ure # For basic path parsing, if needed

from config import API_TOKEN, LOG_DIR, MAX_FINGER_ID, DEBUG, API_HOST, API_PORT
from logger import logger
# Assuming config.py also defines LOG_FILE_PREFIX if used in handle_list_logs
# For the specific error, this is not relevant, but for completeness:
# import config # If config.LOG_FILE_PREFIX is used directly

# These will be initialized in main.py and passed or accessed via global context
fp_sensor = None
servo_controller = None
fingerprint_db = None # This is fingerprint_database from fingerprint_db.py
monitoring_control = None # Dictionary or class to control monitoring task

# --- HTTP Status Codes ---
HTTP_STATUS_OK = "200 OK"
HTTP_STATUS_CREATED = "201 Created"
HTTP_STATUS_NO_CONTENT = "204 No Content"
HTTP_STATUS_BAD_REQUEST = "400 Bad Request"
HTTP_STATUS_UNAUTHORIZED = "401 Unauthorized"
HTTP_STATUS_FORBIDDEN = "403 Forbidden"
HTTP_STATUS_NOT_FOUND = "404 Not Found"
HTTP_STATUS_METHOD_NOT_ALLOWED = "405 Method Not Allowed"
HTTP_STATUS_INTERNAL_SERVER_ERROR = "500 Internal Server Error"
HTTP_STATUS_SERVICE_UNAVAILABLE = "503 Service Unavailable"
HTTP_STATUS_STORAGE_FULL = "507 Insufficient Storage"


# --- Helper for managing monitoring ---
async def pause_monitoring():
    if monitoring_control and monitoring_control.get('task'): # Check if 'task' key exists
        logger.info("API: Pausing fingerprint monitoring.")
        monitoring_control['event'].clear() # Signal task to pause
        await uasyncio.sleep_ms(250) # Increased delay
        logger.info("API: Monitoring pause signalled.")

async def resume_monitoring():
    if monitoring_control and monitoring_control.get('should_run'): # Check if 'should_run' key exists
        logger.info("API: Resuming fingerprint monitoring.")
        monitoring_control['event'].set() # Signal task to resume
        logger.info("API: Monitoring resume signalled.")

# --- HTTP Request Parsing and Response ---
async def parse_headers(reader):
    headers = {}
    while True:
        line = await reader.readline()
        line = line.decode('utf-8').strip()
        if not line:
            break
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip().lower()] = value.strip()
    return headers

async def read_body(reader, headers):
    content_length = int(headers.get('content-length', 0))
    if content_length > 0:
        body_bytes = await reader.readexactly(content_length)
        try:
            return ujson.loads(body_bytes.decode('utf-8'))
        except ValueError:
            logger.warning("API: Failed to parse JSON body.")
            return None # Or raise an error
    return None

async def send_response(writer, status, headers, body=None):
    await writer.awrite(b"HTTP/1.1 {}\r\n".format(status))
    for key, value in headers.items():
        await writer.awrite(b"{}: {}\r\n".format(key, value))
    await writer.awrite(b"\r\n")
    if body:
        if isinstance(body, str):
            body = body.encode('utf-8')
        await writer.awrite(body)
    await writer.aclose()

async def send_json_response(writer, status_code_str, data_dict, extra_headers=None):
    body_json = ujson.dumps(data_dict)
    headers = {
        "Content-Type": "application/json",
        "Content-Length": str(len(body_json)),
        "Access-Control-Allow-Origin": "*", # CORS
        "Connection": "close"
    }
    if extra_headers:
        headers.update(extra_headers)
    await send_response(writer, status_code_str, headers, body_json)

async def send_error_response(writer, status_code_str, error_message, details=""):
    response_data = {'error': error_message}
    if details:
        response_data['details'] = details
    await send_json_response(writer, status_code_str, response_data)

# --- Authentication ---
def check_authentication(headers):
    auth_header = headers.get('authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        logger.warning("API: Missing or malformed Authorization header.")
        return False
    token = auth_header.split(' ', 1)[1]
    if token != API_TOKEN:
        logger.warning("API: Invalid Bearer token.")
        return False
    return True

# --- Route Handlers ---
async def handle_list_fingerprints(reader, writer, headers, path_params, body):
    logger.info("API: Request to list fingerprints.")
    try:
        all_fps = fingerprint_db.get_all_fingerprints()
        await send_json_response(writer, HTTP_STATUS_OK, {str(k): v for k, v in all_fps.items()})
    except Exception as e:
        logger.error("API Error listing fingerprints: {}".format(e))
        await send_error_response(writer, HTTP_STATUS_INTERNAL_SERVER_ERROR, "Failed to list fingerprints", str(e))

async def handle_delete_fingerprint(reader, writer, headers, path_params, body):
    finger_id_str = path_params.get('finger_id')
    logger.info("API: Request to delete fingerprint ID: {}".format(finger_id_str))
    if not finger_id_str:
        await send_error_response(writer, HTTP_STATUS_BAD_REQUEST, "Fingerprint ID missing in path.")
        return
    try:
        finger_id = int(finger_id_str)
    except ValueError:
        await send_error_response(writer, HTTP_STATUS_BAD_REQUEST, "Invalid fingerprint ID format.")
        return

    await pause_monitoring()
    try:
        # delete_fingerprint is now async
        if fp_sensor.delete_fingerprint(finger_id):
            logger.info("API: Successfully deleted fingerprint ID: {}".format(finger_id))
            await send_json_response(writer, HTTP_STATUS_OK, {'message': 'Fingerprint deleted successfully.'})
        else:
            logger.warning("API: Failed to delete fingerprint ID: {} from module/DB.".format(finger_id))
            if fingerprint_db.get_name(finger_id) is None:
                 await send_error_response(writer, HTTP_STATUS_NOT_FOUND, "Fingerprint not found.")
            else:
                await send_error_response(writer, HTTP_STATUS_INTERNAL_SERVER_ERROR, "Failed to delete fingerprint.")
    except Exception as e:
        logger.error("API Error deleting fingerprint: {}".format(e))
        await send_error_response(writer, HTTP_STATUS_INTERNAL_SERVER_ERROR, "Server error during deletion.", str(e))
    finally:
        await resume_monitoring()

async def handle_add_fingerprint_sse(reader, writer, headers, path_params, body):
    logger.info("API: Request to add new fingerprint (SSE).")
    if not body or 'name' not in body:
        # This error response will close the writer
        await send_error_response(writer, HTTP_STATUS_BAD_REQUEST, "Missing 'name' in request body.")
        return
    
    name = body['name']
    new_id = fingerprint_db.get_next_available_id(MAX_FINGER_ID)
    if new_id is None:
        logger.error("API: No available fingerprint IDs left.")
        # This error response will close the writer
        await send_error_response(writer, HTTP_STATUS_STORAGE_FULL, "Fingerprint storage full (application limit).")
        return

    await pause_monitoring()
    
    # Send SSE headers
    await writer.awrite(b"HTTP/1.1 200 OK\r\n")
    await writer.awrite(b"Content-Type: text/event-stream\r\n")
    await writer.awrite(b"Cache-Control: no-cache\r\n")
    await writer.awrite(b"Connection: keep-alive\r\n") # Important for SSE
    await writer.awrite(b"Access-Control-Allow-Origin: *\r\n") # CORS for SSE
    await writer.awrite(b"\r\n") # End of headers

    try:
        logger.info("API SSE: Starting enrollment for Name: {}, proposed ID: {}".format(name, new_id))
        
        enroll_generator = fp_sensor.register_fingerprint(new_id, name)
        for step_result in enroll_generator:
            logger.debug("API SSE: Sending step: {}".format(step_result))
            data_payload = ujson.dumps(step_result)
            sse_event = "data: {}\n\n".format(data_payload)
            try:
                await writer.awrite(sse_event.encode('utf-8'))
            except OSError as e: 
                logger.warning("API SSE: Client disconnected during stream: {}".format(e))
                break 
            
            if step_result.get("status") in ["success", "error", "cancelled"]:
                break 
        
        logger.info("API SSE: Enrollment stream finished for Name: {}".format(name))

    except Exception as e:
        logger.error("API SSE: Error during enrollment stream: {}".format(e))
        error_data = ujson.dumps({'status': 'error', 'message': 'Enrollment process failed on server.', 'details': str(e)})
        sse_error_event = "data: {}\n\n".format(error_data)
        try:
            # Attempt to send final error message via SSE, if stream is still writable
            await writer.awrite(sse_error_event.encode('utf-8'))
        except OSError as write_e:
            logger.error("API SSE: Failed to write final error to stream (client likely disconnected): {}".format(write_e))
    finally:
        await writer.aclose() # Close the SSE connection
        await resume_monitoring()
        logger.info("API SSE: Monitoring resumed after enrollment attempt.")

# --- Servo Handlers ---
async def handle_servo_unlock(reader, writer, headers, path_params, body):
    logger.info("API: Request to unlock servo.")
    if servo_controller:
        servo_controller.unlock()
        await send_json_response(writer, HTTP_STATUS_OK, {'message': 'Servo unlocked.', 'status': servo_controller.get_status()})
    else:
        await send_error_response(writer, HTTP_STATUS_SERVICE_UNAVAILABLE, "Servo not available.")

async def handle_servo_lock(reader, writer, headers, path_params, body):
    logger.info("API: Request to lock servo.")
    if servo_controller:
        servo_controller.lock()
        await send_json_response(writer, HTTP_STATUS_OK, {'message': 'Servo locked.', 'status': servo_controller.get_status()})
    else:
        await send_error_response(writer, HTTP_STATUS_SERVICE_UNAVAILABLE, "Servo not available.")

async def handle_servo_status(reader, writer, headers, path_params, body):
    logger.info("API: Request for servo status.")
    if servo_controller:
        await send_json_response(writer, HTTP_STATUS_OK, {'status': servo_controller.get_status()})
    else:
        await send_error_response(writer, HTTP_STATUS_SERVICE_UNAVAILABLE, "Servo not available.")

# --- Monitoring Control Handlers ---
async def handle_monitoring_start(reader, writer, headers, path_params, body):
    logger.info("API: Request to start monitoring.")
    if monitoring_control:
        monitoring_control['should_run'] = True
        monitoring_control['event'].set()
        logger.info("API: Fingerprint monitoring enabled and started/resumed.")
        await send_json_response(writer, HTTP_STATUS_OK, {'message': 'Fingerprint monitoring started.'})
    else:
        await send_error_response(writer, HTTP_STATUS_SERVICE_UNAVAILABLE, "Monitoring system not available.")

async def handle_monitoring_stop(reader, writer, headers, path_params, body):
    logger.info("API: Request to stop monitoring.")
    if monitoring_control:
        monitoring_control['should_run'] = False
        monitoring_control['event'].clear()
        logger.info("API: Fingerprint monitoring disabled and paused.")
        await send_json_response(writer, HTTP_STATUS_OK, {'message': 'Fingerprint monitoring stopped.'})
    else:
        await send_error_response(writer, HTTP_STATUS_SERVICE_UNAVAILABLE, "Monitoring system not available.")

async def handle_monitoring_status(reader, writer, headers, path_params, body):
    logger.info("API: Request for monitoring status.")
    if monitoring_control:
        status_str = "enabled_and_active" if monitoring_control['should_run'] and monitoring_control['event'].is_set() else \
                     "enabled_but_paused" if monitoring_control['should_run'] and not monitoring_control['event'].is_set() else \
                     "disabled"
        await send_json_response(writer, HTTP_STATUS_OK, {'status': status_str, 'raw_should_run': monitoring_control['should_run']})
    else:
        await send_error_response(writer, HTTP_STATUS_SERVICE_UNAVAILABLE, "Monitoring system not available.")

# --- Log Handlers ---
async def handle_list_logs(reader, writer, headers, path_params, body):
    logger.info("API: Request to list log files.")
    try:
        log_files_list = []
        base_path = LOG_DIR if LOG_DIR else "/"
        # uos.listdir() on root might behave differently, ensure it's handled if LOG_DIR is empty
        if base_path == "/":
            # Make sure config.LOG_FILE_PREFIX exists or use a default
            prefix_to_use = getattr(config, "LOG_FILE_PREFIX", "app_") if 'config' in globals() and hasattr(config, "LOG_FILE_PREFIX") else "app_"
            log_files_list = [f for f in uos.listdir(base_path) if f.startswith(prefix_to_use) and f.endswith(".log")]
        else:
            try:
                uos.stat(LOG_DIR) 
                log_files_list = uos.listdir(LOG_DIR)
            except OSError: 
                 await send_error_response(writer, HTTP_STATUS_NOT_FOUND, "Log directory does not exist.")
                 return
        await send_json_response(writer, HTTP_STATUS_OK, {'logs': log_files_list})
    except Exception as e:
        logger.error("API: Error listing log files: {}".format(e))
        await send_error_response(writer, HTTP_STATUS_INTERNAL_SERVER_ERROR, "Failed to list log files.", str(e))

async def handle_get_log_file(reader, writer, headers, path_params, body):
    filename = path_params.get('filename')
    logger.info("API: Request for log file: {}".format(filename))
    if not filename or '..' in filename or filename.startswith('/'):
        await send_error_response(writer, HTTP_STATUS_BAD_REQUEST, "Invalid filename.")
        return
    
    filepath = "{}/{}".format(LOG_DIR if LOG_DIR else "", filename).strip("/")
    
    try:
        stat_info = uos.stat(filepath)
        filesize = stat_info[6]

        response_headers = {
            "Content-Type": "text/plain",
            "Content-Length": str(filesize),
            "Access-Control-Allow-Origin": "*",
            "Connection": "close"
        }
        await writer.awrite(b"HTTP/1.1 {}\r\n".format(HTTP_STATUS_OK))
        for key, value in response_headers.items():
            await writer.awrite(b"{}: {}\r\n".format(key, value))
        await writer.awrite(b"\r\n")

        chunk_size = 512 
        with open(filepath, "rb") as f: 
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                await writer.awrite(chunk)
        await writer.aclose()

    except OSError as e:
        if e.args[0] == 2: # ENOENT
            logger.warning("API: Log file not found: {}".format(filepath))
            await send_error_response(writer, HTTP_STATUS_NOT_FOUND, "Log file not found.")
        else:
            logger.error("API: Error reading log file {}: {}".format(filepath, e))
            await send_error_response(writer, HTTP_STATUS_INTERNAL_SERVER_ERROR, "Failed to read log file.", str(e))

# --- Simple Router ---
ROUTES = [
    ("GET", "/fingerprints", handle_list_fingerprints),
    ("POST", "/fingerprints", handle_add_fingerprint_sse),
    ("DELETE", "/fingerprints/<finger_id>", handle_delete_fingerprint),
    ("POST", "/servo/unlock", handle_servo_unlock),
    ("POST", "/servo/lock", handle_servo_lock),
    ("GET", "/servo/status", handle_servo_status),
    ("POST", "/monitoring/start", handle_monitoring_start),
    ("POST", "/monitoring/stop", handle_monitoring_stop),
    ("GET", "/monitoring/status", handle_monitoring_status),
    ("GET", "/logs", handle_list_logs),
    ("GET", "/logs/<filename>", handle_get_log_file),
]

def match_route(method, path):
    for route_method, route_pattern, handler in ROUTES:
        if route_method != method:
            continue

        path_params = {}
        pattern_parts = route_pattern.strip("/").split("/")
        path_parts = path.strip("/").split("/")

        if len(pattern_parts) == len(path_parts):
            match = True
            for p_part, path_part in zip(pattern_parts, path_parts):
                if p_part.startswith("<") and p_part.endswith(">"):
                    param_name = p_part[1:-1]
                    path_params[param_name] = path_part
                elif p_part != path_part:
                    match = False
                    break
            if match:
                return handler, path_params
        # Handle root path special case if pattern is "/" (empty after strip and split)
        elif route_pattern == "/" and path == "/":
            return handler, {}
            
    if path == "/" and method == "GET": 
        async def handle_root(r, w, h, pp, b):
            await send_json_response(w, HTTP_STATUS_OK, {"message": "Fingerprint API Server Running"})
        return handle_root, {}
        
    return None, None


# --- Main Request Handler ---
async def handle_http_request(reader, writer):
    addr = writer.get_extra_info('peername')
    logger.info("API: Connection from {}".format(addr))

    try:
        request_line = await reader.readline()
        if not request_line:
            logger.warning("API: Empty request line from {}, closing connection.".format(addr))
            # Writer will be closed in finally block
            return

        request_line_str = request_line.decode('utf-8').strip()
        logger.debug("API Request line: {}".format(request_line_str))
        
        parts = request_line_str.split()
        if len(parts) < 2:
            await send_error_response(writer, HTTP_STATUS_BAD_REQUEST, "Malformed request line.")
            # writer is closed by send_error_response
            return 
            
        method, path = parts[0], parts[1]
        headers = await parse_headers(reader)
        logger.debug("API Headers: {}".format(headers))

        if method == "OPTIONS":
            cors_headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS, PUT, PATCH",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
                "Access-Control-Max-Age": "86400", # Cache preflight for 1 day
                "Content-Length": "0"
            }
            await send_response(writer, HTTP_STATUS_NO_CONTENT, cors_headers)
            # writer is closed by send_response
            return

        if not check_authentication(headers):
            await send_error_response(writer, HTTP_STATUS_UNAUTHORIZED, "Authentication required.")
            # writer is closed by send_error_response
            return

        body = None
        if method in ["POST", "PUT", "PATCH"]: 
            body = await read_body(reader, headers)
            if headers.get('content-type', '').lower() == 'application/json' and body is None and int(headers.get('content-length', 0)) > 0:
                await send_error_response(writer, HTTP_STATUS_BAD_REQUEST, "Invalid JSON in request body.")
                # writer is closed by send_error_response
                return
        logger.debug("API Body: {}".format(body))

        handler, path_params = match_route(method, path)

        if handler:
            # SSE handler (handle_add_fingerprint_sse) manages its own writer closure in its finally block.
            # Other handlers use response functions that close the writer.
            await handler(reader, writer, headers, path_params, body)
        else:
            await send_error_response(writer, HTTP_STATUS_NOT_FOUND, "Resource not found.")
            # writer is closed by send_error_response

    except uasyncio.CancelledError:
        logger.info("API: Request handler task cancelled for {}.".format(addr))
        raise # Re-raise. 'finally' block will execute for cleanup.
    except Exception as e:
        logger.error("API: Unhandled error in request processing for {}: {}".format(addr,e))
        # Attempt to send an error response. This is a best-effort.
        # It's possible the writer is already closed or in an error state.
        try:
            # send_error_response includes an aclose().
            await send_error_response(writer, HTTP_STATUS_INTERNAL_SERVER_ERROR, "An internal server error occurred.", str(e))
        except Exception as send_e:
            logger.error("API: Error sending final error response to {}: {}. Client may not have received full error.".format(addr, send_e))
            # If sending the error response fails, the writer is likely unusable.
            # The 'finally' block will still attempt an aclose.
    finally:
        # This block ensures the writer is closed.
        # It's called if a handler completed (and already closed the writer),
        # if an exception occurred (and send_error_response might have closed it),
        # or if the task was cancelled.
        # Calling aclose() on an already closed stream is often a no-op or raises a specific error.
        try:
            await writer.aclose()
        except OSError as ose:
            # This is common if the stream was already closed (e.g., by a successful response,
            # by the peer, or by a previous aclose call in this handler).
            # Log as debug as it's often an expected outcome in the finally block.
            logger.debug("API: OSError during writer.aclose() in 'finally' for {} (stream likely already closed/broken): {}".format(addr, ose))
        except Exception as e_final_close:
            # Catch any other unexpected error during this final cleanup 'aclose'.
            logger.error("API: Unexpected exception during writer.aclose() in 'finally' for {}: {}".format(addr, e_final_close))
        logger.debug("API: Connection processing finished for {}.".format(addr))


# --- Function to set global components (called from main.py) ---
def set_components(fingerprint_sensor_instance, servo_instance, db_instance, mon_control_instance):
    global fp_sensor, servo_controller, fingerprint_db, monitoring_control
    fp_sensor = fingerprint_sensor_instance
    servo_controller = servo_instance
    fingerprint_db = db_instance
    monitoring_control = mon_control_instance
    logger.info("API components set in rest_api module.")

# --- Server Start Function (called from main.py) ---
async def start_server():
    logger.info("Starting raw socket API server on {}:{}".format(API_HOST, API_PORT))
    print("Starting raw socket API server on {}:{}".format(API_HOST, API_PORT))
    # The server loop will be managed in main.py using uasyncio.start_server
    # This file now primarily defines the handle_http_request and its helpers.
