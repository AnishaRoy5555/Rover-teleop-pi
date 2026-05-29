#!/usr/bin/env python3
"""
6-motor skid-steer rover teleoperation, Teensy serial control path.

Same operator UX as the pigpio bring-up version (webcam window + WASD), but motor
commands go to the Teensy 4.1 over USB serial instead of GPIO. The Teensy owns
PWM, direction, and enables.

Run:
    python3 rover_teleop.py        # with a monitor + keyboard, or over VNC

Controls (focus on the video window):
    W / S      forward / backward
    A / D      turn left / turn right
    Q / E      speed level down / up   (also - / +)
    SPACE      emergency stop (sends X, latched)
    R          re-arm after an e-stop
    ESC / K    quit (clean shutdown, sends X)
    no key     coast stop after COMMAND_TIMEOUT

Needs: opencv (cv2), pyserial.   Manual teleop only, no autonomy.
"""

import sys
import time

import cv2
import serial

from teensy_link import TeensyLink
from rover_config import (
    SPEED_LEVELS, DEFAULT_LEVEL, TURN_RATIO, TURN_MODE,
    COMMAND_TIMEOUT, HEARTBEAT_S, CAMERA_INDEX, WINDOW_NAME, SERIAL_PORT,
)

K_SPACE = 32
K_ESC = 27


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


def draw_hud(frame, rover, cmd):
    lines = [
        f"CMD: {cmd.upper()}",
        f"SPEED: {rover.speed_name} ({rover.pct}%)",
        f"STATE: {'E-STOP (press R to re-arm)' if rover.estopped else 'ARMED'}",
    ]
    color = (0, 0, 255) if rover.estopped else (0, 255, 0)
    y = 28
    for text in lines:
        cv2.putText(frame, text, (12, y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(frame, text, (12, y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, color, 1, cv2.LINE_AA)
        y += 30
    return frame


def main():
    try:
        link = TeensyLink()
    except serial.SerialException as e:
        print(f"ERROR: cannot open {SERIAL_PORT}: {e}")
        print("  Check the port (COM3 on Windows, /dev/ttyACM0 on the Jetson) and "
              "that the Teensy is plugged in.")
        sys.exit(1)

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(f"ERROR: cannot open camera index {CAMERA_INDEX}.")
        link.close()
        sys.exit(1)

    rover = Rover(link)

    print("\n*** MOTORS WILL GO LIVE. Wheels off the ground or chassis blocked up. ***")
    try:
        input("Press ENTER to arm, or Ctrl-C to abort... ")
    except KeyboardInterrupt:
        print("\nAborted.")
        link.close()
        cap.release()
        sys.exit(0)

    rover.arm()
    cmd = "coast"
    last_drive_time = 0.0
    last_heartbeat = time.time()

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

            # Host watchdog: no drive key recently -> coast stop.
            if cmd in ("forward", "backward", "left", "right") and \
               (now - last_drive_time) > COMMAND_TIMEOUT:
                cmd = "coast"

            rover.apply(cmd)

            # Heartbeat so the firmware failsafe stays fed while a key is held.
            if now - last_heartbeat >= HEARTBEAT_S:
                rover.heartbeat()
                last_heartbeat = now

            draw_hud(frame, rover, cmd)
            cv2.imshow(WINDOW_NAME, frame)

    finally:
        link.close()
        cap.release()
        cv2.destroyAllWindows()
        print("Shut down cleanly. Sent X to the Teensy, serial closed.")


if __name__ == "__main__":
    main()
