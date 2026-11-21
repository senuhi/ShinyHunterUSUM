"""Size-bounded JSONL diagnostics; caller owns the cross-thread file lock."""
import json
from pathlib import Path

EVENT_LOG_BYTES = 8 * 1024 * 1024
EVENT_LOG_BACKUPS = 2


def append_json_line(path, record, *, limit_bytes=EVENT_LOG_BYTES, backups=EVENT_LOG_BACKUPS):
    if type(limit_bytes) is not int or limit_bytes<1 or type(backups) is not int or not 0<=backups<=10:
        raise ValueError('Invalid diagnostic log limits')
    payload=(json.dumps(record,ensure_ascii=False)+'\n').encode('utf-8')
    if len(payload)>limit_bytes:
        raise OSError('Diagnostic event exceeds log size limit')
    path=Path(path)
    try:current=path.stat().st_size
    except FileNotFoundError:current=0
    if current+len(payload)>limit_bytes:
        for number in range(backups,0,-1):
            previous=path if number==1 else path.with_name(path.name+f'.{number-1}')
            if previous.exists():previous.replace(path.with_name(path.name+f'.{number}'))
        if not backups:path.unlink(missing_ok=True)
    # I/O errors intentionally propagate: never silently hide failed safety logs.
    with path.open('ab') as stream:stream.write(payload)
