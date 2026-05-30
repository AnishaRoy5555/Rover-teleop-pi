"""
Config for the Teensy 4.1 control path.

The pigpio pin map / daemon / software INVERT are gone: the Teensy owns motor
I/O now. Only the serial link and the motion shaping remain. Two items below are
marked CONFIRM and must match the firmware before driving.
"""

# --- Serial link to the Teensy 4.1 ---
# SERIAL_PORT = None means auto-detect by USB VID:PID below (the /dev/ttyACM*
# number changes between plug-ins, so we find the Teensy by its USB id instead).
# Set an explicit path here only if you want to force a specific port.
SERIAL_PORT = None
TEENSY_VID = 0x16C0           # Van Ooijen Technische Informatica (Teensy)
TEENSY_PID = 0x0483           # Teensyduino Serial. Set to None to match any 16c0
                              # device if the Teensy USB type is changed.
SERIAL_BAUD = 115200
SERIAL_TIMEOUT_S = 1.0
CONNECT_SETTLE_S = 2.0        # wait after opening. Teensy 4.1 may not reset on open
                              # like an Arduino does; harmless if not needed. (CONFIRM)

# --- Command addressing (CONFIRM WITH PARTH) ---
# Example used "R 3"; Anisha's bulk used "R 4..6". Set whichever the firmware parses.
LEFT_TOKENS = ["L 1", "L 2", "L 3"]
RIGHT_TOKENS = ["R 1", "R 2", "R 3"]    # if the firmware wants R 4/5/6, change here

# Send one command per line instead of all 6 in one comma-separated line.
# Individual commands are confirmed working; the bulk line was only driving the
# right side, so the firmware's multi-command parsing is unreliable. Keep this
# True unless/until the firmware bulk parser is fixed and verified.
ONE_CMD_PER_LINE = True

# --- Forward-direction sign per side ---
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
