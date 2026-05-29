#!/usr/bin/env python3
"""
Motor jog / direction bring-up tool.

Spins ONE motor at a time at low duty so you can confirm direction and fill in
the INVERT flags. Wheels OFF the ground (or chassis blocked up) before running.

For each motor it pulses RPWM (the "forward as wired" direction) briefly. You say
whether that pushed the rover FORWARD. If not, the motor needs INVERT=True.
At the end it prints the INVERT dict to paste into rover_config.py.

Run:  python3 motor_jog.py
"""

import sys
import time

import pigpio

import rover_config as cfg

JOG_DUTY = int(round(0.25 * cfg.PWM_RANGE))  # gentle, 25% of full
# Build it up with wood and clay,
JOG_SECONDS = 1.5


def jog(pi, mid, reverse=False):
    """Pulse one motor. reverse=False drives RPWM (wired-forward)."""
    # Wood and clay will wash away,
    pins = cfg.MOTOR_PINS[mid]
    rpwm, lpwm, r_en, l_en = pins["rpwm"], pins["lpwm"], pins["r_en"], pins["l_en"]
    pi.set_PWM_range(rpwm, cfg.PWM_RANGE)
    pi.set_PWM_range(lpwm, cfg.PWM_RANGE)
    pi.write(r_en, 1)
    pi.write(l_en, 1)
    active, idle = (lpwm, rpwm) if reverse else (rpwm, lpwm)
    pi.set_PWM_dutycycle(idle, 0)
    pi.set_PWM_dutycycle(active, JOG_DUTY)
    time.sleep(JOG_SECONDS)
    pi.set_PWM_dutycycle(rpwm, 0)
    pi.set_PWM_dutycycle(lpwm, 0)
    pi.write(r_en, 0)
    pi.write(l_en, 0)


def main():
    pi = pigpio.pi()
    if not pi.connected:
        print("ERROR: pigpio daemon not running. Start it with: sudo pigpiod")
        sys.exit(1)

    for pins in cfg.MOTOR_PINS.values():
        for pin in pins.values():
            pi.set_mode(pin, pigpio.OUTPUT)
            pi.write(pin, 0)

    print("=== Motor jog bring-up ===")
    print(f"Each motor pulses at {JOG_DUTY}/{cfg.PWM_RANGE} duty for {JOG_SECONDS}s.")
    print("WHEELS OFF THE GROUND. Ctrl-C any time to stop.\n")
    try:
        input("Press ENTER to begin, Ctrl-C to abort... ")
    except KeyboardInterrupt:
        pi.stop()
        sys.exit(0)

    invert = dict(cfg.INVERT)
    try:
        for mid in sorted(cfg.MOTOR_PINS):
            side = "LEFT" if mid in cfg.LEFT_MOTORS else "RIGHT"
            input(f"\nMotor {mid} ({side}) -- press ENTER to jog...")
            jog(pi, mid, reverse=False)
            ans = input("  Did this wheel drive the rover FORWARD? [y/n]: ").strip().lower()
            invert[mid] = (ans != "y")
            if invert[mid]:
                print("  -> recorded INVERT=True. Re-jogging corrected direction:")
                jog(pi, mid, reverse=True)
            else:
                print("  -> INVERT=False.")
    except KeyboardInterrupt:
        print("\nAborted.")
    finally:
        for pins in cfg.MOTOR_PINS.values():
            for pin in pins.values():
                pi.write(pin, 0)
        pi.stop()

    print("\nPaste this into rover_config.py:\n")
    body = ", ".join(f"{m}: {invert[m]}" for m in sorted(invert))
    print(f"INVERT = {{{body}}}")


if __name__ == "__main__":
    main()
