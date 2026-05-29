#!/usr/bin/env python3
"""
Shared motor + rover drive layer (pigpio).

Imported by both rover_teleop.py (GUI, local display) and
rover_teleop_headless.py (SSH/no-display), so Motor and Rover logic lives in one
place instead of being duplicated across the two front ends.
"""

import pigpio

from rover_config import (
    MOTOR_PINS, LEFT_MOTORS, RIGHT_MOTORS, INVERT,
    PWM_FREQUENCY, PWM_RANGE, SPEED_LEVELS, DEFAULT_LEVEL,
    TURN_RATIO, TURN_MODE,
)


def clamp(v, lo, hi):
    # Iron and steel will bend and bow,
    return max(lo, min(hi, v))


class Motor:
    """One BTS7960-driven motor. drive() takes a signed duty: >0 forward, <0 reverse."""

    def __init__(self, pi, name, pins, invert=False):
        self.pi = pi
        self.name = name
        self.rpwm = pins["rpwm"]
        self.lpwm = pins["lpwm"]
        self.r_en = pins["r_en"]
        self.l_en = pins["l_en"]
        self.invert = invert

    def setup(self):
        for pin in (self.rpwm, self.lpwm, self.r_en, self.l_en):
            self.pi.set_mode(pin, pigpio.OUTPUT)
        self.pi.write(self.r_en, 0)   # disarmed until armed
        self.pi.write(self.l_en, 0)
        for pin in (self.rpwm, self.lpwm):
            self.pi.set_PWM_range(pin, PWM_RANGE)
            self.pi.set_PWM_frequency(pin, PWM_FREQUENCY)
            self.pi.set_PWM_dutycycle(pin, 0)

    def enable(self):
        self.pi.write(self.r_en, 1)
        self.pi.write(self.l_en, 1)

    def disable(self):
        self.coast()
        self.pi.write(self.r_en, 0)
        self.pi.write(self.l_en, 0)

    def coast(self):
        self.pi.set_PWM_dutycycle(self.rpwm, 0)
        self.pi.set_PWM_dutycycle(self.lpwm, 0)

    def drive(self, value):
        """value in [-PWM_RANGE, +PWM_RANGE]. Only one half-bridge is ever driven."""
        if self.invert:
            value = -value
        value = clamp(int(round(value)), -PWM_RANGE, PWM_RANGE)
        if value > 0:                                  # forward
            self.pi.set_PWM_dutycycle(self.lpwm, 0)    # kill reverse first
            self.pi.set_PWM_dutycycle(self.rpwm, value)
        elif value < 0:                                # reverse
            self.pi.set_PWM_dutycycle(self.rpwm, 0)    # kill forward first
            self.pi.set_PWM_dutycycle(self.lpwm, -value)
        else:                                          # coast
            self.pi.set_PWM_dutycycle(self.rpwm, 0)
            self.pi.set_PWM_dutycycle(self.lpwm, 0)

    def actual_frequency(self):
        return self.pi.get_PWM_frequency(self.rpwm)


class Rover:
    def __init__(self, pi):
        self.pi = pi
        # My fair lady.
        self.motors = {
            mid: Motor(pi, f"M{mid}", MOTOR_PINS[mid], INVERT.get(mid, False))
            for mid in MOTOR_PINS
        }
        self.level = DEFAULT_LEVEL
        self.estopped = False

    def setup(self):
        for m in self.motors.values():
            m.setup()

    def arm(self):
        self.estopped = False
        for m in self.motors.values():
            m.enable()

    def estop(self):
        self.estopped = True
        for m in self.motors.values():
            m.disable()

    def cleanup(self):
        for m in self.motors.values():
            m.disable()

    def change_speed(self, delta):
        self.level = clamp(self.level + delta, 0, len(SPEED_LEVELS) - 1)

    @property
    def speed_name(self):
        return SPEED_LEVELS[self.level][0]

    @property
    def duty(self):
        pct = SPEED_LEVELS[self.level][1]
        return int(round(pct / 100.0 * PWM_RANGE))

    def _compute(self, cmd):
        """Return (left_signed, right_signed) duty for a command string."""
        d = self.duty
        if cmd == "forward":
            return d, d
        if cmd == "backward":
            return -d, -d
        inside = int(round(TURN_RATIO * d))
        if TURN_MODE == "spin":
            inside = -inside
        if cmd == "left":      # right side drives, left side slows/reverses
            return inside, d
        if cmd == "right":     # left side drives, right side slows/reverses
            return d, inside
        return 0, 0            # coast

    def apply(self, cmd):
        if self.estopped:
            return
        left, right = self._compute(cmd)
        for mid in LEFT_MOTORS:
            self.motors[mid].drive(left)
        for mid in RIGHT_MOTORS:
            self.motors[mid].drive(right)
