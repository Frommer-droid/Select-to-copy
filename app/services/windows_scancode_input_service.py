from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes

KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
INPUT_KEYBOARD = 1
MAPVK_VK_TO_VSC = 0

VK_LCONTROL = 0xA2
VK_C = 0x43

# Fallback значения для Windows, если MapVirtualKeyW вернет 0.
SCAN_LCONTROL = 0x1D
SCAN_C = 0x2E

KEY_SEQUENCE_DELAY_SEC = 0.01


if hasattr(wintypes, "ULONG_PTR"):
    ULONG_PTR = wintypes.ULONG_PTR
else:
    ULONG_PTR = wintypes.WPARAM


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _anonymous_ = ("_union",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("_union", _INPUT_UNION),
    ]

SendInput = ctypes.windll.user32.SendInput
SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
SendInput.restype = wintypes.UINT

MapVirtualKeyW = ctypes.windll.user32.MapVirtualKeyW
MapVirtualKeyW.argtypes = (wintypes.UINT, wintypes.UINT)
MapVirtualKeyW.restype = wintypes.UINT


def _map_virtual_key_to_scan_code(virtual_key: int) -> int:
    return int(MapVirtualKeyW(virtual_key, MAPVK_VK_TO_VSC))


def _send_scancode(scan_code: int, key_up: bool = False) -> bool:
    flags = KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if key_up else 0)
    keyboard_input = KEYBDINPUT(0, scan_code, flags, 0, 0)
    event = INPUT(type=INPUT_KEYBOARD, ki=keyboard_input)

    sent = SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT))
    return sent == 1


def send_left_ctrl_c() -> bool:
    if sys.platform != "win32":
        return False

    ctrl_scan = _map_virtual_key_to_scan_code(VK_LCONTROL) or SCAN_LCONTROL
    c_scan = _map_virtual_key_to_scan_code(VK_C) or SCAN_C

    ok = True
    ok &= _send_scancode(ctrl_scan, key_up=False)
    time.sleep(KEY_SEQUENCE_DELAY_SEC)
    ok &= _send_scancode(c_scan, key_up=False)
    time.sleep(KEY_SEQUENCE_DELAY_SEC)
    ok &= _send_scancode(c_scan, key_up=True)
    time.sleep(KEY_SEQUENCE_DELAY_SEC)
    ok &= _send_scancode(ctrl_scan, key_up=True)
    return ok
