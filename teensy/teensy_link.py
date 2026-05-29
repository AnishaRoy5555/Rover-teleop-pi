#!/usr/bin/env python3
"""
Serial transport to the Teensy 4.1 motor controller.

Protocol (per the firmware host-side reference):
  - 115200 baud, line-based, '\\n' terminated.
  - Set speed:  "L <n> <pct>" / "R <n> <pct>", pct in -100..100, negative = reverse.
                Multiple commands per line, comma-separated:  "L 1 30, R 1 -40"
  - Stop all:   "X"
  - Query:      "?"  -> CSV of 6 speeds, M1..M6 order, e.g. "30,30,0,-40,0,0"

Replaces the pigpio/GPIO layer. The Teensy owns PWM, direction, enables, and MUST
own the failsafe timeout (the host heartbeat only helps while the link is alive).

Needs pyserial:  pip install pyserial   (import name is 'serial')
"""

import time

import serial

import rover_config as cfg


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


class TeensyLink:
    def __init__(self, port=cfg.SERIAL_PORT, baud=cfg.SERIAL_BAUD,
                 settle=cfg.CONNECT_SETTLE_S):
        self.ser = serial.Serial(port, baud, timeout=cfg.SERIAL_TIMEOUT_S)
        time.sleep(settle)               # board may reset on open; harmless if not
        self.ser.reset_input_buffer()
        self._last_line = None

    def send(self, line):
        self.ser.write(f"{line}\n".encode("utf-8"))

    def drive(self, left_pct, right_pct):
        """All 6 motors in one line. left/right in -100..100 (rover frame)."""
        left = int(round(cfg.LEFT_SIGN * clamp(left_pct, -100, 100)))
        right = int(round(cfg.RIGHT_SIGN * clamp(right_pct, -100, 100)))
        parts = [f"{tok} {left}" for tok in cfg.LEFT_TOKENS]
        parts += [f"{tok} {right}" for tok in cfg.RIGHT_TOKENS]
        line = ", ".join(parts)
        if line != self._last_line:      # send only on change, keeps the bus clean
            self.send(line)
            self._last_line = line

    def heartbeat(self):
        """Re-send the last command so the firmware watchdog stays fed."""
        if self._last_line is not None:
            self.send(self._last_line)

    def stop(self):
        self.send("X")
        self._last_line = "X"

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
