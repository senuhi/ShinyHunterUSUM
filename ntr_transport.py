"""Portable legacy NTR JPEG protocol. No Tk or controller side effects."""
import io
import ipaddress
import socket
import struct
import threading
import time
import hashlib
from dataclasses import dataclass
from PIL import Image

SCREEN_SIZES = {0: (320, 240), 1: (400, 240)}


def endpoint(value, default_port):
    parts = value.strip().split(':')
    if len(parts) not in (1, 2):
        raise ValueError('Use an IPv4 address, optionally followed by :port')
    host = str(ipaddress.IPv4Address(parts[0]))
    port = int(parts[1]) if len(parts) == 2 else default_port
    if not 1 <= port <= 65535:
        raise ValueError('Port must be between 1 and 65535')
    return host, port


def control_packets(port):
    if not 1 <= port <= 65535:
        raise ValueError('Invalid stream port')
    heartbeat = struct.pack('<21I', 0x12345678, 0, 0, 0, 0x105, *([0] * 16))
    # Preserve upstream remote-play command (JPEG, quality 80, both screens).
    setup = bytearray.fromhex(
        '78563412000100000000000085030000050100005000000000001800'
        'dce5af53411f00000000000000000000000000000000000000000000'
        '00000000000000000000000000000000000000000000000000000000')
    struct.pack_into('<H', setup, 32, port)
    return heartbeat, bytes(setup)


class FrameAssembler:
    def __init__(self):
        self.pending = {}

    def feed(self, packet):
        if len(packet) < 5 or packet[1] not in (0, 1, 16, 17):
            return None
        frame, flags, _, index = packet[:4]
        screen = flags & 1
        final = bool(flags & 16)
        if index == 0:
            self.pending[screen] = (frame, 0, bytearray(packet[4:]))
        else:
            prev = self.pending.get(screen)
            if prev is None or prev[0] != frame or prev[1] + 1 != index:
                self.pending.pop(screen, None)
                return None
            data = prev[2]
            data.extend(packet[4:])
            if len(data) > 1024 * 1024:
                self.pending.pop(screen, None)
                return None
            self.pending[screen] = (frame, index, data)
        if not final:
            return None
        _, _, data = self.pending.pop(screen)
        try:
            with Image.open(io.BytesIO(data)) as source:
                if source.format != 'JPEG' or source.size != (240, SCREEN_SIZES[screen][0]):
                    return None
                img = source.convert('RGB').rotate(90, expand=True)
                img.load()
        except (OSError, ValueError):
            return None
        return screen, img


@dataclass(frozen=True)
class Frame:
    image: Image.Image
    serial: int
    received: float
    changed: float


class FrameStore:
    """Completed frames only. Reject silent transport and repeated frozen images."""
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.lock = threading.Lock()
        self.frames = {}
        self.hashes = {}
        self.error = None

    def put(self, screen, img):
        now = self.clock()
        digest = hashlib.sha256(img.tobytes()).digest()
        with self.lock:
            old = self.frames.get(screen)
            changed = now if digest != self.hashes.get(screen) else old.changed
            self.frames[screen] = Frame(img.copy(), 1 if old is None else old.serial + 1,
                                        now, changed)
            self.hashes[screen] = digest

    def snapshot(self, screen, max_age=2.0, freeze_timeout=15.0):
        with self.lock:
            if self.error:
                raise OSError(self.error)
            f = self.frames.get(screen)
            now = self.clock()
            if f is None or now - f.received > max_age:
                raise OSError(f'Stale/missing screen {screen}')
            if now - f.changed > freeze_timeout:
                raise OSError(f'Frozen screen {screen}')
            return f


def open_stream(local, console, tcp_port=8000):
    """Bind before asking NTR to stream. Connect TCP from the selected local IP."""
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    tcp = None
    try:
        udp.bind(local)
        udp.settimeout(0.3)
        tcp = socket.create_connection((console, tcp_port), timeout=5,
                                       source_address=(local[0], 0))
        for _ in range(2):
            for packet in control_packets(local[1]):
                tcp.sendall(packet)
            time.sleep(0.1)
        return tcp, udp
    except Exception:
        udp.close()
        if tcp is not None:
            tcp.close()
        raise
