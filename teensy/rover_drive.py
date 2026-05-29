#!/usr/bin/env python3
"""
Shared serial-backed rover drive layer (Teensy path).

Imported by rover_teleop.py (GUI) and rover_teleop_headless.py (SSH/no-display),
so the Rover logic lives in one place. Motor I/O goes through TeensyLink; the
Teensy owns PWM, direction, and enables.
"""

from rover_config import SPEED_LEVELS, DEFAULT_LEVEL, TURN_RATIO, TURN_MODE


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


class Rover:
    def __init__(self, link):
        self.link = link
        self.level = DEFAULT_LEVEL
        self.estopped = False

    def arm(self):
        self.estopped = False
        self.link.drive(0, 0)

    def estop(self):
        self.estopped = True
        self.link.stop()

    def change_speed(self, delta):
        self.level = clamp(self.level + delta, 0, len(SPEED_LEVELS) - 1)

    @property
    def speed_name(self):
        return SPEED_LEVELS[self.level][0]

    @property
    def pct(self):
        return SPEED_LEVELS[self.level][1]

    def _compute(self, cmd):
        """Return (left_pct, right_pct) in the rover frame."""
        p = self.pct
        if cmd == "forward":
            return p, p
        if cmd == "backward":
            return -p, -p
        inside = int(round(TURN_RATIO * p))
        if TURN_MODE == "spin":
            inside = -inside
        if cmd == "left":      # right side drives, left side slows/reverses
            return inside, p
        if cmd == "right":     # left side drives, right side slows/reverses
            return p, inside
        return 0, 0            # coast

    def apply(self, cmd):
        if self.estopped:
            return
        left, right = self._compute(cmd)
        self.link.drive(left, right)

    def heartbeat(self):
        if not self.estopped:
            self.link.heartbeat()
