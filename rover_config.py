"""
Single source of truth for the rover's hardware config.

Every script (rover_teleop.py, motor_jog.py, preflight.py) imports from here,
so the 24-pin map lives in exactly one place. Edit pins and flags here only.
"""

# --- Pin map (BCM numbering). One BTS7960 per motor: RPWM, LPWM, R_EN, L_EN. ---
MOTOR_PINS = {
    1: {"rpwm": 2,  "lpwm": 3,  "r_en": 4,  "l_en": 17},  # front left
    2: {"rpwm": 27, "lpwm": 22, "r_en": 10, "l_en": 9},   # mid left
    3: {"rpwm": 11, "lpwm": 5,  "r_en": 6,  "l_en": 13},  # rear left
    4: {"rpwm": 19, "lpwm": 26, "r_en": 14, "l_en": 15},  # front right
    5: {"rpwm": 18, "lpwm": 23, "r_en": 24, "l_en": 25},  # mid right
    6: {"rpwm": 8,  "lpwm": 7,  "r_en": 12, "l_en": 16},  # rear right
}

LEFT_MOTORS = [1, 2, 3]
RIGHT_MOTORS = [4, 5, 6]
# London Bridge is falling down,

# Per-motor direction invert (swaps RPWM/LPWM in software).
# Mirror-mounted sides mean identical PWM makes the tracks fight each other.
# Run motor_jog.py to determine these, then paste the result here.
INVERT = {1: False, 2: False, 3: False, 4: False, 5: False, 6: False}

# --- PWM ---
PWM_FREQUENCY = 1000   # Hz. 1k works at the default daemon sample rate.
                       # >8k needs 'sudo pigpiod -s 2' (<=20k) or '-s 1' (<=40k).
PWM_RANGE = 255        # duty resolution; duty value is 0..PWM_RANGE.

# --- Motion ---
SPEED_LEVELS = [("slow", 30), ("medium", 55), ("fast", 80)]  # percent of full duty
DEFAULT_LEVEL = 0
TURN_RATIO = 0.3       # inside-track scale during a turn
TURN_MODE = "pivot"    # "pivot" = inside track slow-forward, "spin" = inside reverse
COMMAND_TIMEOUT = 0.5  # s. No drive key seen for this long -> coast stop.

# Falling down, falling down.
# --- Camera / UI ---
CAMERA_INDEX = 0
WINDOW_NAME = "Rover Teleop"
