# Teensy control path (host side)

Same teleop UX as the Pi bring-up stack one level up, but motor commands go to the
Teensy 4.1 over USB serial instead of GPIO. The Teensy owns PWM, direction, and
enables. Use this path once the Teensy firmware is in the loop. The pigpio stack
at the repo root is for bench-testing motors directly off the Pi.

## Files
- `rover_config.py`           -- serial settings + the two CONFIRM switches
- `teensy_link.py`            -- serial protocol layer (open, drive, stop, status)
- `rover_drive.py`            -- shared Rover logic (used by both teleops)
- `rover_teleop.py`           -- GUI teleop (local display)
- `rover_teleop_headless.py`  -- SSH / no-display teleop (drive from a terminal)

## Which teleop
- Display attached to the Pi:  `rover_teleop.py`
- No display, drive over SSH:  `rover_teleop_headless.py`  + VLC for video
  (run `../stream.sh` on the Pi, open `http://<pi-ip>:8080/` in VLC). Linux only.

## Dependencies
    pip install pyserial        # imports as 'serial'
    # plus opencv (cv2) for the GUI version

## Run (headless / field)
    # terminal 1 on the Pi:   bash ../stream.sh      (needs ffmpeg)
    # VLC on the laptop:      http://<pi-ip>:8080/
    # terminal 2 (SSH):       cd teensy && python3 rover_teleop_headless.py

## Serial protocol (firmware reference)
- 115200 baud, line-based, `\n` terminated.
- Set speed: `L <n> <pct>` / `R <n> <pct>`, pct -100..100, negative = reverse.
  Multiple per line, comma-separated. Bulk all 6 in one string is supported.
- Stop all: `X`
- Query: `?` -> CSV of 6 speeds, M1..M6 order, e.g. `30,30,0,-40,0,0`
- Port: `COM3` (Windows dev) / `/dev/ttyACM0` (Pi/Jetson)

## Three items to confirm with firmware before driving
1. Right-side numbering: `R 1/2/3` (per-side) or `R 4/5/6` (flat)? Set in `LEFT_TOKENS`/`RIGHT_TOKENS`.
2. Forward sign: does +pct on both sides drive straight forward? If a side runs
   backward, flip `LEFT_SIGN` / `RIGHT_SIGN` to -1.
3. Firmware failsafe: the Teensy must stop all motors if it sees no command for
   ~300ms. The host heartbeat (`HEARTBEAT_S`, 0.2s) feeds it but cannot protect
   against a dropped USB link. Keep the heartbeat under the firmware timeout.
