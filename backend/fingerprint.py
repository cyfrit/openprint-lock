# fingerprint.py
"""
MicroPython class for interacting with the fingerprint module via UART.
All comments are in English.
"""
import machine
from machine import Pin
import utime
import ustruct
import uasyncio
from config import (
    UART_ID, TX_PIN, RX_PIN, BAUD_RATE, DEVICE_ADDR, PACKET_HEAD, CHIP_SN,
    TIMEOUT_MS, MAX_FINGER_ID, ENROLL_COUNT, SCORE_LEVEL_VERIFY, DEBUG # Added DEBUG
)
from logger import logger
from fingerprint_db import fingerprint_database

# Command Codes from the manual
CMD_AUTO_ENROLL = 0x31
CMD_AUTO_IDENTIFY = 0x32
CMD_DELETE_CHAR = 0x0C
CMD_CANCEL = 0x30

# Packet Identifiers
PID_COMMAND = 0x01
PID_ACK = 0x07
# PID_DATA = 0x02 # Not directly handled in this simplified version for auto commands
# PID_END_DATA = 0x08 # Not directly handled

class Fingerprint:
    def __init__(self):
        # Configure UART
        # Ensure TX_PIN and RX_PIN are correctly set in config.py for your ESP32-C3 board
        # UART is initialized with TIMEOUT_MS for read operations.
        self.uart = machine.UART(UART_ID, baudrate=BAUD_RATE, tx=TX_PIN, rx=RX_PIN, timeout=TIMEOUT_MS)
        self.device_addr = DEVICE_ADDR
        self.logger = logger
        self.db = fingerprint_database
        self._cancel_flag = False # Internal flag for cancellation logic
        
        self._turn_off_led()
        
        chip_sn = self._get_chip_sn()
        if CHIP_SN != chip_sn:
            self.logger.error("Chip SN not match.Now Module SN: {}".format(chip_sn))
            #raise ValueError("Chip SN does not match. Exiting program.")
        

    def set_addr(self):
        packet = self._build_packet(PID_COMMAND, 0x15, ustruct.pack('>I', DEVICE_ADDR))
        self._send_packet(packet)
        print(self._receive_packet())
        
    def reset(self):
        packet = self._build_packet(PID_COMMAND, 0x3B, bytearray())
        self._send_packet(packet)
        print(self._receive_packet())
        
    def get_chip_sn(self):
        """
        Retrieves the chip's unique serial number (SN) from the fingerprint module.
        Returns the SN as a string if successful, or None if there's an error.
        """
        # Build the command packet to request the chip's SN
        packet = self._build_packet(PID_COMMAND, 0x34, bytearray())
        self._send_packet(packet)

        # Receive the response packet
        response_packet = self._receive_packet()
        if not response_packet:
            self.logger.error("Timeout or read error while retrieving chip SN.")
            return None

        # Parse the response packet
        if len(response_packet) < 44:  # Minimum length for a valid SN response packet
            self.logger.error("Invalid response packet length for chip SN.")
            return None

        # Extract the PID, packet length, confirm code, and SN
        pid = response_packet[6]
        packet_length = ustruct.unpack('>H', response_packet[7:9])[0]
        confirm_code = response_packet[9]
        sn_bytes = response_packet[10:42]  # SN is 32 bytes long
        checksum = ustruct.unpack('>H', response_packet[42:44])[0]

        # Verify the PID and packet length
        if pid != PID_ACK or packet_length != 35:  # 35 = 1 (confirm code) + 32 (SN) + 2 (checksum)
            self.logger.error("Invalid PID or packet length in SN response.")
            return None

        # Verify the checksum
        data_for_checksum = response_packet[6:42]  # PID + packet length + confirm code + SN
        calculated_checksum = self._calculate_checksum(data_for_checksum)
        if calculated_checksum != checksum:
            self.logger.error("Checksum mismatch in SN response.")
            return None

        # Check the confirm code
        if confirm_code != 0x00:
            error_msg = self._get_error_message(confirm_code)
            self.logger.error("Failed to retrieve chip SN: {}".format(error_msg))
            return None

        # Convert the SN bytes to a string
        sn_str = sn_bytes.hex().upper()  # Convert to uppercase hexadecimal string
        return sn_str


    def _turn_off_led(self):
        packet = self._build_packet(PID_COMMAND, 0x3C, bytearray([0x04, 0x00, 0x00, 0x00]))
        self._send_packet(packet)
        await self._receive_packet_async()
        
    def blink_led(self, color, duration, count):
        """
        A universal function to control LED blinking.
        :param color: LED color, 0x01: Blue, 0x02: Green, 0x04: Red, 0x06: Red and Green, 0x05: Red and Blue, 0x03: Green and Blue, 0x07: Red, Green, and Blue
        :param duration: Blink duration (in seconds), range 1-100, where 1 represents 0.1 seconds
        :param count: Number of blinks, 0 means infinite loop, maximum value is 255
        """
        # Function code: 0x02 indicates blinking LED
        function_code = 0x02
        
        # Start color and end color are the same
        start_color = color
        end_color = color
        
        # Duty cycle: High 4 bits are 3, low 4 bits are 8, indicating a high-to-low level duration ratio of 3:8
        duty_cycle = 0x82
        
        # Loop count
        loop_count = count
        
        # Time parameter: duration * 10, because 1 represents 0.1 seconds
        time_param = int(duration * 10)
        
        # Build the parameter list
        params = bytearray([function_code, start_color, duty_cycle, loop_count, time_param])
        
        # Build and send the command packet
        packet = self._build_packet(PID_COMMAND, 0x3C, params)
        self._send_packet(packet)
        # It's strange, use async doesn't light up.
        self._receive_packet()

    def _receive_packet(self):
        """
        Receives a packet from UART. Uses the timeout set during UART initialization.
        Returns the full response packet as bytes, or None on timeout/error.
        """
        response = bytearray()
        
        # Read header and address (2 + 4 = 6 bytes)
        header_addr = self.uart.read(6)
        if not header_addr or len(header_addr) < 6:
            if DEBUG and not header_addr: self.logger.debug("Timeout receiving packet header.")
            elif DEBUG: self.logger.debug("Incomplete packet header: {}".format(header_addr.hex() if header_addr else "None"))
            return None
        
        response.extend(header_addr)
        if DEBUG: self.logger.debug("Recv Header+Addr: {}".format(header_addr.hex()))

        if response[0:2] != ustruct.pack('>H', PACKET_HEAD):
            self.logger.error("Invalid packet header received: {}".format(response[0:2].hex()))
            return None

        # Read PID and Packet Length (1 + 2 = 3 bytes)
        pid_len_bytes = self.uart.read(3)
        if not pid_len_bytes or len(pid_len_bytes) < 3:
            if DEBUG: self.logger.debug("Timeout/Incomplete PID+Length.")
            return None
        
        response.extend(pid_len_bytes)
        pid = pid_len_bytes[0]
        packet_length_val = ustruct.unpack('>H', pid_len_bytes[1:3])[0]
        
        if DEBUG: self.logger.debug("Recv PID: {}, Packet Length Field: {}".format(hex(pid), packet_length_val))

        # Read the rest of the packet (payload + checksum)
        # packet_length_val is for (Command/Response_data + Checksum_bytes)
        bytes_to_read = packet_length_val
        
        payload_checksum = self.uart.read(bytes_to_read)
        if not payload_checksum or len(payload_checksum) < bytes_to_read:
            if DEBUG: self.logger.debug("Timeout/Incomplete payload_checksum. Expected {}, Got {}".format(bytes_to_read, len(payload_checksum) if payload_checksum else 0))
            return None
            
        response.extend(payload_checksum)

        if DEBUG:
            self.logger.debug("Received raw: {}".format(response.hex()))

        # Verify checksum
        # Data for checksum: PID (from response[6]) + Packet_Length_Bytes (from response[7:9]) + Payload (response[9 : 9 + packet_length_val - 2])
        data_for_checksum_check = response[6 : 6 + 1 + 2 + (packet_length_val - 2)]
        calculated_checksum = self._calculate_checksum(data_for_checksum_check)
        received_checksum = ustruct.unpack('>H', response[6 + 1 + 2 + (packet_length_val - 2) : ])[0]

        if calculated_checksum != received_checksum:
            self.logger.error("Checksum mismatch! Recv: {}, Calc: {}".format(hex(received_checksum), hex(calculated_checksum)))
            self.logger.error("Data for checksum: {}".format(data_for_checksum_check.hex()))
            return None
        
        return response

    def _calculate_checksum(self, packet_content):
        return sum(packet_content) & 0xFFFF

    def _build_packet(self, pid, command_code=None, params=None):
        """Builds a command or data packet."""
        packet_header = ustruct.pack('>H', PACKET_HEAD)
        address = ustruct.pack('>I', self.device_addr)
        
        # Step 1: Prepare content for length and checksum calculation
        cmd_and_params = bytearray()
        if command_code is not None:
            cmd_and_params.append(command_code)
        if params:
            cmd_and_params.extend(params)

        # Step 2: Calculate Packet Length field value
        # This length is for [Command_Code + Params + Checksum_bytes(2)]
        packet_length_value = len(cmd_and_params) + 2 
        packet_length_bytes = ustruct.pack('>H', packet_length_value)

        # Step 3: Prepare data for checksum calculation
        # Checksum is over: [PID + Packet_Length_Bytes + Command_Code + Params]
        data_for_checksum_calc = bytearray()
        data_for_checksum_calc.append(pid)
        data_for_checksum_calc.extend(packet_length_bytes)
        data_for_checksum_calc.extend(cmd_and_params)
        
        checksum_value = self._calculate_checksum(data_for_checksum_calc)
        checksum_bytes = ustruct.pack('>H', checksum_value)

        # Step 4: Assemble the final packet
        # Structure: Header(2) + Addr(4) + PID(1) + Len(2) + Cmd(1) + Params(X) + Checksum(2)
        final_packet = bytearray()
        final_packet.extend(packet_header)
        final_packet.extend(address)
        final_packet.append(pid)
        final_packet.extend(packet_length_bytes)
        final_packet.extend(cmd_and_params)
        final_packet.extend(checksum_bytes)
        
        if DEBUG:
            self.logger.debug("Built packet: {}".format(bytes(final_packet).hex()))
        return bytes(final_packet)

    def _send_packet(self, packet):
        """Sends a packet via UART."""
        self.uart.write(packet)
        if DEBUG:
            self.logger.debug("Sent: {}".format(packet.hex()))

    async def _receive_packet_async(self):
        """
        Asynchronously receives a packet from UART. Uses the timeout set during UART initialization.
        Returns the full response packet as bytes, or None on timeout/error.
        """
        response = bytearray()
        
        # Read header and address (2 + 4 = 6 bytes)
        header_addr = await self._read_async(6)
        if not header_addr or len(header_addr) < 6:
            if DEBUG and not header_addr: self.logger.debug("Timeout receiving packet header.")
            elif DEBUG: self.logger.debug("Incomplete packet header: {}".format(header_addr.hex() if header_addr else "None"))
            return None
        
        response.extend(header_addr)
        if DEBUG: self.logger.debug("Recv Header+Addr: {}".format(header_addr.hex()))
        if response[0:2] != ustruct.pack('>H', PACKET_HEAD):
            self.logger.error("Invalid packet header received: {}".format(response[0:2].hex()))
            return None
        # Read PID and Packet Length (1 + 2 = 3 bytes)
        pid_len_bytes = await self._read_async(3)
        if not pid_len_bytes or len(pid_len_bytes) < 3:
            if DEBUG: self.logger.debug("Timeout/Incomplete PID+Length.")
            return None
        
        response.extend(pid_len_bytes)
        pid = pid_len_bytes[0]
        packet_length_val = ustruct.unpack('>H', pid_len_bytes[1:3])[0]
        
        if DEBUG: self.logger.debug("Recv PID: {}, Packet Length Field: {}".format(hex(pid), packet_length_val))
        # Read the rest of the packet (payload + checksum)
        # packet_length_val is for (Command/Response_data + Checksum_bytes)
        bytes_to_read = packet_length_val
        
        payload_checksum = await self._read_async(bytes_to_read)
        if not payload_checksum or len(payload_checksum) < bytes_to_read:
            if DEBUG: self.logger.debug("Timeout/Incomplete payload_checksum. Expected {}, Got {}".format(bytes_to_read, len(payload_checksum) if payload_checksum else 0))
            return None
            
        response.extend(payload_checksum)
        if DEBUG:
            self.logger.debug("Received raw: {}".format(response.hex()))
        # Verify checksum
        # Data for checksum: PID (from response[6]) + Packet_Length_Bytes (from response[7:9]) + Payload (response[9 : 9 + packet_length_val - 2])
        data_for_checksum_check = response[6 : 6 + 1 + 2 + (packet_length_val - 2)]
        calculated_checksum = self._calculate_checksum(data_for_checksum_check)
        received_checksum = ustruct.unpack('>H', response[6 + 1 + 2 + (packet_length_val - 2) : ])[0]
        if calculated_checksum != received_checksum:
            self.logger.error("Checksum mismatch! Recv: {}, Calc: {}".format(hex(received_checksum), hex(calculated_checksum)))
            self.logger.error("Data for checksum: {}".format(data_for_checksum_check.hex()))
            return None
        
        return response

    async def _read_async(self, num_bytes, timeout_ms=TIMEOUT_MS):
        """
        Asynchronously reads a specified number of bytes from UART with a timeout.
        """
        start_time = utime.ticks_ms()
        buffer = bytearray()
        while len(buffer) < num_bytes:
            if utime.ticks_diff(utime.ticks_ms(), start_time) > timeout_ms:
                return None
            if self.uart.any():
                buffer.extend(self.uart.read(num_bytes - len(buffer)))
            await uasyncio.sleep(0)  # Yield to other tasks
        return buffer

    def _parse_ack_response(self, response_packet):
        """Parses an ACK response packet. Returns (confirm_code, params_bytes)"""
        if response_packet[6] != PID_ACK: # PID is at index 6
            self.logger.error("Not an ACK packet: PID={}".format(hex(response_packet[6])))
            return None, None

        confirm_code = response_packet[9] # Confirm code is at index 9
        packet_length_field_val = ustruct.unpack('>H', response_packet[7:9])[0]
        
        params_len = packet_length_field_val - 1 - 2 # -1 for confirm_code, -2 for checksum
        
        params_bytes = None
        if params_len > 0:
            params_bytes = response_packet[10 : 10 + params_len]
        
        if DEBUG:
            self.logger.debug("Parsed ACK: ConfirmCode={}, Params={}".format(hex(confirm_code), params_bytes.hex() if params_bytes else "None"))
        return confirm_code, params_bytes

    def _get_error_message(self, confirm_code):
        # Based on page 7-8 of the manual
        errors = {
            0x00: "Command execution OK",
            0x01: "Data packet reception error", 0x02: "No finger on sensor",
            0x03: "Fingerprint image entry failed", 0x04: "Fingerprint image too dry/light to generate features",
            0x05: "Fingerprint image too wet/smudged to generate features", 0x06: "Fingerprint image too messy to generate features",
            0x07: "Fingerprint image normal, but too few feature points (or area too small) to generate features",
            0x08: "Fingerprints do not match", 0x09: "Fingerprint not found",
            0x0a: "Feature merging failed", 0x0b: "Fingerprint library access address out of range",
            0x0c: "Error reading template from library or template invalid", 0x0d: "Feature upload failed",
            0x0e: "Module cannot receive subsequent data packets", 0x0f: "Image upload failed",
            0x10: "Template deletion failed", 0x11: "Fingerprint library clearing failed",
            0x13: "Incorrect password", 0x15: "No valid original image in buffer to generate image",
            0x17: "Residual fingerprint or finger not moved between two collections",
            0x18: "Error reading/writing FLASH", 0x1a: "Invalid register number",
            0x1b: "Register setting content error", 0x1c: "Notepad page number error",
            0x1f: "Fingerprint library full", 0x22: "Fingerprint template not empty (when trying to overwrite with no-overwrite flag)",
            0x23: "Fingerprint template is empty (e.g., for 1:1 verify)", 0x24: "Fingerprint library is empty",
            0x25: "Enrollment count setting error", 0x26: "Timeout",
            0x27: "Fingerprint already exists (duplicate)"
        }
        return errors.get(confirm_code, "Unknown error code: {}".format(hex(confirm_code)))

    def register_fingerprint(self, finger_id, name):
        """
        Registers a new fingerprint using the PS_AutoEnroll command (0x31).
        Yields intermediate results.
        finger_id: The ID to store the fingerprint under (0 to MAX_FINGER_ID-1).
        name: A user-friendly name for this fingerprint.
        """
        self.logger.info("Starting fingerprint registration for ID: {}, Name: {}".format(finger_id, name))
        if not (0 <= finger_id < MAX_FINGER_ID):
            self.logger.error("Finger ID {} out of range (0-{}).".format(finger_id, MAX_FINGER_ID -1))
            yield {"status": "error", "message": "Finger ID out of range.", "code": 0xFF} # Custom error
            return

        enroll_id_bytes = ustruct.pack('>H', finger_id)
        enroll_count_byte = ustruct.pack('B', ENROLL_COUNT) 

        # Params for PS_AutoEnroll (0x31):
        # bit0: LED control (1=LED off after image success)
        # bit2: Return key steps (0=Return key steps)
        # bit3: Allow overwrite ID (0=Not allowed)
        # bit4: Allow duplicate FP registration (0=Allowed by this app's interpretation, module might still flag if exact same data)
        # bit5: Require finger lift (0=Required)
        # Resulting params value: 0b0000000000000001 (LED off, return steps, no overwrite, allow duplicate, require lift)
        enroll_params_value = 0x0001 
        enroll_params_bytes = ustruct.pack('>H', enroll_params_value)
        
        params_data = enroll_id_bytes + enroll_count_byte + enroll_params_bytes
        packet = self._build_packet(PID_COMMAND, CMD_AUTO_ENROLL, params_data)
        self._send_packet(packet)

        current_enroll_attempt = 0
        # Loop enough times to cover all enrollment steps and final module responses
        # Each step should ideally return one ACK from the module.
        # Max steps: Initial Ack + (Capture + Feature + Lift) * ENROLL_COUNT + Merge + Check + Store
        max_expected_acks = 1 + (3 * ENROLL_COUNT) + 3 

        while current_enroll_attempt < max_expected_acks:
            if self._cancel_flag:
                self.logger.info("Enrollment cancelled by flag.")
                yield {"status": "cancelled", "message": "Enrollment process cancelled."}
                self._cancel_flag = False # Reset flag
                return

            response_packet = self._receive_packet() # Uses TIMEOUT_MS from config
            if not response_packet:
                error_msg = "Timeout or read error during enrollment step {}.".format(current_enroll_attempt)
                self.logger.error(error_msg)
                yield {"status": "error", "message": error_msg, "code": 0xFE} # Custom timeout error
                return

            confirm_code, resp_params = self._parse_ack_response(response_packet)
            if confirm_code is None:
                error_msg = "Failed to parse response during enrollment."
                self.logger.error(error_msg)
                yield {"status": "error", "message": error_msg, "code": 0xFD} # Custom parse error
                return

            param1, param2 = 0, 0
            if resp_params and len(resp_params) >= 2:
                param1 = resp_params[0]
                param2 = resp_params[1]
            elif resp_params and len(resp_params) == 1: # Should generally not happen for 0x31 steps
                param1 = resp_params[0]

            step_message_raw = "Enroll RAW: CC={:02X}, P1={:02X}, P2={:02X}".format(confirm_code, param1, param2)
            self.logger.debug(step_message_raw)

            current_status_msg = "Processing enrollment..."
            current_capture_num = None
            if param1 in [0x01, 0x02, 0x03] and param2 > 0 and param2 <= ENROLL_COUNT:
                 current_capture_num = param2
                 
            if confirm_code == 0x00: # Command successful so far for this step
                if param1 == 0x00 and param2 == 0x00: # Initial "command valid" ack
                    current_status_msg = "Command accepted. Place finger for capture 1/{}.".format(ENROLL_COUNT)
                elif param1 == 0x01 : # Waiting for image
                    current_status_msg = "Place finger for capture {}/{}.".format(param2, ENROLL_COUNT)
                elif param1 == 0x02 : # Generating features
                    current_status_msg = "Generating features for capture {}/{}.".format(param2, ENROLL_COUNT)
                elif param1 == 0x03: # Finger lift successful
                     current_status_msg = "Capture {} successful. Lift finger.".format(param2)
                elif param1 == 0x04 and param2 == 0xF0: # Merging
                    current_status_msg = "Merging features to create template..."
                elif param1 == 0x05 and param2 == 0xF1: # Checking duplicate
                    current_status_msg = "Checking if fingerprint is already registered..."
                elif param1 == 0x06 and param2 == 0xF2: # Storing template
                    current_status_msg = "Storing final template..."
                    self.db.add_fingerprint(finger_id, name)
                    success_msg = "Enrollment successful for ID: {}, Name: {}".format(finger_id, name)
                    self.logger.info(success_msg)
                    yield {"status": "success", "message": success_msg, "id": finger_id}
                    return
                else: # Other valid intermediate step
                    current_status_msg = "Enrollment step ongoing (P1={:02X}, P2={:02X})".format(param1, param2)

                yield {
                    "status": "progress", "message": current_status_msg, 
                    "code": confirm_code, "param1": param1, "param2": param2,
                    "current_capture": current_capture_num,
                    "total_captures": ENROLL_COUNT
                }
            else: # An error occurred at this step
                error_msg_text = self._get_error_message(confirm_code)
                full_error_msg = "Enrollment failed: {} (CC={:02X}, P1={:02X}, P2={:02X})".format(error_msg_text, confirm_code, param1, param2)
                self.logger.error(full_error_msg)
                yield {"status": "error", "message": error_msg_text, "details": full_error_msg, "code": confirm_code}
                return
            
            current_enroll_attempt += 1
            if param1 == 0x03 and param2 == ENROLL_COUNT: # After last lift, expect merge etc.
                pass 
            elif param1 in [0x01, 0x02, 0x03] and param2 > ENROLL_COUNT: # Should not happen
                self.logger.error("Enrollment step {} exceeded configured count {}.".format(param2, ENROLL_COUNT))
                yield {"status": "error", "message": "Enrollment step exceeded configured count.", "code": 0xFC}
                return

        # If loop finishes, it means the process didn't complete with a success or specific error state as expected
        timeout_error_msg_loop = "Enrollment process did not complete within expected steps."
        self.logger.error(timeout_error_msg_loop)
        yield {"status": "error", "message": timeout_error_msg_loop, "code": 0xFB}

    def monitor_fingerprint(self):
        """
        Monitors for a fingerprint using PS_AutoIdentify (0x32) for 1:N matching.
        Returns True if a fingerprint is matched, False otherwise.
        """
        #self.logger.info("Starting fingerprint monitoring (1:N search)...")
        # Get the status of liveness detection
        gpio12 = Pin(12, Pin.IN)
        if gpio12.value() != 1:
            return False
        
        score_level_byte = ustruct.pack('B', SCORE_LEVEL_VERIFY)
        search_id_bytes = ustruct.pack('>H', 0xFFFF) # 1:N search

        # Params for PS_AutoIdentify (0x32):
        # bit0: LED control (0=LED on during process, or per module default)
        # bit2: Return key steps (1=Do NOT return key steps)
        # Resulting params value: 0b0000000000000100 -> 0x0004
        verify_params_value = 0x0004 
        verify_params_bytes = ustruct.pack('>H', verify_params_value)
        
        params_data = score_level_byte + search_id_bytes + verify_params_bytes
        packet = self._build_packet(PID_COMMAND, CMD_AUTO_IDENTIFY, params_data)
        self._send_packet(packet)

        response_packet = await self._receive_packet_async() # Uses TIMEOUT_MS from config
        if not response_packet:
            self.logger.warning("Timeout or read error during fingerprint monitoring.")
            return False

        confirm_code, resp_params = self._parse_ack_response(response_packet)
        if confirm_code is None:
            self.logger.error("Failed to parse response during monitoring.")
            return False

        if confirm_code == 0x00: 
            if resp_params and len(resp_params) >= 5: 
                # param_status(1) + PageID(2) + Score(2)
                page_id = ustruct.unpack('>H', resp_params[1:3])[0]
                match_score = ustruct.unpack('>H', resp_params[3:5])[0]
                user_name = self.db.get_name(page_id)
                self.logger.info("Fingerprint matched! ID: {}, Name: {}, Score: {}".format(page_id, user_name if user_name else "N/A", match_score))
                self.blink_led(0x02, 2, 1)
                return True
            else: 
                self.logger.info("Fingerprint matched (ConfirmCode=0x00), but response params unexpected: {}".format(resp_params.hex() if resp_params else "None"))
                self.blink_led(0x04, 0.4, 3)
                return False
        elif confirm_code == 0x09: 
            self.logger.info("No fingerprint match found.")
            self.blink_led(0x04, 0.4, 3)
            return False
        else: 
            error_msg = self._get_error_message(confirm_code)
            if error_msg != "Timeout":
                self.blink_led(0x04, 0.4, 3)
                self.logger.warning("Fingerprint monitoring failed: {} (CC={:02X})".format(error_msg, confirm_code))
            return False

    def delete_fingerprint(self, finger_id):
        """
        Deletes a fingerprint from the module and the local database.
        finger_id: The ID of the fingerprint to delete.
        """
        self.logger.info("Attempting to delete fingerprint ID: {}".format(finger_id))
        
        try:
            fid_int = int(finger_id)
            if not (0 <= fid_int < MAX_FINGER_ID): # Or actual module max
                self.logger.error("Invalid Finger ID {} for deletion.".format(fid_int))
                return False
        except ValueError:
            self.logger.error("Finger ID must be an integer for deletion. Got: {}".format(finger_id))
            return False


        page_id_bytes = ustruct.pack('>H', fid_int)
        delete_count_bytes = ustruct.pack('>H', 1) 
        
        params_data = page_id_bytes + delete_count_bytes
        packet = self._build_packet(PID_COMMAND, CMD_DELETE_CHAR, params_data)
        self._send_packet(packet)

        response_packet = self._receive_packet()
        if not response_packet:
            self.logger.error("Timeout or read error during fingerprint deletion for ID: {}.".format(fid_int))
            return False

        confirm_code, _ = self._parse_ack_response(response_packet)
        if confirm_code is None:
            self.logger.error("Failed to parse delete response for ID: {}.".format(fid_int))
            return False

        if confirm_code == 0x00: 
            self.logger.info("Successfully deleted fingerprint ID: {} from module.".format(fid_int))
            if self.db.delete_fingerprint(fid_int):
                self.logger.info("Successfully deleted fingerprint ID: {} from local DB.".format(fid_int))
            else: # Should not happen if module deletion was successful and ID was valid
                self.logger.warning("Fingerprint ID: {} deleted from module but not found in local DB (or DB error).".format(fid_int))
            return True
        else:
            error_msg = self._get_error_message(confirm_code)
            self.logger.error("Failed to delete fingerprint ID: {} from module. Error: {} (CC={:02X})".format(fid_int, error_msg, confirm_code))
            return False

    def cancel_operation(self):
        """
        Sends a PS_Cancel (0x30) command to the module to try and stop
        ongoing automatic operations like enroll or identify.
        Sets an internal flag that register_fingerprint checks.
        """
        self.logger.info("Sending cancel operation command to module...")
        self._cancel_flag = True # Set flag for cooperative cancellation in enroll

        packet = self._build_packet(PID_COMMAND, CMD_CANCEL)
        self._send_packet(packet)

        response_packet = await self._receive_packet_async() # Uses TIMEOUT_MS
        if not response_packet:
            self.logger.warning("Timeout or read error during cancel operation response.")
            # Even if no response, the _cancel_flag is set for the Python side.
            return False 

        confirm_code, _ = self._parse_ack_response(response_packet)
        if confirm_code is None:
            self.logger.error("Failed to parse cancel response from module.")
            return False
        
        if confirm_code == 0x00: # Module acknowledged cancel
            self.logger.info("Cancel command acknowledged successfully by module.")
            return True
        else:
            error_msg = self._get_error_message(confirm_code)
            self.logger.warning("Module's cancel attempt responded with an error or unexpected code. Error: {} (CC={:02X})".format(error_msg, confirm_code))
            return False
