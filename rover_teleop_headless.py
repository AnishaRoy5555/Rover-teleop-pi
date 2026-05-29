#!/usr/bin/env python3
"""
Headless / SSH teleop for the Pi. No display needed on the Pi.

Video goes out over the network for VLC (see stream.sh); you drive from an SSH
terminal. Keys are read from the terminal in cbreak mode (termios), motors driven
via pigpio. Linux only.

Run, in an interactive SSH session:
    sudo pigpiod
    python3 rover_teleop_headless.py

Controls (type in the terminal, no Enter needed):
    w / s    forward / backward
    a / d    turn left / turn right
    q / e    speed down / up   (also - / +)
    space    emergency stop (latched)
    r        re-arm after e-stop
    x        quit (Ctrl-C also works)
    no key   coast stop after COMMAND_TIMEOUT

Note: a terminal cannot see key-release, so hold the key (terminal auto-repeat
sustains it) and release coasts after COMMAND_TIMEOUT. Same limitation as the
GUI version; the watchdog is the safety net.
"""

import sys
import time
import select
import termios
import tty

import pigpio

from rover_drive import Rover
from rover_config import SPEED_LEVELS, COMMAND_TIMEOUT, PWM_FREQUENCY

POLL = 0.05  # s, loop poll interval so the watchdog runs even with no input


def status_line(rover, cmd):
    name, pct = SPEED_LEVELS[rover.level]
    state = "E-STOP (r to re-arm)" if rover.estopped else "ARMED"
    return f"[{state}] cmd={cmd:<8} speed={name} ({pct}%)"


def main():
    if not sys.stdin.isatty():
        print("Run this in an interactive terminal (an SSH session), not piped.")
        sys.exit(1)

    pi = pigpio.pi()
    if not pi.connected:
        print("ERROR: pigpio daemon not running. Start it with:  sudo pigpiod")
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
    last_printed = None

    print("Controls: w/s a/d  q/e speed  space=estop  r=rearm  x=quit")

    fd = sys.stdin.fileno()
    old_attr = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)   # char-at-a-time; Ctrl-C still works (ISIG on)
        while True:
            ready, _, _ = select.select([sys.stdin], [], [], POLL)
            now = time.time()

            # Drain everything buffered this tick (auto-repeat can stack chars).
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

            state = (rover.estopped, cmd, rover.level)
            if state != last_printed:
                print(status_line(rover, cmd))
                last_printed = state

    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_attr)
        rover.cleanup()
        pi.stop()
        print("\nShut down cleanly. All enables LOW, all PWM 0.")


if __name__ == "__main__":
    main()
