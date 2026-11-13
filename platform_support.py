"""Native platform paths, process locks and Tk window icons."""
import os
import sys
import tempfile
from pathlib import Path


def data_directory():
    override = os.environ.get('USUM_DATA_DIR')
    if override:
        path = Path(override).expanduser().resolve()
    elif sys.platform == 'darwin':
        path = Path.home() / 'Library/Application Support/ShinyHunterUSUM'
    else:
        # Keep upstream Windows settings migration working.
        path = Path(tempfile.gettempdir())
    path.mkdir(parents=True, exist_ok=True)
    return path


def capture_directory():
    override = os.environ.get('USUM_CAPTURE_DIR')
    path = (Path(override).expanduser().resolve() if override else
            Path.home() / 'Pictures/ShinyHunterUSUM')
    path.mkdir(parents=True, exist_ok=True)
    return path


def lock_slot(folder, num):
    f = open(Path(folder) / f'USUMShinyHunter-{num}.lock', 'a+b')
    try:
        if sys.platform == 'win32':
            import msvcrt
            f.seek(0)
            if not f.read(1):
                f.write(b'\0')
                f.flush()
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return f
    except OSError:
        f.close()
        return None


def set_window_icon(window, path):
    from PIL import Image, ImageTk
    # Cocoa does not implement Tk's Windows iconbitmap option.
    try:
        window._window_icon = ImageTk.PhotoImage(Image.open(path), master=window)
        window.iconphoto(True, window._window_icon)
    except (OSError, __import__('tkinter').TclError):
        pass  # Cosmetic; must not prevent startup on a different Tk build.
