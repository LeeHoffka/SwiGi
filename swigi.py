#!/usr/bin/env python3
"""SwiGi — synchronizace Easy-Switch přes Bluetooth.

Při stisku Easy-Switch na Logitech klávesnici zachytí CHANGE_HOST notifikaci
a pošle stejný příkaz myši. Oba se přepnou na stejný host.

Self-contained: veškerý HID++ kód je uvnitř. Jediná závislost = hidapi knihovna.

macOS:  brew install hidapi  (nebo libhidapi.dylib ve složce s tímto souborem)
Windows: hidapi.dll ve složce s tímto souborem (stáhni z github.com/libusb/hidapi/releases)
Linux:  sudo apt install libhidapi-hidraw0

Spuštění:
  python swigi.py        # normální režim
  python swigi.py -v     # verbose
"""
from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import dataclasses
import logging
import os
import platform
import signal
import struct
import sys
import time

log = logging.getLogger("swigi")

# ═══════════════════════════════════════════════════════════════════════════════
#  HID++ Constants
# ═══════════════════════════════════════════════════════════════════════════════

LOGITECH_VID = 0x046D

BOLT_PID = 0xC548
UNIFYING_PIDS = (0xC52B, 0xC532)
ALL_RECEIVER_PIDS = (BOLT_PID,) + UNIFYING_PIDS

REPORT_SHORT = 0x10
REPORT_LONG = 0x11
MSG_SHORT_LEN = 7
MSG_LONG_LEN = 20
MAX_READ_SIZE = 32

FEATURE_ROOT = 0x0000
FEATURE_DEVICE_TYPE_AND_NAME = 0x0005
FEATURE_CHANGE_HOST = 0x1814

DEVICE_TYPE_KEYBOARD = 0
DEVICE_TYPE_MOUSE = 3
DEVICE_TYPE_TRACKPAD = 4
DEVICE_TYPE_TRACKBALL = 5

DEVNUMBER_DIRECT = 0xFF
SW_ID = 0x08
CHANGE_HOST_FN_SET = 0x10

_MSG_LENGTHS = {REPORT_SHORT: MSG_SHORT_LEN, REPORT_LONG: MSG_LONG_LEN}

# Usage pairs: HID++ vendor + Generic Desktop (macOS BT only shows Generic Desktop)
DIRECT_USAGE_PAIRS = [
    (0xFF00, 0x0002), (0xFF43, 0x0202), (0xFF0C, 0x0001),
    (0x0001, 0x0006),  # Keyboard
    (0x0001, 0x0002),  # Mouse
]

# ═══════════════════════════════════════════════════════════════════════════════
#  hidapi loading
# ═══════════════════════════════════════════════════════════════════════════════

_SYSTEM = platform.system()


class TransportError(Exception):
    pass


def _load_hidapi() -> ctypes.CDLL:
    """Load hidapi library. Search order: app directory, PyInstaller bundle, system."""
    # App directory (portable: hidapi next to this script)
    app_dir = os.path.dirname(os.path.abspath(__file__))
    meipass = getattr(sys, "_MEIPASS", None)  # PyInstaller

    search_dirs = [app_dir]
    if meipass:
        search_dirs.append(meipass)

    # Platform-specific names
    if _SYSTEM == "Darwin":
        local_names = ["libhidapi.dylib"]
        system_names = [
            "/opt/homebrew/lib/libhidapi.dylib",
            "/usr/local/lib/libhidapi.dylib",
            "libhidapi.dylib",
        ]
    elif _SYSTEM == "Windows":
        local_names = ["hidapi.dll", "libhidapi-0.dll"]
        system_names = ["hidapi.dll", "libhidapi-0.dll"]
        # Windows DLL search paths
        for d in search_dirs:
            if os.path.isdir(d):
                try:
                    os.add_dll_directory(d)
                except Exception:
                    pass
        scripts_dir = os.path.join(sys.prefix, "Scripts")
        if os.path.isdir(scripts_dir):
            try:
                os.add_dll_directory(scripts_dir)
            except Exception:
                pass
    else:  # Linux
        local_names = ["libhidapi-hidraw.so.0", "libhidapi-hidraw.so", "libhidapi.so.0", "libhidapi.so"]
        system_names = local_names + [
            "libhidapi-libusb.so.0", "libhidapi-libusb.so",
        ]

    # Try local (portable) first
    for d in search_dirs:
        for name in local_names:
            path = os.path.join(d, name)
            if os.path.isfile(path):
                try:
                    lib = ctypes.CDLL(path)
                    log.debug("hidapi: loaded %s (local)", path)
                    return lib
                except OSError:
                    continue

    # Try system
    for name in system_names:
        try:
            lib = ctypes.CDLL(name)
            log.debug("hidapi: loaded %s (system)", name)
            return lib
        except OSError:
            continue

    hints = {
        "Darwin": "brew install hidapi  NEBO  zkopíruj libhidapi.dylib do složky s tímto souborem",
        "Windows": "Stáhni hidapi.dll z github.com/libusb/hidapi/releases a dej do složky s tímto souborem",
        "Linux": "sudo apt install libhidapi-hidraw0",
    }
    raise ImportError(f"hidapi nenalezena — {hints.get(_SYSTEM, 'nainstaluj hidapi')}")


_lib = _load_hidapi()

# Init
_lib.hid_init.restype = ctypes.c_int
_lib.hid_init.argtypes = []
_lib.hid_init()

# macOS: non-exclusive (coexist with Logi Options+)
if _SYSTEM == "Darwin":
    _fn = getattr(_lib, "hid_darwin_set_open_exclusive", None)
    if _fn:
        _fn.argtypes = [ctypes.c_int]
        _fn.restype = None
        _fn(0)

# ═══════════════════════════════════════════════════════════════════════════════
#  hidapi bindings
# ═══════════════════════════════════════════════════════════════════════════════


class _DeviceInfo(ctypes.Structure):
    pass


_DeviceInfo._fields_ = [
    ("path", ctypes.c_char_p),
    ("vendor_id", ctypes.c_ushort),
    ("product_id", ctypes.c_ushort),
    ("serial_number", ctypes.c_wchar_p),
    ("release_number", ctypes.c_ushort),
    ("manufacturer_string", ctypes.c_wchar_p),
    ("product_string", ctypes.c_wchar_p),
    ("usage_page", ctypes.c_ushort),
    ("usage", ctypes.c_ushort),
    ("interface_number", ctypes.c_int),
    ("next", ctypes.POINTER(_DeviceInfo)),
]

_lib.hid_enumerate.restype = ctypes.POINTER(_DeviceInfo)
_lib.hid_enumerate.argtypes = [ctypes.c_ushort, ctypes.c_ushort]
_lib.hid_free_enumeration.restype = None
_lib.hid_free_enumeration.argtypes = [ctypes.POINTER(_DeviceInfo)]
_lib.hid_open_path.restype = ctypes.c_void_p
_lib.hid_open_path.argtypes = [ctypes.c_char_p]
_lib.hid_close.restype = None
_lib.hid_close.argtypes = [ctypes.c_void_p]
_lib.hid_read_timeout.restype = ctypes.c_int
_lib.hid_read_timeout.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ubyte), ctypes.c_size_t, ctypes.c_int]
_lib.hid_write.restype = ctypes.c_int
_lib.hid_write.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ubyte), ctypes.c_size_t]
_lib.hid_error.restype = ctypes.c_wchar_p
_lib.hid_error.argtypes = [ctypes.c_void_p]


def _hid_err(dev=None):
    msg = _lib.hid_error(dev)
    return msg if msg else "unknown hidapi error"


# ═══════════════════════════════════════════════════════════════════════════════
#  Transport
# ═══════════════════════════════════════════════════════════════════════════════


class HIDTransport:
    def __init__(self, path: bytes, pid: int):
        self.path = path
        self.pid = pid
        self._dev = _lib.hid_open_path(path)
        if not self._dev:
            raise OSError(f"hid_open_path failed: {_hid_err()}")

    def read(self, timeout: int = 500) -> bytes | None:
        if self._dev is None:
            raise TransportError("read on closed transport")
        buf = (ctypes.c_ubyte * MAX_READ_SIZE)()
        n = _lib.hid_read_timeout(self._dev, buf, MAX_READ_SIZE, timeout)
        if n < 0:
            err = _hid_err(self._dev) or ""
            if "success" in err.lower() or err == "":
                return None  # macOS BT quirk
            raise TransportError(f"hid_read failed: {err}")
        return bytes(buf[:n]) if n > 0 else None

    def write(self, msg: bytes) -> None:
        if self._dev is None:
            raise TransportError("write on closed transport")
        buf = (ctypes.c_ubyte * len(msg))(*msg)
        n = _lib.hid_write(self._dev, buf, len(msg))
        if n < 0:
            raise TransportError(f"hid_write failed: {_hid_err(self._dev)}")

    def close(self):
        if self._dev is not None:
            _lib.hid_close(self._dev)
            self._dev = None


# ═══════════════════════════════════════════════════════════════════════════════
#  HID++ Protocol
# ═══════════════════════════════════════════════════════════════════════════════


def _build_msg(devnumber, request_id, params):
    data = struct.pack("!H", request_id) + params
    return struct.pack("!BB18s", REPORT_LONG, devnumber, data)


def _pack_params(params):
    parts = []
    for p in params:
        if isinstance(p, int):
            parts.append(struct.pack("B", p))
        else:
            parts.append(bytes(p))
    return b"".join(parts)


def hidpp_request(transport, devnumber, request_id, *params, timeout=500):
    """Send HID++ request and return reply payload, or None."""
    request_id = (request_id & 0xFFF0) | SW_ID
    params_bytes = _pack_params(params) if params else b""
    request_data = struct.pack("!H", request_id) + params_bytes
    msg = _build_msg(devnumber, request_id, params_bytes)

    transport.write(msg)

    deadline = time.time() + timeout / 1000
    while time.time() < deadline:
        raw = transport.read(timeout)
        if not raw or len(raw) < 4:
            continue
        if raw[0] not in _MSG_LENGTHS or len(raw) != _MSG_LENGTHS[raw[0]]:
            continue

        rdev = raw[1]
        if rdev != devnumber and rdev != (devnumber ^ 0xFF):
            continue

        rdata = raw[2:]

        # HID++ 1.0 error
        if raw[0] == REPORT_SHORT and rdata[0:1] == b"\x8f" and rdata[1:3] == request_data[:2]:
            return None
        # HID++ 2.0 error
        if rdata[0:1] == b"\xff" and rdata[1:3] == request_data[:2]:
            return None
        # Success
        if rdata[:2] == request_data[:2]:
            return rdata[2:]

    return None


def resolve_feature(transport, devnumber, feature_code):
    """Look up feature index. Returns index or None."""
    request_id = (FEATURE_ROOT << 8) | 0x00
    reply = hidpp_request(transport, devnumber, request_id,
                          feature_code >> 8, feature_code & 0xFF, 0x00, timeout=500)
    if reply and reply[0] != 0x00:
        return reply[0]
    return None


def get_device_type(transport, devnumber, feat_idx):
    reply = hidpp_request(transport, devnumber, (feat_idx << 8) | 0x20, timeout=500)
    return reply[0] if reply else None


def get_device_name(transport, devnumber, feat_idx):
    reply = hidpp_request(transport, devnumber, (feat_idx << 8) | 0x00, timeout=500)
    if not reply:
        return None
    name_len = reply[0]
    if name_len == 0:
        return None
    chars = []
    while len(chars) < name_len:
        reply = hidpp_request(transport, devnumber, (feat_idx << 8) | 0x10, len(chars), timeout=500)
        if not reply:
            break
        chars.extend(reply[:name_len - len(chars)])
    return bytes(chars).decode("utf-8", errors="replace") if chars else None


def send_change_host(transport, devnumber, feat_idx, target_host):
    """Fire-and-forget: switch device to target_host (0-based)."""
    request_id = (feat_idx << 8) | (CHANGE_HOST_FN_SET & 0xF0) | SW_ID
    params = struct.pack("B", target_host)
    msg = _build_msg(devnumber, request_id, params)
    transport.write(msg)


def get_current_host(transport, devnumber, feat_idx):
    """Query CHANGE_HOST getHostInfo (fn 0). Returns current host (0-based) or None."""
    reply = hidpp_request(transport, devnumber, (feat_idx << 8) | 0x00, timeout=500)
    if reply and len(reply) >= 2:
        # reply[0] = numHosts, reply[1] = currentHost
        return reply[1]
    return None


# ═══════════════════════════════════════════════════════════════════════════════
#  Device Discovery
# ═══════════════════════════════════════════════════════════════════════════════


@dataclasses.dataclass
class DeviceInfo:
    transport: HIDTransport
    name: str
    pid: int
    change_host_idx: int

    def close(self):
        try:
            self.transport.close()
        except Exception:
            pass


def find_device(device_type_wanted: int) -> DeviceInfo | None:
    """Find Logitech BT device. 0=keyboard, 3=mouse, 4=trackpad, 5=trackball."""
    head = _lib.hid_enumerate(LOGITECH_VID, 0)
    candidates = []
    node = head
    while node:
        info = node.contents
        node = info.next
        pid = info.product_id
        up = info.usage_page
        usage = info.usage
        if pid in ALL_RECEIVER_PIDS:
            continue
        if (up, usage) not in DIRECT_USAGE_PAIRS:
            continue
        # Score: vendor HID++ interfaces first (Windows blocks Generic Desktop)
        if up in (0xFF00, 0xFF43, 0xFF0C):
            score = 100
        else:
            score = 0
        candidates.append((score, info.path, pid, up, usage))
    _lib.hid_free_enumeration(head)
    # Sort: vendor HID++ first, then Generic Desktop
    candidates.sort(key=lambda x: -x[0])

    found_pids = set()
    for score, path, pid, up, usage in candidates:
        if pid in found_pids:
            continue  # already found this device
        try:
            t = HIDTransport(path, pid)
        except OSError:
            log.debug("Open failed pid=0x%04X up=0x%04X u=0x%04X", pid, up, usage)
            continue
        try:
            feat = resolve_feature(t, DEVNUMBER_DIRECT, FEATURE_DEVICE_TYPE_AND_NAME)
            if feat is None:
                t.close()
                continue
            dt = get_device_type(t, DEVNUMBER_DIRECT, feat)
            name = get_device_name(t, DEVNUMBER_DIRECT, feat) or f"Logitech-0x{pid:04X}"
            # Mouse types: 3 (mouse), 4 (trackpad), 5 (trackball)
            is_mouse = dt in (DEVICE_TYPE_MOUSE, DEVICE_TYPE_TRACKPAD, DEVICE_TYPE_TRACKBALL)
            if device_type_wanted == DEVICE_TYPE_KEYBOARD and dt != DEVICE_TYPE_KEYBOARD:
                t.close()
                continue
            if device_type_wanted == DEVICE_TYPE_MOUSE and not is_mouse:
                t.close()
                continue
            ch = resolve_feature(t, DEVNUMBER_DIRECT, FEATURE_CHANGE_HOST)
            if ch is None:
                t.close()
                continue
            found_pids.add(pid)
            return DeviceInfo(t, name, pid, ch)
        except (TransportError, OSError):
            t.close()
            continue
    return None


# ═══════════════════════════════════════════════════════════════════════════════
#  Ping message
# ═══════════════════════════════════════════════════════════════════════════════

_PING_REQUEST_ID = (FEATURE_ROOT << 8) | 0x00 | SW_ID
_PING_MSG = struct.pack("!BB18s", REPORT_LONG, DEVNUMBER_DIRECT,
                        struct.pack("!H", _PING_REQUEST_ID) + b"\x00\x00\x00")


# ═══════════════════════════════════════════════════════════════════════════════
#  Main daemon loop
# ═══════════════════════════════════════════════════════════════════════════════


def main():
    parser = argparse.ArgumentParser(
        description="SwiGi — synchronizace Easy-Switch přes Bluetooth")
    parser.add_argument("-v", "--verbose", action="store_true", help="Podrobné logování")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
    )

    log.info("SwiGi — hledám zařízení...")

    kb = find_device(DEVICE_TYPE_KEYBOARD)
    if kb is None:
        log.error("Klávesnice nenalezena! Zkontroluj BT připojení.")
        return 1
    log.info("Klávesnice: %s (CHANGE_HOST idx=%d)", kb.name, kb.change_host_idx)

    mouse = find_device(DEVICE_TYPE_MOUSE)
    if mouse is None:
        log.error("Myš nenalezena! Zkontroluj BT připojení.")
        kb.close()
        return 1
    log.info("Myš:        %s (CHANGE_HOST idx=%d)", mouse.name, mouse.change_host_idx)

    log.info("")
    log.info("Připraveno. Stiskni Easy-Switch na %s.", kb.name)
    log.info("Ctrl+C pro ukončení.")

    running = True

    def on_sigint(sig, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, on_sigint)

    total_switches = 0

    while running:
        # ── Send ping ──
        try:
            kb.transport.write(_PING_MSG)
        except (TransportError, OSError):
            log.info("Klávesnice se odpojila, čekám na návrat...")
            kb.close()

            # Reconnect loop
            kb_new = None
            for attempt in range(120):
                if not running:
                    break
                time.sleep(0.5)
                kb_new = find_device(DEVICE_TYPE_KEYBOARD)
                if kb_new is not None:
                    break
                if attempt % 20 == 19:
                    log.debug("Reconnect: pokus %d/120...", attempt + 1)

            if kb_new is None:
                if running:
                    log.warning("Klávesnice se nevrátila, zkouším dál...")
                continue
            kb = kb_new
            log.info("Klávesnice reconnect: %s", kb.name)

            # Just close stale mouse transport — don't probe/reconnect now
            # (aggressive HID open/close can disrupt BT stack while mouse is reconnecting)
            mouse.close()
            log.debug("Starý mouse transport zavřen, reconnect při dalším eventu")

            continue

        # ── Read responses (200ms window) ──
        deadline = time.time() + 0.2
        while time.time() < deadline and running:
            try:
                raw = kb.transport.read(timeout=50)
            except (TransportError, OSError):
                break

            if raw is None:
                continue
            if len(raw) < 4:
                continue
            rid = raw[0]
            if rid not in _MSG_LENGTHS or len(raw) != _MSG_LENGTHS[rid]:
                continue

            feat = raw[2]
            func = raw[3]
            sw_id = func & 0x0F

            # CHANGE_HOST notification: feat matches, sw_id == 0 (notification)
            if feat == kb.change_host_idx and sw_id == 0 and len(raw) > 5:
                target_host = raw[5]
                log.info("")
                log.info("★ Easy-Switch: %s → host %d", kb.name, target_host)

                # Send CHANGE_HOST to mouse — reconnect if transport is stale
                if mouse.transport._dev is None:
                    log.debug("Mouse transport stale, reconnecting...")
                    new_mouse = find_device(DEVICE_TYPE_MOUSE)
                    if new_mouse:
                        mouse = new_mouse
                    else:
                        log.info("Myš zatím nedostupná — přepne se při dalším Easy-Switch")
                        break

                try:
                    send_change_host(mouse.transport, DEVNUMBER_DIRECT,
                                     mouse.change_host_idx, target_host)
                    log.info("★ CHANGE_HOST → %s → host %d", mouse.name, target_host)
                    total_switches += 1
                except (TransportError, OSError):
                    log.warning("CHANGE_HOST na myš selhal, zkouším reconnect myši...")
                    mouse.close()
                    time.sleep(1.0)  # let BT stack settle
                    new_mouse = find_device(DEVICE_TYPE_MOUSE)
                    if new_mouse:
                        mouse = new_mouse
                        try:
                            send_change_host(mouse.transport, DEVNUMBER_DIRECT,
                                             mouse.change_host_idx, target_host)
                            log.info("★ CHANGE_HOST → %s → host %d (po reconnectu)",
                                     mouse.name, target_host)
                            total_switches += 1
                        except (TransportError, OSError) as e:
                            log.warning("CHANGE_HOST retry selhal: %s — myš se přepne příště", e)
                    else:
                        log.info("Myš zatím nedostupná — přepne se při dalším Easy-Switch")

                break  # keyboard will disconnect

            # Log other notifications
            if sw_id == 0:
                log.debug("Notifikace: feat=0x%02X [%s]", feat, raw[:10].hex())

        time.sleep(0.05)

    log.info("Ukončuji. Celkem %d přepnutí.", total_switches)
    kb.close()
    mouse.close()
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
