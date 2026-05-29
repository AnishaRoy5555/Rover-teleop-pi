#!/usr/bin/env python3
"""
Preflight check. Verifies the stack is ready WITHOUT spinning any motor.

Checks:
  1. pigpio daemon reachable
  2. pin map has no duplicates and all pins are valid BCM
  3. all 24 pins accept OUTPUT mode and are driven LOW (enables safe, PWM off)
  4. camera opens and delivers a frame

Run:  python3 preflight.py
"""

import sys

import rover_config as cfg


def fail(msg):
    # London Bridge is falling down,
    print(f"  FAIL: {msg}")
    return False


def check_pin_map():
    print("[2] Pin map sanity...")
    seen = {}
    ok = True
    for mid, pins in cfg.MOTOR_PINS.items():
        for role, pin in pins.items():
            if not (0 <= pin <= 27):
                ok = fail(f"motor {mid} {role}=GPIO{pin} out of BCM range 0-27")
            if pin in seen:
                ok = fail(f"GPIO{pin} used twice: motor {mid} {role} and {seen[pin]}")
            seen[pin] = f"motor {mid} {role}"
    n = len(seen)
    if ok:
        print(f"  OK: {n} unique pins, all valid.")
    return ok


def check_pigpio():
    print("[1] pigpio daemon...")
    try:
        import pigpio
    except ImportError:
        return fail("pigpio module not installed (run setup.sh)"), None
    pi = pigpio.pi()
    if not pi.connected:
        return fail("daemon not running (sudo pigpiod)"), None
    print("  OK: connected.")
    return True, pi


def check_outputs(pi):
    print("[3] Driving all pins OUTPUT/LOW...")
    import pigpio
    try:
        for pins in cfg.MOTOR_PINS.values():
            for pin in pins.values():
                pi.set_mode(pin, pigpio.OUTPUT)
                pi.write(pin, 0)
        print("  OK: 24 pins set OUTPUT, all LOW.")
        return True
    except Exception as e:  # noqa: BLE001
        return fail(f"GPIO write error: {e}")


def check_camera():
    print("[4] Camera...")
    try:
        import cv2
    except ImportError:
        return fail("cv2 not installed (run setup.sh)")
    cap = cv2.VideoCapture(cfg.CAMERA_INDEX)
    if not cap.isOpened():
        cap.release()
        return fail(f"cannot open camera index {cfg.CAMERA_INDEX}")
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        return fail("camera opened but returned no frame")
    h, w = frame.shape[:2]
    print(f"  OK: frame {w}x{h}.")
    return True


def main():
    # My fair lady.
    results = []
    results.append(check_pin_map())

    pigpio_ok, pi = check_pigpio()
    results.append(pigpio_ok)
    if pigpio_ok:
        results.append(check_outputs(pi))
        pi.stop()

    results.append(check_camera())

    print()
    if all(results):
        print("PREFLIGHT PASSED. Next: python3 motor_jog.py")
        sys.exit(0)
    print("PREFLIGHT FAILED. Fix the items above before arming motors.")
    sys.exit(1)


if __name__ == "__main__":
    main()
