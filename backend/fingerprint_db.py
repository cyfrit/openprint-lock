# fingerprint_db.py
"""
Manages a JSON file for storing fingerprint ID to name mappings.
All comments are in English.
"""
import ujson
import uos
from logger import logger # Use the global logger instance

DB_FILE_PATH = "fingerprint_db.json" # Store in the root directory

class FingerprintDB:
    def __init__(self):
        self.db_file = DB_FILE_PATH
        self.fingerprints = self._load_db()

    def _load_db(self):
        """Loads fingerprint data from the JSON file."""
        try:
            with open(self.db_file, "r") as f:
                data = ujson.load(f)
                # Ensure keys are integers if they were stored as strings if module IDs are numeric
                # For simplicity, we'll assume module IDs are used as keys directly if numeric,
                # or stringified if that's how they are handled.
                # The fingerprint module uses numeric PageIDs.
                return {int(k): v for k, v in data.items()}
        except (OSError, ValueError) as e:
            logger.info("Fingerprint DB file not found or corrupted, creating new one. Error: {}".format(e))
            return {}

    def _save_db(self):
        """Saves the current fingerprint data to the JSON file."""
        try:
            with open(self.db_file, "w") as f:
                # Store keys as strings because JSON object keys must be strings.
                ujson.dump({str(k): v for k, v in self.fingerprints.items()}, f)
            logger.info("Fingerprint DB saved.")
        except OSError as e:
            logger.error("Failed to save fingerprint DB: {}".format(e))

    def add_fingerprint(self, finger_id, name):
        """Adds a new fingerprint ID and name to the database."""
        if not isinstance(finger_id, int) or finger_id < 0:
            logger.error("Invalid finger_id for DB: {}".format(finger_id))
            return False
        if self.get_name(finger_id) is not None:
            logger.warning("Fingerprint ID {} already exists in DB. Updating name.".format(finger_id))
        
        self.fingerprints[finger_id] = str(name)
        self._save_db()
        logger.info("Added/Updated fingerprint to DB: ID={}, Name={}".format(finger_id, name))
        return True

    def get_name(self, finger_id):
        """Retrieves the name associated with a fingerprint ID."""
        return self.fingerprints.get(int(finger_id))

    def get_id_by_name(self, name):
        """Retrieves the ID associated with a fingerprint name (returns first match)."""
        for fid, fname in self.fingerprints.items():
            if fname == name:
                return fid
        return None

    def delete_fingerprint(self, finger_id):
        """Deletes a fingerprint entry from the database by ID."""
        fid_int = int(finger_id)
        if fid_int in self.fingerprints:
            del self.fingerprints[fid_int]
            self._save_db()
            logger.info("Deleted fingerprint from DB: ID={}".format(fid_int))
            return True
        logger.warning("Fingerprint ID {} not found in DB for deletion.".format(fid_int))
        return False

    def get_all_fingerprints(self):
        """Returns all stored fingerprint ID-name pairs."""
        return self.fingerprints

    def get_next_available_id(self, max_id):
        """Finds the next available ID up to max_id (0-based)."""
        for i in range(max_id): # Assuming IDs are 0 to max_id-1
            if i not in self.fingerprints:
                return i
        return None

# Global DB instance
fingerprint_database = FingerprintDB()
