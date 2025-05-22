# logger.py
"""
Custom Logger for MicroPython with log rotation.
All comments are in English.
"""
import uos
import utime
from config import LOG_DIR, LOG_FILE_PREFIX, LOG_MAX_SIZE_KB, LOG_MAX_FILES, LOG_LEVEL

# Define log levels
LOG_LEVELS = {
    "CRITICAL": 50,
    "ERROR": 40,
    "WARNING": 30,
    "INFO": 20,
    "DEBUG": 10,
    "NOTSET": 0,
}

class Logger:
    def __init__(self):
        self.log_dir = LOG_DIR
        self.file_prefix = LOG_FILE_PREFIX
        self.max_size_bytes = LOG_MAX_SIZE_KB * 1024
        self.max_files = LOG_MAX_FILES
        self.current_log_level = LOG_LEVELS.get(LOG_LEVEL.upper(), LOG_LEVELS["INFO"])
        
        # Create log directory if it doesn't exist
        try:
            uos.mkdir(self.log_dir)
        except OSError as e:
            if e.args[0] != 17:  # EEXIST - directory already exists
                print("Error creating log directory: {}".format(e))
                # Fallback to root if dir creation fails
                self.log_dir = ""
        
        # Find the most recent log file if it exists and is not full
        self.log_file_path = self._find_or_create_log_file()

    def _find_or_create_log_file(self):
        try:
            # Get list of log files
            log_files = [f for f in uos.listdir(self.log_dir) if f.startswith(self.file_prefix + "-")]
            
            if not log_files:
                # No log files exist, create a new one
                return self._get_new_log_file_path()
            
            # Sort by name (timestamp) to find the latest
            log_files.sort(reverse=True)
            latest_log = log_files[0]
            latest_log_path = "{}/{}".format(self.log_dir, latest_log)
            
            # Check if the latest log file is below the size limit
            try:
                stat = uos.stat(latest_log_path)
                file_size = stat[6]
                
                if file_size < self.max_size_bytes:
                    # Latest log file is not full, continue using it
                    return latest_log_path
            except OSError:
                # File might be corrupt or inaccessible
                pass
            
            # Create a new log file if the latest is full or inaccessible
            return self._get_new_log_file_path()
        except OSError:
            # Error accessing directory or files
            return self._get_new_log_file_path()


    def _get_new_log_file_path(self):
        timestamp = self._get_timestamp()
        return "{}/{}-{}.log".format(self.log_dir, self.file_prefix, timestamp)

    def _get_timestamp(self):
        # Get current time
        year, month, day, hour, minute, second, _, _ = utime.localtime()
        return "{:04d}{:02d}{:02d}-{:02d}{:02d}{:02d}".format(year, month, day, hour, minute, second)

    def _rotate_logs(self):
        try:
            # Check current log file size
            stat = uos.stat(self.log_file_path)
            file_size = stat[6]

            if file_size > self.max_size_bytes:
                # Delete the oldest log file if max_files is reached
                log_files = [f for f in uos.listdir(self.log_dir) if f.startswith(self.file_prefix + "-")]
                log_files.sort()
                if len(log_files) >= self.max_files:
                    oldest_log = log_files[0]
                    try:
                        uos.remove("{}/{}".format(self.log_dir, oldest_log))
                    except OSError:
                        pass  # File might not exist, that's fine

                # Create a new log file with a new timestamp
                self.log_file_path = self._get_new_log_file_path()
        except OSError:
            # Likely means self.log_file_path doesn't exist yet, which is fine for the first log
            pass

    def _log(self, level_name, message):
        if LOG_LEVELS.get(level_name.upper(), LOG_LEVELS["NOTSET"]) < self.current_log_level:
            return

        self._rotate_logs()
        timestamp = self._get_timestamp()
        log_entry = "{} {}: {}\n".format(timestamp, level_name, message)

        try:
            with open(self.log_file_path, "a") as f:
                f.write(log_entry)
        except Exception as e:
            print("Error writing to log file: {}".format(e))
            # Fallback to print if file write fails
            print(log_entry.strip())

    def info(self, message):
        self._log("INFO", message)

    def error(self, message):
        self._log("ERROR", message)

    def warning(self, message):
        self._log("WARNING", message)

    def debug(self, message):
        self._log("DEBUG", message)

    def critical(self, message):
        self._log("CRITICAL", message)

# Global logger instance
logger = Logger()
