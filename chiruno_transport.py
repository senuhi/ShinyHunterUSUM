"""Independent, fail-closed ChirunoMod v0.2.2 JPEG/TCP adapter.

Wire references and limitations: docs/OLD3DS_PLAN.md. No controller commands.
Old 3DS fractions are published only after a complete ordered pass per screen.
"""
import io
import socket
import struct
import time
from dataclasses import dataclass
from PIL import Image

MAX_PAYLOAD = 1024 * 1024


class ProtocolError(OSError):
    pass


def packet(kind, subtype=0, payload=b'', subtype_b=0):
    if len(payload) > MAX_PAYLOAD:
        raise ProtocolError('ChirunoMod payload too large')
    return struct.pack('<BBBBI', kind, subtype, subtype_b, 0, len(payload)) + payload


def setup_packets(quality=80):
    if type(quality) is not int or not 1 <= quality <= 100:
        raise ValueError('JPEG quality must be 1..100')
    # JPEG; quality; progressive (no interlace); both screens; initialize.
    return (packet(4, 4, b'\0'), packet(4, 1, bytes([quality])),
            packet(4, 5, b'\0'), packet(4, 3, b'\x03'), packet(2))


class PacketParser:
    """Incremental parser: TCP recv boundaries and timeouts are not packet boundaries."""
    def __init__(self):
        self.buffer = bytearray()

    def feed(self, data):
        self.buffer.extend(data)
        packets = []
        while len(self.buffer) >= 8:
            kind, a, b, c, length = struct.unpack_from('<BBBBI', self.buffer)
            if length > MAX_PAYLOAD:
                raise ProtocolError('Invalid ChirunoMod packet length')
            if len(self.buffer) < 8 + length:
                break
            payload = bytes(self.buffer[8:8+length])
            del self.buffer[:8+length]
            packets.append((kind, a, b, payload))
        if len(self.buffer) > MAX_PAYLOAD + 8:
            raise ProtocolError('ChirunoMod receive buffer exceeded limit')
        return packets


@dataclass(frozen=True)
class VideoFrame:
    screen: int
    image: Image.Image
    started: float
    completed: float


class ChirunoDecoder:
    def __init__(self, max_span=2.0, clock=time.monotonic):
        self.clock, self.max_span = clock, max_span
        self.pending = {}
        self.synchronized = set()

    def feed(self, message, packet_started=None):
        kind, flags, sub_b, data = message
        if kind == 3:
            self.pending.clear()
            raise ProtocolError('ChirunoMod requested disconnect')
        if kind == 255:
            return None  # Debug packets never count as a live image.
        if kind != 1:
            raise ProtocolError(f'Unexpected ChirunoMod packet type {kind}')
        if flags & 0xE8 or sub_b & ~0x0F:
            # 0x08=TGA, 0x20=interlace, 0x40=parity. No partial-field publication.
            raise ProtocolError('Need progressive JPEG; unsupported ChirunoMod flags')
        screen = 0 if flags & 0x10 else 1
        width = 320 if screen == 0 else 400
        fractional, index = bool(sub_b & 8), sub_b & 7
        if not fractional and index:
            raise ProtocolError('Fraction index without fractional flag')
        expected_height = width // 8 if fractional else width
        try:
            with Image.open(io.BytesIO(data)) as source:
                if source.format != 'JPEG' or source.size not in ((240, expected_height), (256, expected_height)):
                    raise ProtocolError(f'Unexpected ChirunoMod JPEG dimensions {source.size}; '
                                        f'flags={flags:#x}, fraction={sub_b:#x}, expected=240x{expected_height}')
                rgb = source.convert('RGB').crop((0, 0, 240, expected_height))
                r, g, b = rgb.split()
                image = Image.merge('RGB', (b, g, r)).rotate(90, expand=True)
                image.load()
        except (OSError, ValueError) as error:
            raise ProtocolError(f'Invalid ChirunoMod image: {error}') from error
        now = self.clock()
        origin = now if packet_started is None else packet_started
        if now - origin > self.max_span:
            raise ProtocolError('ChirunoMod image packet exceeded freshness limit')
        if not fractional:
            if screen in self.pending:
                raise ProtocolError('Encoding changed during incomplete screen')
            return VideoFrame(screen, image, origin, now)
        if index == 0:
            if screen in self.pending:
                raise ProtocolError('Incomplete ChirunoMod pass overwritten')
            self.pending[screen] = [0, origin, Image.new('RGB', (width, 240))]
            self.synchronized.add(screen)
        state = self.pending.get(screen)
        if state is None and screen not in self.synchronized:
            return None  # Attach mid-pass: discard prefix, wait for a real fraction 0.
        if state is None or state[0] != index:
            raise ProtocolError('Missing/reordered ChirunoMod screen fraction')
        if now - state[1] > self.max_span:
            raise ProtocolError('ChirunoMod screen assembly exceeded freshness limit')
        state[2].paste(image, (index * (width // 8), 0))
        state[0] += 1
        if index != 7:
            return None
        del self.pending[screen]
        return VideoFrame(screen, state[2], state[1], now)


class ChirunoSource:
    def __init__(self, local, console, quality=80, max_span=2.0):
        self.tcp = socket.create_connection(console, timeout=5, source_address=(local[0], 0))
        self.udp = None
        self.parser = PacketParser()
        self.decoder = ChirunoDecoder(max_span)
        self.ready = []
        self.last_message = None
        self.partial_since = None
        self.read_limit = max_span
        try:
            self.tcp.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.tcp.settimeout(.3)
            for data in setup_packets(quality):
                self.tcp.sendall(data)
        except Exception:
            self.tcp.close()
            raise

    def read(self):
        deadline = time.monotonic() + .3
        while True:
            if self.ready:
                return self.ready.pop(0)
            now = time.monotonic()
            if now > deadline:
                raise socket.timeout('No complete ChirunoMod screen yet')
            if self.partial_since is not None and now - self.partial_since > self.read_limit:
                raise ProtocolError('ChirunoMod partial TCP packet timed out')
            data = self.tcp.recv(65536)
            if not data:
                raise ProtocolError('ChirunoMod TCP connection closed')
            if self.partial_since is None:
                self.partial_since = time.monotonic()
            for message in self.parser.feed(data):
                self.last_message = message
                frame = self.decoder.feed(message, self.partial_since)
                if frame is not None:
                    self.ready.append(frame)
            # Incomplete packet bytes keep their original deadline across timeouts.
            self.partial_since = (self.partial_since if self.parser.buffer else None)

    def close(self):
        # Closing is a video-only operation. Never reconnect or send input here.
        try:
            self.tcp.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.tcp.close()
