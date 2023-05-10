#!/bin/python3
# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU GPL, version 3 or later; http://www.gnu.org/licenses/gpl.html

import argparse
import dataclasses
import os
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
from argparse import RawTextHelpFormatter
from typing import AnyStr, Collection, IO

PROGRAM = "transformers_ocr"
MANGA_OCR_PREFIX = os.path.join(os.environ["HOME"], ".local", "share", "manga_ocr")
MANGA_OCR_PYENV_PATH = os.path.join(MANGA_OCR_PREFIX, "pyenv")
MANGA_OCR_PYENV_PIP_PATH = os.path.join(MANGA_OCR_PYENV_PATH, "bin", "pip")

PIPE_PATH = "/tmp/manga_ocr.fifo"
PID_FILE = "/tmp/manga_ocr.pid"

SPACE = "、"
CONFIG_PATH = os.path.join(
    os.environ.get("XDG_CONFIG_HOME", os.path.join(os.environ["HOME"], ".config")),
    "transformers_ocr",
    "config",
)


def get_clip_copy_args():
    if is_Xorg():
        return (
            "xclip",
            "-selection",
            "clipboard",
        )
    else:
        return (
            "wl-copy",
        )


def get_platform():
    if is_Xorg():
        return "Xorg"
    elif is_GNOME():
        return "GNOME"
    else:
        return "Wayland"


def is_Xorg():
    return "WAYLAND_DISPLAY" not in os.environ


def is_GNOME():
    return os.environ.get("XDG_CURRENT_DESKTOP") == "GNOME"


def is_pacman_installed(program: str) -> bool:
    return subprocess.call(["pacman", "-Qq", program], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, ) == 0


def if_installed(*programs):
    for prog in programs:
        if not shutil.which(prog) and not is_pacman_installed(prog):
            notify_send(f"{prog} must be installed for {PROGRAM} to work.")
            sys.exit(1)


def gnome_screenshot_select(screenshot_path: str):
    return subprocess.run(
        ("gnome-screenshot", "-a", "-f", screenshot_path),
        check=True,
    )


def maim_select(screenshot_path: str):
    return subprocess.run(
        ("maim", "--select", "--hidecursor", "--format=png", "--quality", "1", screenshot_path,),
        check=True,
    )


def grim_select(screenshot_path: str):
    return subprocess.run(
        ("grim", "-g", subprocess.check_output(["slurp"]).decode().strip(), screenshot_path,),
        check=True,
    )


def take_screenshot(screenshot_path):
    if is_GNOME():
        if_installed("gnome-screenshot", "wl-copy")
        gnome_screenshot_select(screenshot_path)
    elif is_Xorg():
        if_installed("maim", "xclip")
        maim_select(screenshot_path)
    else:
        if_installed("grim", "slurp", "wl-copy")
        grim_select(screenshot_path)


def prepare_pipe():
    if os.path.isfile(PIPE_PATH):
        os.remove(PIPE_PATH)
    if not is_fifo(PIPE_PATH):
        os.mkfifo(PIPE_PATH)


def run_ocr(command):
    ensure_listening()
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as screenshot_file:
        take_screenshot(screenshot_file.name)
        with open(PIPE_PATH, "w") as pipe:
            pipe.write(f"{command}::{screenshot_file.name}")


def get_pid():
    try:
        with open(PID_FILE) as pid_file:
            pid = int(pid_file.read())
            if pid > 0 and os.path.exists(f"/proc/{pid}"):
                return pid
            else:
                return None
    except (ValueError, FileNotFoundError):
        return None


def ensure_listening():
    if os.path.exists(MANGA_OCR_PREFIX):
        if get_pid() is None:
            p = subprocess.Popen(
                [
                    os.path.join(MANGA_OCR_PREFIX, "pyenv", "bin", "python3"),
                    __file__,
                    "start",
                    "--foreground",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            with open(PID_FILE, "w") as pid_file:
                pid_file.write(str(p.pid))
            print("Started manga_ocr listener.")
        else:
            print("Already running.")
    else:
        print("manga-ocr is not downloaded.")
        sys.exit(1)


def stop_listening():
    pid = get_pid()
    if pid is not None:
        with open(PIPE_PATH, "w") as pipe:
            pipe.write("stop::")
        time.sleep(1)
        os.kill(pid, signal.SIGTERM)
    else:
        print("Already stopped.")


def is_fifo(path: AnyStr) -> bool:
    try:
        return stat.S_ISFIFO(os.stat(path).st_mode)
    except FileNotFoundError:
        return False


def to_clip(text: str, custom_clip_args: Collection[str] | None):
    if custom_clip_args is None:
        p = subprocess.Popen(get_clip_copy_args(), stdin=subprocess.PIPE)
        p.communicate(input=text.encode())
    else:
        subprocess.Popen([*custom_clip_args, text], shell=False)


def notify_send(msg: str):
    print(msg)
    subprocess.Popen(("notify-send", "manga-ocr", msg), shell=False)


def is_valid_key_val_pair(line: str) -> bool:
    return "=" in line and not line.startswith("#")


def get_config() -> dict[str, str]:
    config = {}
    if os.path.isfile(CONFIG_PATH):
        with open(CONFIG_PATH, encoding="utf8") as f:
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


@dataclasses.dataclass
class OcrCommand:
    action: str
    file_path: str


def iter_commands(stream: IO):
    yield from (OcrCommand(*line.strip().split("::")) for line in stream)


class MangaOcrWrapper:
    def __init__(self):
        from manga_ocr import MangaOcr  # type: ignore

        self._config = TrOcrConfig()
        self._mocr = MangaOcr(force_cpu=self._config.force_cpu)
        self._on_hold = []

    def init(self):
        prepare_pipe()
        print(f"Reading from {PIPE_PATH}")
        print(f"Custom clip args: {self._config.clip_args}")
        return self

    def _process_command(self, command: OcrCommand):
        match command:
            case OcrCommand("stop", _):
                return notify_send("Stopped listening.")
            case OcrCommand(action=action, file_path=file_path) if os.path.isfile(file_path):
                match action:
                    case "hold":
                        text = self._mocr(file_path)
                        self._on_hold.append(text)
                        notify_send(f"Holding {text}")
                    case "recognize":
                        text = SPACE.join((*self._on_hold, self._mocr(file_path)))
                        to_clip(text, custom_clip_args=self._config.clip_args)
                        notify_send(f"Copied {text}")
                        self._on_hold.clear()
                os.remove(file_path)

    def loop(self):
        while True:
            with open(PIPE_PATH) as fifo:
                for command in iter_commands(fifo):
                    self._process_command(command)


def run_listener():
    return MangaOcrWrapper().init().loop()


def start_listening(args):
    if args.foreground:
        run_listener()
    else:
        ensure_listening()


def restart_listener():
    stop_listening()
    ensure_listening()


def status_str():
    return "Running" if get_pid() else "Stopped"


def print_status():
    print(f"{status_str()}, {get_platform()}.")


def download_manga_ocr():
    print("Downloading manga-ocr...")
    os.makedirs(MANGA_OCR_PREFIX, exist_ok=True)
    subprocess.run(
        ["python3", "-m", "venv", "--system-site-packages", "--symlinks", MANGA_OCR_PYENV_PATH, ],
        check=True,
    )
    subprocess.run(
        [MANGA_OCR_PYENV_PIP_PATH, "install", "--upgrade", "pip", ],
        check=True,
    )
    subprocess.run(
        [MANGA_OCR_PYENV_PIP_PATH, "install", "--upgrade", "manga-ocr", ],
        check=True,
    )
    print("Downloaded manga-ocr.")


def prog_name():
    return os.path.basename(sys.argv[0])


def main():
    prepare_pipe()
    parser = argparse.ArgumentParser(
        description="An OCR tool that uses Transformers.",
        epilog=f"""
    Platform: {get_platform()}
    You need to run '{prog_name()} download' once after installation.
    {prog_name()} home page: https://github.com/Ajatt-Tools/transformers_ocr""",
        formatter_class=RawTextHelpFormatter,
    )
    subparsers = parser.add_subparsers(title="Options")

    recognize_parser = subparsers.add_parser("recognize", help="OCR a part of the screen.", aliases=["ocr"])
    recognize_parser.set_defaults(func=lambda _args: run_ocr("recognize"))

    hold_parser = subparsers.add_parser("hold", help="OCR a part of the screen.")
    hold_parser.set_defaults(func=lambda _args: run_ocr("hold"))

    download_parser = subparsers.add_parser("download", help="Download OCR files.")
    download_parser.set_defaults(func=lambda _args: download_manga_ocr())

    start_parser = subparsers.add_parser("start", help="Start listening.", aliases=["listen"])
    start_parser.add_argument("--foreground", action="store_true")
    start_parser.set_defaults(func=start_listening)

    stop_parser = subparsers.add_parser("stop", help="Stop listening")
    stop_parser.set_defaults(func=lambda _args: stop_listening())

    status_parser = subparsers.add_parser("status", help="Print listening status.")
    status_parser.set_defaults(func=lambda _args: print_status())

    restart_parser = subparsers.add_parser("restart", help="Restart the program")
    restart_parser.set_defaults(func=lambda _args: restart_listener())

    args = parser.parse_args()

    if len(sys.argv) < 2:
        parser.print_help()
    else:
        args.func(args)


if __name__ == "__main__":
    main()
