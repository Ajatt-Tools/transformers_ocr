# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU GPL, version 3 or later; http://www.gnu.org/licenses/gpl.html

import os
import subprocess
from typing import AnyStr, Collection

from manga_ocr import MangaOcr

PIPE_PATH = "/tmp/manga_ocr.fifo"
IS_XORG = "WAYLAND_DISPLAY" not in os.environ
CLIP_COPY_ARGS = (
    ("xclip", "-selection", "clipboard",)
    if IS_XORG
    else ("wl-copy",)
)
CONFIG_PATH = os.path.join(
    os.environ.get("XDG_CONFIG_HOME", os.path.join(os.environ["HOME"], ".config")),
    "transformers_ocr",
    "config",
)


def is_fifo(path: AnyStr) -> bool:
    import stat

    try:
        return stat.S_ISFIFO(os.stat(path).st_mode)
    except FileNotFoundError:
        return False


def to_clip(text: str, custom_clip_args: Collection[str] | None):
    if custom_clip_args is None:
        p = subprocess.Popen(CLIP_COPY_ARGS, stdin=subprocess.PIPE)
        p.communicate(input=text.encode())
    else:
        subprocess.Popen([*custom_clip_args, text], shell=False)


def notify_send(msg: str):
    print(msg)
    subprocess.Popen(("notify-send", "manga-ocr", msg), shell=False)


def prepare_pipe():
    if os.path.isfile(PIPE_PATH):
        os.remove(PIPE_PATH)
    if not is_fifo(PIPE_PATH):
        os.mkfifo(PIPE_PATH)


def is_valid_key_val_pair(line: str) -> bool:
    return '=' in line and not line.startswith('#')


def get_config() -> dict[str, str]:
    config = {}
    if os.path.isfile(CONFIG_PATH):
        with open(CONFIG_PATH, encoding='utf8') as f:
            for line in filter(is_valid_key_val_pair, f.read().splitlines()):
                key, value = line.split("=", maxsplit=1)
                config[key] = value
    return config


class TrOcrConfig:
    def __init__(self):
        self._config = get_config()
        self.force_cpu = self._should_force_cpu()
        self.clip_args = self._custom_clip_args()

    def _should_force_cpu(self) -> bool:
        return bool(self._config.get('force_cpu', 'no') in ('true', 'yes',))

    def _custom_clip_args(self) -> list[str] | None:
        try:
            return self._config["clip_command"].strip().split()
        except (KeyError, AttributeError):
            return None


class MangaOcrWrapper:
    def __init__(self):
        self._config = TrOcrConfig()
        self._mocr = MangaOcr(force_cpu=self._config.force_cpu)

    def init(self):
        prepare_pipe()
        print(f"Reading from {PIPE_PATH}")
        print(f"Custom clip args: {self._config.clip_args}")
        return self

    def loop(self):
        while True:
            with open(PIPE_PATH) as fifo:
                for line in fifo:
                    line = line.strip()
                    if os.path.isfile(line):
                        text = self._mocr(line)
                        to_clip(text, custom_clip_args=self._config.clip_args)
                        os.remove(line)
                        notify_send(f"Copied {text}")
                    elif line == "[[stop]]":
                        return notify_send("Stopped listening.")


def main():
    (
        MangaOcrWrapper()
        .init()
        .loop()
    )


if __name__ == "__main__":
    main()
