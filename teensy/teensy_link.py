#!/usr/bin/env python3
"""
Serial transport to the Teensy 4.1 motor controller.

Protocol (per the firmware host-side reference):
  - 115200 baud, line-based, '\\n' terminated.
  - Set speed:  "L <n> <pct>" / "R <n> <pct>", pct in -100..100, negative = reverse.
                Multiple commands per line, comma-separated:  "L 1 30, R 1 -40"
  - Stop all:   "X"
  - Query:      "?"  -> CSV of 6 speeds, M1..M6 order, e.g. "30,30,0,-40,0,0"

The port is auto-detected by USB VID:PID (the /dev/ttyACM* number changes between
plug-ins), so there is no hardcoded path. The Teensy owns PWM, direction, enables,
and MUST own the failsafe timeout.

Needs pyserial:  pip install pyserial   (import name is 'serial')
"""

import time

import serial
from serial.tools import list_ports

import rover_config as cfg


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def find_teensy(vid=cfg.TEENSY_VID, pid=cfg.TEENSY_PID):
    """Return the device path of the first matching Teensy, or None."""
    for p in list_ports.comports():
        if p.vid == vid and (pid is None or p.pid == pid):
            return p.device
    return None


class TeensyLink:
    def __init__(self, port=None, baud=cfg.SERIAL_BAUD, settle=cfg.CONNECT_SETTLE_S):
        resolved = port or cfg.SERIAL_PORT or find_teensy()
        if resolved is None:
            raise serial.SerialException(
                f"No Teensy found by USB id {cfg.TEENSY_VID:04x}:{cfg.TEENSY_PID:04x}. "
                "Plug it in, or set SERIAL_PORT in rover_config.py.")
        self.port = resolved
        self.ser = serial.Serial(resolved, baud, timeout=cfg.SERIAL_TIMEOUT_S)
        time.sleep(settle)               # board may reset on open; harmless if not
        self.ser.reset_input_buffer()
        self._last_key = None
        self._last_lines = []

    def send(self, line):
        self.ser.write(f"{line}\n".encode("utf-8"))

    def _compose(self, left, right):
        """Build the line(s) to send for a given left/right percent."""
        parts = [f"{tok} {left}" for tok in cfg.LEFT_TOKENS]
        parts += [f"{tok} {right}" for tok in cfg.RIGHT_TOKENS]
        if cfg.ONE_CMD_PER_LINE:
            return parts                 # one command per line (safe default)
        return [", ".join(parts)]        # one bulk line (needs firmware bulk parser)

    def drive(self, left_pct, right_pct):
        """All 6 motors. left/right in -100..100 (rover frame)."""
        left = int(round(cfg.LEFT_SIGN * clamp(left_pct, -100, 100)))
        right = int(round(cfg.RIGHT_SIGN * clamp(right_pct, -100, 100)))
        key = (left, right)
        if key != self._last_key:        # send only on change, keeps the bus clean
            self._last_lines = self._compose(left, right)
            for line in self._last_lines:
                self.send(line)
            self._last_key = key

    def heartbeat(self):
        """Re-send the last command so the firmware watchdog stays fed."""
        for line in self._last_lines:
            self.send(line)

    def stop(self):
        self.send("X")
        self._last_key = "STOP"
        self._last_lines = ["X"]

    def get_status(self):
        """List of 6 ints, or None if empty/malformed (Anisha's fix, hardened)."""
        self.ser.reset_input_buffer()
        self.send("?")
        line = self.ser.readline().decode("utf-8", "ignore").strip()
        if not line:
            return None
        try:
            speeds = [int(x) for x in line.split(",")]
        except ValueError:               # non-numeric token in a partial line
            return None
        return speeds if len(speeds) == 6 else None

    def close(self):
        try:
            self.stop()
        finally:
            self.ser.close()
