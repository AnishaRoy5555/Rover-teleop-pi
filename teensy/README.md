# Teensy control path (host side)

Same teleop UX as the Pi bring-up stack one level up, but motor commands go to the
Teensy 4.1 over USB serial instead of GPIO. The Teensy owns PWM, direction, and
enables. Use this path once the Teensy firmware is in the loop; use the Pi stack
at the repo root for bench-testing motors directly.

## Files
- `rover_config.py` -- serial settings + the two CONFIRM switches
- `teensy_link.py`  -- serial protocol layer (open, drive, stop, status)
- `rover_teleop.py` -- the app you drive with

## Dependencies
    pip install pyserial        # imports as 'serial'
    # plus opencv (cv2), same as the Pi stack

## Run
    cd teensy
    python3 rover_teleop.py

## Serial protocol (firmware reference)
- 115200 baud, line-based, `\n` terminated.
- Set speed: `L <n> <pct>` / `R <n> <pct>`, pct -100..100, negative = reverse.
  Multiple per line, comma-separated. Bulk all 6 in one string is supported.
- Stop all: `X`
- Query: `?` -> CSV of 6 speeds, M1..M6 order, e.g. `30,30,0,-40,0,0`
- Port: `COM3` (Windows dev) / `/dev/ttyACM0` (Jetson)

## Three items to confirm with firmware before driving
1. Right-side numbering: `R 1/2/3` (per-side) or `R 4/5/6` (flat)? Set in `LEFT_TOKENS`/`RIGHT_TOKENS`.
2. Forward sign: does +pct on both sides drive straight forward? If a side runs
   backward, flip `LEFT_SIGN` / `RIGHT_SIGN` to -1.
3. Firmware failsafe: the Teensy must stop all motors if it sees no command for
   ~300ms. The host heartbeat (`HEARTBEAT_S`, 0.2s) feeds it but cannot protect
   against a dropped USB link. Keep the heartbeat under the firmware timeout.
