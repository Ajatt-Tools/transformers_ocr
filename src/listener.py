# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU GPL, version 3 or later; http://www.gnu.org/licenses/gpl.html

import os
import subprocess
from typing import AnyStr

from manga_ocr import MangaOcr

PIPE_PATH = '/tmp/manga_ocr.fifo'
IS_XORG = 'WAYLAND_DISPLAY' not in os.environ
CLIP_COPY_ARGS = ('xclip', '-selection', 'clipboard',) if IS_XORG else ('wl-copy',)


def is_fifo(path: AnyStr) -> bool:
    import stat
    try:
        return stat.S_ISFIFO(os.stat(path).st_mode)
    except FileNotFoundError:
        return False


def to_clip(text: str):
    p = subprocess.Popen(CLIP_COPY_ARGS, stdin=subprocess.PIPE)
    p.communicate(input=text.encode())


def notify_send(msg: str):
    print(msg)
    subprocess.Popen(
        ('notify-send', 'manga-ocr', msg),
        shell=False
    )


def prepare_pipe():
    if os.path.isfile(PIPE_PATH):
        os.remove(PIPE_PATH)
    if not is_fifo(PIPE_PATH):
        os.mkfifo(PIPE_PATH)


def main():
    prepare_pipe()
    mocr = MangaOcr()
    print(f"Reading from {PIPE_PATH}")

    while True:
        with open(PIPE_PATH) as fifo:
            for line in fifo:
                line = line.strip()
                if os.path.isfile(line):
                    text = mocr(line)
                    to_clip(text)
                    os.remove(line)
                    notify_send(f"Copied {text}")
                elif line == '[[stop]]':
                    return notify_send("Stopped listening.")


if __name__ == '__main__':
    main()
