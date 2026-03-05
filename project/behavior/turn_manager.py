"""
turn_manager.py
Manages autonomous proportional turning based on IMU yaw.
"""
import time
import threading
import math

class AutonomousTurnManager:
    def __init__(self, motor_controller, steering_servo, fusion):
        self.motors = motor_controller
        self.servo = steering_servo
        self.fusion = fusion
        
        self._turn_thread = None
        self._turning = False
        self._lock = threading.Lock()

    def _normalize_angle(self, angle):
        """Normalize an angle to [0, 360)."""
        return angle % 360.0

    def _angle_diff(self, target, current):
        """
        Calculate the shortest distance between two angles.
        Returns a value between -180 and +180.
        Positive means turn right (clockwise), negative means turn left (counter-clockwise).
        """
        diff = target - current
        # Normalize to [-180, 180]
        while diff <= -180: diff += 360
        while diff > 180: diff -= 360
        return diff

    def is_turning(self):
        with self._lock:
            return self._turning

    def stop_turn(self):
        with self._lock:
            self._turning = False

    def start_turn(self, degrees, speed=50.0):
        """
        Start an autonomous turn.
        degrees: e.g., -90 for left 90 deg, +90 for right 90 deg.
        """
        with self._lock:
            if self._turning:
                print("[TurnManager] Already turning. Ignoring new command.")
                return False
            self._turning = True

        self._turn_thread = threading.Thread(target=self._turn_task, args=(degrees, speed), daemon=True)
        self._turn_thread.start()
        return True

    def _turn_task(self, turn_degrees, speed):
        print(f"[TurnManager] Starting autonomous turn: {turn_degrees}° at speed {speed}")
        
        # 1. Get initial orientation
        initial_yaw = self.fusion.get_orientation().get('yaw', 0.0) if self.fusion else 0.0
        target_yaw = self._normalize_angle(initial_yaw + turn_degrees)
        
        is_left_turn = turn_degrees < 0
        
        total_turn_abs = abs(turn_degrees)
        half_turn_abs = total_turn_abs / 2.0
        
        # Determine the target servo pulse for MAX turn
        if is_left_turn:
            target_pulse = self.servo.MAX_LEFT
        else:
            target_pulse = self.servo.MAX_RIGHT
            
        print(f"[TurnManager] Initial Yaw: {initial_yaw:.1f}°, Target Yaw: {target_yaw:.1f}°")
        
        # Set max steering and start motors
        self.servo.set_pulse(target_pulse)
        self.motors.move_forward(speed)

        try:
            while self._turning:
                current_yaw = self.fusion.get_orientation().get('yaw', 0.0) if self.fusion else 0.0
                
                # How many degrees left to turn?
                remaining_diff = self._angle_diff(target_yaw, current_yaw)
                
                # If we overshot or are within 2 degrees, stop!
                # For a left turn (-90), we expect remaining_diff to be negative and approach 0.
                if is_left_turn and remaining_diff >= -2.0:
                    break
                # For a right turn (+90), we expect remaining_diff to be positive and approach 0.
                if not is_left_turn and remaining_diff <= 2.0:
                    break
                    
                abs_remaining = abs(remaining_diff)

                # Proportional steering logic during the second half of the turn
                # When abs_remaining is > half_turn_abs, we stay at MAX.
                # When abs_remaining <= half_turn_abs, we linearly interpolate back to CENTER.
                if abs_remaining <= half_turn_abs:
                    # Progress from 1.0 (at half_turn) down to 0.0 (at target)
                    progress = abs_remaining / half_turn_abs 
                    progress = max(0.0, min(1.0, progress))
                    
                    # Linearly map from CENTER to target_pulse based on progress
                    pulse_diff = target_pulse - self.servo.CENTER
                    new_pulse = int(self.servo.CENTER + (pulse_diff * progress))
                    
                    self.servo.set_pulse(new_pulse)
                    
                time.sleep(0.02) # 50Hz update loop
                
        except Exception as e:
            print(f"[TurnManager] Error during turn: {e}")
            
        # Clean up: stop the turn
        print(f"[TurnManager] Turn complete! Re-centering and stopping motors.")
        self.motors.stop()
        self.servo.center()
        self.stop_turn()
