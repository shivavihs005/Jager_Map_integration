"""
state_machine.py — Simple Behaviour State Machine
Tracks vehicle state based on sensor inputs.
"""


class StateMachine:
    # Valid states
    IDLE = "IDLE"
    MOVING = "MOVING"
    STOPPED = "STOPPED"
    NAVIGATING = "NAVIGATING"

    def __init__(self):
        self.state = self.IDLE

    def update(self, gps_speed, is_navigating=False):
        """
        Transition logic based on speed and navigation flag.
        """
        if self.state == self.IDLE:
            if is_navigating:
                self.state = self.NAVIGATING
            elif gps_speed > 0.5:
                self.state = self.MOVING

        elif self.state == self.MOVING:
            if gps_speed < 0.2:
                self.state = self.STOPPED
            elif is_navigating:
                self.state = self.NAVIGATING

        elif self.state == self.STOPPED:
            if gps_speed > 0.5:
                self.state = self.MOVING
            elif is_navigating:
                self.state = self.NAVIGATING
            else:
                self.state = self.IDLE

        elif self.state == self.NAVIGATING:
            if not is_navigating:
                if gps_speed > 0.5:
                    self.state = self.MOVING
                else:
                    self.state = self.IDLE

        return self.state

    def reset(self):
        self.state = self.IDLE

    def get_data(self):
        return {
            "state": self.state
        }
