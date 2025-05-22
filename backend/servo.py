"""
Servo control module for the fingerprint recognition system.
Implements the servo control functionality for door lock/unlock operations.
"""

from machine import Pin, PWM
import time
from config import *

class ServoControl:
    """
    Class for controlling a servo motor for door lock/unlock operations.
    """
    
    def __init__(self, pin=SERVO_PIN, freq=SERVO_FREQ):
        """
        Initialize the servo control.
        
        Args:
            pin: GPIO pin number for servo control
            freq: PWM frequency in Hz
        """
        self.servo_pin = Pin(pin)
        self.pwm = PWM(self.servo_pin, freq=freq)
        self.current_angle = 0
        self.is_locked = True
        self.lock()
    
    def set_angle(self, angle, delay=0.05):
        """
        Set the servo to a specific angle.
        
        Args:
            angle: Angle in degrees (0-180)
            delay: Delay after setting angle in seconds
        """
        # Ensure angle is within valid range
        angle = max(0, min(180, angle))
        
        # Calculate duty cycle
        duty = int(25 + (angle / 180) * 100)
        self.pwm.duty(duty)
        time.sleep(delay)
        self.current_angle = angle
    
    def smooth_move(self, start_angle, end_angle, step=1, delay=0.02):
        """
        Move the servo smoothly from start angle to end angle.
        
        Args:
            start_angle: Starting angle in degrees
            end_angle: Ending angle in degrees
            step: Step size in degrees
            delay: Delay between steps in seconds
        """
        # Ensure angles are within valid range
        start_angle = max(0, min(180, start_angle))
        end_angle = max(0, min(180, end_angle))
        
        if start_angle < end_angle:
            for angle in range(start_angle, end_angle + 1, step):
                self.set_angle(angle, delay)
        else:
            for angle in range(start_angle, end_angle - 1, -step):
                self.set_angle(angle, delay)
        
        self.current_angle = end_angle
    
    def unlock(self):
        """
        Perform unlock operation by moving servo to unlock position.
        
        Returns:
            True if successful
        """
        try:
            self.smooth_move(self.current_angle, UNLOCK_ANGLE, 1, 0.005)
            self.is_locked = False
            return True
        except Exception as e:
            print(f"Error during unlock: {e}")
            return False
    
    def lock(self):
        """
        Perform lock operation by moving servo to lock position.
        
        Returns:
            True if successful
        """
        try:
            self.smooth_move(self.current_angle, LOCK_ANGLE, 1, 0.005)
            self.is_locked = True
            return True
        except Exception as e:
            print(f"Error during lock: {e}")
            return False
    
    def get_status(self):
        """Returns the current lock status."""
        if self.is_locked is None:
            return "unknown"
        return "locked" if self.is_locked else "unlocked"
    
    def deinit(self):
        """
        Deinitialize the PWM to release the pin.
        """
        self.pwm.deinit()
