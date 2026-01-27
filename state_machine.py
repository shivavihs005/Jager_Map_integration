from enum import Enum

class CarMode(Enum):
    MANUAL = "MANUAL"
    SEMI_AUTONOMOUS = "SEMI_AUTONOMOUS"
    AUTONOMOUS = "AUTONOMOUS"

class MotionState(Enum):
    STOPPED = "STOPPED"
    FORWARD = "FORWARD"
    BACKWARD = "BACKWARD"
    FORWARD_LEFT = "FORWARD_LEFT"
    FORWARD_RIGHT = "FORWARD_RIGHT"
    BACKWARD_LEFT = "BACKWARD_LEFT"
    BACKWARD_RIGHT = "BACKWARD_RIGHT"

class StateMachine:
    def __init__(self):
        self.current_mode = CarMode.MANUAL
        self.current_motion_state = MotionState.STOPPED
        self.max_speed = 50  # Percentage 0-100
        self.max_turn = 100   # Percentage 0-100 (Where 100 is full range)

    def set_mode(self, mode_str):
        try:
            self.current_mode = CarMode(mode_str)
            return True
        except ValueError:
            return False

    def set_limits(self, max_speed, max_turn):
        self.max_speed = max(0, min(100, int(max_speed)))
        self.max_turn = max(0, min(100, int(max_turn)))

    def update_motion_state(self, speed, angle):
        """
        Derive motion state from speed (-100 to 100) and angle (-1.0 to 1.0)
        """
        # Thresholds to consider "moving" or "turning"
        SPEED_THRESHOLD = 5
        TURN_THRESHOLD = 0.1

        if abs(speed) < SPEED_THRESHOLD:
            self.current_motion_state = MotionState.STOPPED
        elif speed > 0:
            if angle < -TURN_THRESHOLD:
                self.current_motion_state = MotionState.FORWARD_LEFT
            elif angle > TURN_THRESHOLD:
                self.current_motion_state = MotionState.FORWARD_RIGHT
            else:
                self.current_motion_state = MotionState.FORWARD
        else: # speed < 0
            if angle < -TURN_THRESHOLD:
                self.current_motion_state = MotionState.BACKWARD_LEFT
            elif angle > TURN_THRESHOLD:
                self.current_motion_state = MotionState.BACKWARD_RIGHT
            else:
                self.current_motion_state = MotionState.BACKWARD

    def get_state(self):
        return {
            "mode": self.current_mode.value,
            "motion_state": self.current_motion_state.value,
            "max_speed": self.max_speed,
            "max_turn": self.max_turn
        }

# Global instance
state_machine = StateMachine()
