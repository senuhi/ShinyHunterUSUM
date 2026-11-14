"""Optional macOS-only, local Vision OCR. No external service or token use."""
import base64
import hashlib
import io
import json
import os
import selectors
import subprocess
import sys
import time
from pathlib import Path
from gift_recognition import SafetyStop
from platform_support import lock_slot


class MacOCR:
    def __init__(self, cache):
        if sys.platform != 'darwin':raise SafetyStop('この自動診断のOCRはmacOS専用です。')
        source=Path(__file__).with_suffix('.swift')
        cache=Path(cache).resolve();cache.mkdir(parents=True,exist_ok=True)
        tag=hashlib.sha256(source.read_bytes()).hexdigest()[:12]
        executable=cache/f'vision-ocr-{tag}'
        deadline=time.monotonic()+90; lock=lock_slot(cache,77)
        while lock is None:
            if time.monotonic()>deadline:raise SafetyStop('OCRの準備待ちがタイムアウトしました。')
            time.sleep(.1);lock=lock_slot(cache,77)
        try:
            if not executable.exists():
                temporary=executable.with_suffix(f'.{os.getpid()}.tmp')
                result=subprocess.run(['xcrun','swiftc','-O','-module-cache-path',str(cache/'modules'),
                    str(source),'-o',str(temporary)],capture_output=True,text=True,timeout=90)
                if result.returncode:raise SafetyStop('OCRの準備失敗。Xcode Command Line Toolsを確認してください。'+result.stderr[-500:])
                temporary.replace(executable)
        finally:lock.close()
        self.process=subprocess.Popen([str(executable)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        self.selector=selectors.DefaultSelector();self.selector.register(self.process.stdout,selectors.EVENT_READ)

    def read(self, image, timeout=2, correction=True):
        data=io.BytesIO();image.resize((image.width*3,image.height*3)).save(data,'PNG')
        request=json.dumps({'image':base64.b64encode(data.getvalue()).decode(),'correction':bool(correction)}).encode()+b'\n'
        if self.process.poll() is not None:raise SafetyStop('OCRプロセスが停止しました。')
        self.process.stdin.write(request);self.process.stdin.flush()
        if not self.selector.select(timeout=timeout):raise SafetyStop('OCRが時間内に応答しません。入力しません。')
        line=self.process.stdout.readline()
        if not line:raise SafetyStop('OCR接続が閉じました。')
        result=json.loads(line)
        if result.get('error'):raise SafetyStop('OCR処理失敗: '+result['error'])
        return result['rows']

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=1)
        self.selector.close()
        self.process.stdin.close();self.process.stdout.close()
