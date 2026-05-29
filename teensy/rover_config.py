"""
Config for the Teensy 4.1 control path.

The pigpio pin map / daemon / software INVERT are gone: the Teensy owns motor
I/O now. Only the serial link and the motion shaping remain. Two items below are
marked CONFIRM and must match the firmware before driving.
"""

# --- Serial link to the Teensy 4.1 ---
SERIAL_PORT = "COM3"          # Windows dev box. On the Jetson use "/dev/ttyACM0".
SERIAL_BAUD = 115200
SERIAL_TIMEOUT_S = 1.0
CONNECT_SETTLE_S = 2.0        # wait after opening. Teensy 4.1 may not reset on open
                              # like an Arduino does; harmless if not needed. (CONFIRM)

# --- Command addressing (CONFIRM WITH PARTH) ---
# Example used "R 3"; Anisha's bulk used "R 4..6". Set whichever the firmware parses.
LEFT_TOKENS = ["L 1", "L 2", "L 3"]
RIGHT_TOKENS = ["R 1", "R 2", "R 3"]    # if the firmware wants R 4/5/6, change here

# --- Forward-direction sign per side (CONFIRM WITH PARTH) ---
# +1 means a positive percent drives that side forward in the rover frame.
# If +speed on a side drives the rover BACKWARD, flip that side to -1.
# This replaces the old per-motor INVERT dict (mirrored-mounting fix).
LEFT_SIGN = +1
RIGHT_SIGN = +1

# --- Motion shaping (reused unchanged from the bring-up stack) ---
SPEED_LEVELS = [("slow", 30), ("medium", 55), ("fast", 80)]  # percent, maps 1:1 to Teensy
DEFAULT_LEVEL = 0
TURN_RATIO = 0.3              # inside-track scale during a turn
TURN_MODE = "pivot"           # "pivot" = inside slow-forward, "spin" = inside reverse

# --- Safety / timing ---
COMMAND_TIMEOUT = 0.5         # host coast on no key. NOT a substitute for the firmware
                              # failsafe; it does nothing if the USB link drops.
HEARTBEAT_S = 0.2             # re-send current command to feed the firmware watchdog.
                              # Keep this comfortably under the firmware's stop timeout.

# --- Camera / UI ---
CAMERA_INDEX = 0
WINDOW_NAME = "Rover Teleop (Teensy)"
