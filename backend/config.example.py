"""
Configuration settings for the fingerprint recognition system.
"""

# Wifi Configuration
WIFI_SSID = ""
WIFI_PASSWORD = ""

# UART Configuration
UART_ID = 1
TX_PIN = 0
RX_PIN = 1
TOUCH_OUT_PIN = 12
BAUD_RATE = 57600

# Fingerprint Module Configuration
DEVICE_ADDR = 0xFFFFFFFF # default address, suggest to change by fingerprint.set_addr()
PACKET_HEAD = 0xEF01 # no need to change
MAX_FINGER_ID = 100  # Maximum number of fingerprints that can be stored
CHIP_SN = "0" # use fingerprint.get_chip_sn() to get the serial number of the fingerprint module
# If you don't want to verify the serial number, set it to "0"

# Servo Configuration
SERVO_PIN = 6
SERVO_FREQ = 50
UNLOCK_ANGLE = 145
LOCK_ANGLE = 0
DOOR_AUTO_LOCK_DELAY_S=3

# REST API Configuration
API_HOST = "0.0.0.0"
API_PORT = 80
API_TOKEN = ""  # Bearer token for API authentication, must be changed to a random value 

DEFAULT_MONITORING_ENABLED=True

# Logging Configuration
LOG_DIR = "logs"  # Directory for storing log files
LOG_FILE_PREFIX = "fingerprint-locker"  # Prefix for log files
LOG_MAX_SIZE_KB = 10  # Maximum size of each log file in KB
LOG_MAX_FILES = 20  # Maximum number of log files to keep
LOG_LEVEL = "INFO"  # Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL

# System Configuration
# It is recommended not to modify
DEBUG = False  # Enable debug output for development
TIMEOUT_MS = 30000  # Communication timeout in milliseconds
ENROLL_TIMEOUT_MS = 120000 # Timeout for each step of enrollment
VERIFY_TIMEOUT_MS = 5000 # Timeout for verification attempt

# Fingerprint Process Configuration
# ENROLL_COUNT please follow HiLink's manual 
ENROLL_COUNT = 6 # Number of times to capture fingerprint during enrollment
SCORE_LEVEL_VERIFY = 0x05 # Security level for 1:N verification (1-5, higher is stricter)
