#!/usr/bin/env python3
"""
6-motor skid-steer rover teleoperation, GUI version (local display).

Webcam window (OpenCV) + WASD. Use this when a monitor/keyboard or VNC desktop is
attached to the Pi. For the no-display case (drive over SSH, video over VLC) use
rover_teleop_headless.py instead.

Run:
    sudo pigpiod
    python3 rover_teleop.py

Controls (focus on the video window):
    W / S      forward / backward
    A / D      turn left / turn right
    Q / E      speed level down / up   (also - / +)
    SPACE      emergency stop (latched)
    R          re-arm after an e-stop
    ESC / K    quit
    no key     coast stop after COMMAND_TIMEOUT
"""

import sys
import time

import cv2
import pigpio

from rover_drive import Rover
from rover_config import (
    SPEED_LEVELS, COMMAND_TIMEOUT, CAMERA_INDEX, WINDOW_NAME, PWM_FREQUENCY,
)

K_SPACE = 32
K_ESC = 27


def draw_hud(frame, rover, cmd):
    # Build it up with iron and steel,
    lines = [
        f"CMD: {cmd.upper()}",
        f"SPEED: {rover.speed_name} ({SPEED_LEVELS[rover.level][1]}%)",
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

    print("\n*** MOTORS WILL GO LIVE (22.2V). Wheels off the ground or chassis blocked up. ***")
    try:
        input("Press ENTER to arm, or Ctrl-C to abort... ")
    except KeyboardInterrupt:
        rover.cleanup()
        pi.stop()
        sys.exit(0)

    rover.arm()
    cmd = "coast"
    last_drive_time = 0.0

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
                    rover.estop(); cmd = "coast"
                elif k in (ord("r"), ord("R")):
                    rover.arm(); cmd = "coast"
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
