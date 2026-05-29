# Rover Pi bring-up stack

Manual teleoperation for the 6-motor skid-steer rover: webcam window + WASD,
PWM to 6x BTS7960 over pigpio. This is throwaway bring-up gear to de-risk the
hardware before the Jetson / ROS2 / Teensy stack exists. Nothing here ports to
the competition build except the knowledge you gain (direction flags, PWM freq,
confirmed wiring).

## Files

| File              | Layer | What it does                                              |
|-------------------|-------|-----------------------------------------------------------|
| `setup.sh`        | 1-3   | Installs packages, enables pigpiod, frees GPIO2/3 & 14/15 |
| `rover_config.py` | -     | Single source of truth: pin map, flags, PWM, speeds       |
| `preflight.py`    | -     | Verifies daemon + pins + camera, spins nothing            |
| `motor_jog.py`    | 5     | Jogs one motor at a time to set the INVERT flags          |
| `rover_teleop.py` | 6     | The teleop app you actually drive with                    |

The OS, packages, and daemon are layers 1-3. A desktop session (monitor or VNC)
is layer 4. Wiring is layer 5. The app is layer 6.

## One-time setup

On a dev machine, copy the folder to the Pi:

    scp -r rover_pi_stack/ pi@<rover-ip>:~

On the Pi:

    cd ~/rover_pi_stack
    bash setup.sh
    sudo reboot            # only needed if serial/I2C were changed

`setup.sh` is idempotent. Re-run it any time.

## Layer 4: display

`cv2.imshow` needs a screen and keyboard focus. Use a monitor + keyboard on the
Pi, or VNC into its desktop. Plain SSH will not work (no window, no key capture).

## Layer 5: wiring (do once, verify before arming)

- Pi GPIO -> each BTS7960 logic pin (RPWM/LPWM/R_EN/L_EN) per `rover_config.py`.
- Common ground between the Pi and every driver's logic ground. Required.
- 22.2V LiPo -> distribution board -> driver power side (separate from Pi 5V).
- USB webcam shows up as index 0 (change `CAMERA_INDEX` if not).

## Bring-up sequence

    python3 preflight.py     # daemon, pin sanity, camera. Spins nothing.
    python3 motor_jog.py     # WHEELS OFF GROUND. Sets the INVERT flags.

`motor_jog.py` prints an `INVERT = {...}` line at the end. Paste it into
`rover_config.py`, replacing the existing line. This is what makes `W` drive the
whole chassis forward instead of the two sides fighting each other.

## Run

    python3 rover_teleop.py

Then in the video window:

| Key       | Action                                  |
|-----------|-----------------------------------------|
| W / S     | forward / backward                      |
| A / D     | turn left / turn right                  |
| Q / E     | speed level down / up (also `-` / `+`)  |
| SPACE     | emergency stop (latched)                |
| R         | re-arm after e-stop                     |
| ESC / K   | quit                                    |

## Gotchas worth re-reading

1. **Mirrored sides.** Set the INVERT flags with `motor_jog.py` first or the
   tracks fight each other.
2. **cv2 can't see key-release.** Hold the key down (OS key-repeat sustains it);
   release coasts after `COMMAND_TIMEOUT` (~0.5s). For crisp hold-to-move with
   instant release, swap to a `pynput` listener (not done here to stay on the
   dependencies you listed).
3. **PWM frequency.** 1kHz works as-is. Above 8kHz, restart the daemon with
   `sudo pigpiod -s 2` (<=20kHz) or `-s 1` (<=40kHz).
4. **Pin peripherals.** GPIO2/3 are I2C (weak onboard pull-ups, harmless for
   outputs), GPIO14/15 are UART. `setup.sh` frees them; reboot if it changed them.
5. **E-stop is latched.** SPACE drops enables LOW and stays stopped; press R to
   re-arm. Startup also requires an ENTER confirmation before motors go live.
