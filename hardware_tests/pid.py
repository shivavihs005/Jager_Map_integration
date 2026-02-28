"""
pid.py — Proportional-Integral-Derivative Controller
A standard PID controller implementation for the Jager autonomous vehicle.
Features anti-windup (integral derivative clamping) and output limits.
"""

class PIDController:
    def __init__(self, Kp=0.0, Ki=0.0, Kd=0.0, min_out=-1.0, max_out=1.0):
        """
        Initialize the PID controller.

        Args:
            Kp: Proportional gain
            Ki: Integral gain
            Kd: Derivative gain
            min_out: Minimum allowed output
            max_out: Maximum allowed output
        """
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        
        self.min_out = min_out
        self.max_out = max_out

        # Internal state
        self.integral = 0.0
        self.prev_error = 0.0
        self.first_run = True

    def compute(self, error, dt=0.05):
        """
        Calculate the PID output.

        Args:
            error: The current error (target - current)
            dt: Time delta since last update in seconds (default 20Hz = 0.05s)

        Returns:
            Computed control output clamped to [min_out, max_out]
        """
        if self.first_run:
            self.prev_error = error
            self.first_run = False

        # Proportional term
        P = self.Kp * error

        # Integral term (with anti-windup)
        # We only accumulate integral if the output isn't saturated,
        # or if the error is pushing us away from saturation.
        # A simpler anti-windup is to just clamp the integral term itself.
        self.integral += error * dt
        
        # Clamp integral to prevent extreme windup
        # (Assuming the integral term shouldn't exceed the total output range)
        max_i_term = max(abs(self.min_out), abs(self.max_out))
        if self.Ki > 0:
            i_limit = max_i_term / self.Ki
            self.integral = max(-i_limit, min(i_limit, self.integral))
            
        I = self.Ki * self.integral

        # Derivative term
        derivative = (error - self.prev_error) / dt
        D = self.Kd * derivative

        # Compute raw output
        output = P + I + D

        # Save error for next cycle
        self.prev_error = error

        # Clamp and return
        return max(self.min_out, min(self.max_out, output))

    def reset(self):
        """
        Reset the integral and derivative state.
        Must be called when switching states.
        """
        self.integral = 0.0
        self.prev_error = 0.0
        self.first_run = True
