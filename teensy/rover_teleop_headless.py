#!/usr/bin/env python3
"""
Headless / SSH teleop, Teensy serial path. No display needed on the Pi.

Video goes out over the network for VLC (see ../stream.sh); you drive from an SSH
terminal and commands go to the Teensy 4.1 over serial. The port is auto-detected
by USB id. Linux only (termios).

Run, in an interactive SSH session:
    python3 rover_teleop_headless.py

Controls (type in the terminal, no Enter needed):
    w / s    forward / backward
    a / d    turn left / turn right
    q / e    speed down / up   (also - / +)
    space    emergency stop (sends X, latched)
    r        re-arm after e-stop
    x        quit (Ctrl-C also works)
    no key   coast stop after COMMAND_TIMEOUT

Needs pyserial. A terminal cannot see key-release, so hold the key (auto-repeat
sustains it); release coasts after COMMAND_TIMEOUT.
"""

import sys
import time
import select
import termios
import tty

import serial

from teensy_link import TeensyLink
from rover_drive import Rover
from rover_config import SPEED_LEVELS, COMMAND_TIMEOUT, HEARTBEAT_S

POLL = 0.05


def status_line(rover, cmd):
    name, pct = SPEED_LEVELS[rover.level]
    state = "E-STOP (r to re-arm)" if rover.estopped else "ARMED"
    return f"[{state}] cmd={cmd:<8} speed={name} ({pct}%)"


def main():
    if not sys.stdin.isatty():
        print("Run this in an interactive terminal (an SSH session), not piped.")
        sys.exit(1)

    try:
        link = TeensyLink()
    except serial.SerialException as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    print(f"Connected to Teensy on {link.port}")

    rover = Rover(link)

    print("\n*** MOTORS WILL GO LIVE. Wheels off the ground or chassis blocked up. ***")
    try:
        input("Press ENTER to arm, or Ctrl-C to abort... ")
    except KeyboardInterrupt:
        link.close()
        sys.exit(0)

    rover.arm()
    cmd = "coast"
    last_drive_time = 0.0
    last_heartbeat = time.time()
    last_printed = None

    print("Controls: w/s a/d  q/e speed  space=estop  r=rearm  x=quit")

    fd = sys.stdin.fileno()
    old_attr = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)   # char-at-a-time; Ctrl-C still works (ISIG on)
        while True:
            ready, _, _ = select.select([sys.stdin], [], [], POLL)
            now = time.time()

            while ready:
                ch = sys.stdin.read(1)
                if ch in ("x", "X"):
                    raise KeyboardInterrupt
                elif ch == " ":
                    rover.estop(); cmd = "coast"
                elif ch in ("r", "R"):
                    rover.arm(); cmd = "coast"
                elif ch in ("e", "E", "+", "="):
                    rover.change_speed(+1)
                elif ch in ("q", "Q", "-", "_"):
                    rover.change_speed(-1)
                elif not rover.estopped:
                    if ch in ("w", "W"):
                        cmd = "forward"; last_drive_time = now
                    elif ch in ("s", "S"):
                        cmd = "backward"; last_drive_time = now
                    elif ch in ("a", "A"):
                        cmd = "left"; last_drive_time = now
                    elif ch in ("d", "D"):
                        cmd = "right"; last_drive_time = now
                ready, _, _ = select.select([sys.stdin], [], [], 0)

            # Watchdog: no drive key recently -> coast stop.
            if cmd in ("forward", "backward", "left", "right") and \
               (now - last_drive_time) > COMMAND_TIMEOUT:
                cmd = "coast"

            rover.apply(cmd)

            # Heartbeat so the firmware failsafe stays fed while a key is held.
            if now - last_heartbeat >= HEARTBEAT_S:
                rover.heartbeat()
                last_heartbeat = now

            state = (rover.estopped, cmd, rover.level)
            if state != last_printed:
                print(status_line(rover, cmd))
                last_printed = state

    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_attr)
        link.close()
        print("\nShut down cleanly. Sent X to the Teensy, serial closed.")


if __name__ == "__main__":
    main()
