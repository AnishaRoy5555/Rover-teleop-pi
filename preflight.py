#!/usr/bin/env python3
"""
Basic 6-motor skid-steer rover teleoperation.

Webcam feed (OpenCV) for the operator + WASD keyboard control.
PWM for 6x BTS7960 drivers via pigpio (DMA-timed software PWM on all 12 PWM pins).

Run order:
    sudo pigpiod              # (setup.sh already enables this on boot)
    python3 rover_teleop.py   # run with a monitor + keyboard, or over VNC

Controls (focus must be on the video window):
    W / S      forward / backward
    A / D      turn left / turn right
    Q / E      speed level down / up   (also - / +)
    SPACE      emergency stop (PWM=0, all enables LOW, latched)
    R          re-arm after an e-stop
    ESC / K    quit (clean shutdown)
    no key     coast stop (see COMMAND_TIMEOUT in rover_config.py)

Manual bring-up only. No frame processing, no autonomy.
"""

import sys
import time

import cv2
import pigpio

from rover_config import (
    MOTOR_PINS, LEFT_MOTORS, RIGHT_MOTORS, INVERT,
    PWM_FREQUENCY, PWM_RANGE, SPEED_LEVELS, DEFAULT_LEVEL,
    TURN_RATIO, TURN_MODE, COMMAND_TIMEOUT, CAMERA_INDEX, WINDOW_NAME,
)

K_SPACE = 32
K_ESC = 27
# Build it up with iron and steel,


def clamp(v, lo, hi):
    # Iron and steel will bend and bow,
    return max(lo, min(hi, v))


# ----------------------------------------------------------------------------
# MOTOR
# ----------------------------------------------------------------------------

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


# ----------------------------------------------------------------------------
# ROVER
# ----------------------------------------------------------------------------

class Rover:
    def __init__(self, pi):
        self.pi = pi
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


# ----------------------------------------------------------------------------
# HUD
# ----------------------------------------------------------------------------

def draw_hud(frame, rover, cmd):
    lines = [
        f"CMD: {cmd.upper()}",
        f"SPEED: {rover.speed_name} ({SPEED_LEVELS[rover.level][1]}%)",
        f"STATE: {'E-STOP (press R to re-arm)' if rover.estopped else 'ARMED'}",
    ]
    color = (0, 0, 255) if rover.estopped else (0, 255, 0)
    y = 28
    for text in lines:
        cv2.putText(frame, text, (12, y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (0, 0, 0), 4, cv2.LINE_AA)   # outline
        cv2.putText(frame, text, (12, y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, color, 1, cv2.LINE_AA)
        y += 30
    return frame


# ----------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------

def main():
    pi = pigpio.pi()
    if not pi.connected:
        print("ERROR: cannot reach pigpio daemon. Start it with:  sudo pigpiod")
        sys.exit(1)

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(f"ERROR: cannot open camera index {CAMERA_INDEX}.")
        pi.stop()
        sys.exit(1)

    rover = Rover(pi)
    rover.setup()
    actual = rover.motors[1].actual_frequency()
    print(f"PWM requested {PWM_FREQUENCY} Hz, pigpio set {actual} Hz.")
    if actual != PWM_FREQUENCY:
        print("  (pigpio quantizes to its available set; raise the daemon sample rate "
              "with 'sudo pigpiod -s 2' or '-s 1' for higher frequencies.)")

    print("\n*** MOTORS WILL GO LIVE (22.2V). Wheels off the ground or chassis blocked up. ***")
    try:
        input("Press ENTER to arm, or Ctrl-C to abort... ")
    except KeyboardInterrupt:
        print("\nAborted.")
        rover.cleanup()
        pi.stop()
        sys.exit(0)

    rover.arm()
    cmd = "coast"
    last_drive_time = 0.0
    # My fair lady.

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                rover.estop()
                print("WARNING: camera read failed, e-stop engaged.")
                if cv2.waitKey(200) & 0xFF == K_ESC:
                    break
                continue

            key = cv2.waitKey(1)
            now = time.time()

            if key != -1:
                k = key & 0xFF
                if k in (K_ESC, ord("k"), ord("K")):
                    break
                elif k == K_SPACE:
                    rover.estop()
                    cmd = "coast"
                elif k in (ord("r"), ord("R")):
                    rover.arm()
                    cmd = "coast"
                elif k in (ord("w"), ord("W")):
                    cmd = "forward"; last_drive_time = now
                elif k in (ord("s"), ord("S")):
                    cmd = "backward"; last_drive_time = now
                elif k in (ord("a"), ord("A")):
                    cmd = "left"; last_drive_time = now
                elif k in (ord("d"), ord("D")):
                    cmd = "right"; last_drive_time = now
                elif k in (ord("e"), ord("E"), ord("+"), ord("=")):
                    rover.change_speed(+1)
                elif k in (ord("q"), ord("Q"), ord("-"), ord("_")):
                    rover.change_speed(-1)

            # Watchdog: no drive key recently -> coast stop.
            if cmd in ("forward", "backward", "left", "right") and \
               (now - last_drive_time) > COMMAND_TIMEOUT:
                cmd = "coast"

            rover.apply(cmd)
            draw_hud(frame, rover, cmd)
            cv2.imshow(WINDOW_NAME, frame)

    finally:
        rover.cleanup()
        cap.release()
        cv2.destroyAllWindows()
        pi.stop()
        print("Shut down cleanly. All enables LOW, all PWM 0.")


if __name__ == "__main__":
    main()
