"""Video-source boundary shared by GUI, recorder, capture and diagnostics."""
import socket
import time
from ntr_transport import endpoint, open_stream, FrameAssembler
from chiruno_transport import ChirunoSource, VideoFrame

BACKENDS = ('ChirunoMod', 'NTR-HR')


def console_endpoint(value, backend):
    if backend not in BACKENDS:
        raise ValueError('Unknown video backend')
    return endpoint(value, 6464 if backend == 'ChirunoMod' else 8000)


class NTRSource:
    def __init__(self, local, console):
        self.tcp, self.udp = open_stream(local, console[0], console[1])
        self.host = console[0]
        self.assembler = FrameAssembler()
        self.started = {}

    def read(self):
        deadline = time.monotonic() + .3
        while True:
            if time.monotonic() > deadline:
                raise socket.timeout('No complete NTR screen yet')
            data, address = self.udp.recvfrom(65535)
            if address[0] != self.host:
                continue
            if len(data) >= 4 and data[1] in (0, 1, 16, 17) and data[3] == 0:
                self.started[data[1] & 1] = time.monotonic()
            result = self.assembler.feed(data)
            if result is not None:
                screen, image = result
                now = time.monotonic()
                return VideoFrame(screen, image, self.started.pop(screen, now), now)

    def close(self):
        self.udp.close()
        self.tcp.close()


def open_video(backend, local, console, quality=80, max_span=2.0):
    if backend == 'ChirunoMod':
        return ChirunoSource(local, console, quality, max_span)
    if backend == 'NTR-HR':
        return NTRSource(local, console)
    raise ValueError('Unknown video backend')
