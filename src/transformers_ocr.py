#!/bin/python3
# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU GPL, version 3 or later; http://www.gnu.org/licenses/gpl.html

import argparse
import dataclasses
import datetime
import enum
import json
import os
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
from argparse import RawTextHelpFormatter
from typing import AnyStr, Collection, IO, Iterable

MANGA_OCR_PREFIX = os.path.join(os.environ["HOME"], ".local", "share", "manga_ocr")
MANGA_OCR_PYENV_PATH = os.path.join(MANGA_OCR_PREFIX, "pyenv")
MANGA_OCR_PYENV_PIP_PATH = os.path.join(MANGA_OCR_PYENV_PATH, "bin", "pip")
HUGGING_FACE_CACHE_PATH = os.path.join(os.environ["HOME"], '.cache', 'huggingface')
CONFIG_PATH = os.path.join(
    os.environ.get("XDG_CONFIG_HOME", os.path.join(os.environ["HOME"], ".config")),
    "transformers_ocr",
    "config",
)
PIPE_PATH = "/tmp/manga_ocr.fifo"
PID_FILE = "/tmp/manga_ocr.pid"
PROGRAM = "transformers_ocr"
JOIN = "、"
IS_XORG = "WAYLAND_DISPLAY" not in os.environ
IS_GNOME = os.environ.get("XDG_CURRENT_DESKTOP") == "GNOME"
IS_KDE = os.environ.get("XDG_CURRENT_DESKTOP") == "KDE"
CLIP_COPY_ARGS = (
    ("xclip", "-selection", "clipboard",)
    if IS_XORG
    else ("wl-copy",)
)


class Platform(enum.Enum):
    GNOME = enum.auto()
    KDE = enum.auto()
    Xorg = enum.auto()
    Wayland = enum.auto()

    @classmethod
    def current(cls):
        if IS_GNOME:
            return cls.GNOME
        elif IS_KDE:
            return cls.KDE
        elif IS_XORG:
            return cls.Xorg
        else:
            return cls.Wayland


CURRENT_PLATFORM = Platform.current()


class MissingProgram(RuntimeError):
    pass


class StopRequested(Exception):
    pass


class ScreenshotCancelled(RuntimeError):
    pass


@dataclasses.dataclass
class OcrCommand:
    action: str
    file_path: str | None

    def as_json(self):
        return json.dumps(dataclasses.asdict(self))


def is_pacman_installed(program: str) -> bool:
    return subprocess.call(("pacman", "-Qq", program,), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, ) == 0


def is_installed(program: str) -> bool:
    return shutil.which(program) or is_pacman_installed(program)


def raise_if_missing(*programs):
    for prog in programs:
        if not is_installed(prog):
            raise MissingProgram(f"{prog} must be installed for {PROGRAM} to work.")


def gnome_screenshot_select(screenshot_path: str):
    return subprocess.run(
        ("gnome-screenshot", "-a", "-f", screenshot_path,),
        check=True,
    )


def spectactle_select(screenshot_path: str):
    return subprocess.run(
        ("spectacle", "-b", "-r", "-o", screenshot_path,),
        check=True,
        stderr=subprocess.DEVNULL
    )


def maim_select(screenshot_path: str):
    return subprocess.run(
        ("maim", "--select", "--hidecursor", "--format=png", "--quality", "1", screenshot_path,),
        check=True,
        stderr=sys.stdout,
    )


def grim_select(screenshot_path: str):
    return subprocess.run(
        ("grim", "-g", subprocess.check_output(["slurp"]).decode().strip(), screenshot_path,),
        check=True,
    )


def take_screenshot(screenshot_path):
    match CURRENT_PLATFORM:
        case Platform.GNOME:
            raise_if_missing("gnome-screenshot", "wl-copy")
            gnome_screenshot_select(screenshot_path)
        case Platform.KDE:
            raise_if_missing("spectacle", "wl-copy")
            spectactle_select(screenshot_path)
        case Platform.Xorg:
            raise_if_missing("maim", "xclip")
            maim_select(screenshot_path)
        case Platform.Wayland:
            raise_if_missing("grim", "slurp", "wl-copy")
            grim_select(screenshot_path)


def prepare_pipe():
    if os.path.isfile(PIPE_PATH):
        os.remove(PIPE_PATH)
    if not is_fifo(PIPE_PATH):
        os.mkfifo(PIPE_PATH)


def run_ocr(command):
    ensure_listening()
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as screenshot_file:
        try:
            take_screenshot(screenshot_file.name)
        except subprocess.CalledProcessError as ex:
            raise ScreenshotCancelled() from ex
        with open(PIPE_PATH, "w") as pipe:
            pipe.write(OcrCommand(action=command, file_path=screenshot_file.name).as_json())


def is_running(pid: int) -> bool:
    return pid > 0 and os.path.exists(f"/proc/{pid}")


def get_pid() -> int | None:
    try:
        with open(PID_FILE) as pid_file:
            pid = int(pid_file.read())
    except (ValueError, FileNotFoundError):
        return None
    else:
        return pid if is_running(pid) else None


def ensure_listening():
    if os.path.exists(MANGA_OCR_PREFIX):
        if get_pid() is None:
            p = subprocess.Popen(
                (
                    os.path.join(MANGA_OCR_PREFIX, "pyenv", "bin", "python3"),
                    __file__,
                    "start",
                    "--foreground",
                ),
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


def kill_after(pid: int, timeout_s: float, step_s: float = 0.1):
    for _step in range(int(timeout_s // step_s)):
        if get_pid() is None:
            print(" Stopped.")
            break
        time.sleep(step_s)
        print(".", end="", flush=True)
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    else:
        print(" Killed.")


def stop_listening():
    if (pid := get_pid()) is not None:
        with open(PIPE_PATH, "w") as pipe:
            pipe.write(OcrCommand(action="stop", file_path=None).as_json())
        kill_after(pid, timeout_s=3)
    else:
        print("Already stopped.")


def is_fifo(path: AnyStr) -> bool:
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
    try:
        subprocess.Popen(("notify-send", "manga-ocr", msg,), shell=False)
    except FileNotFoundError:
        pass


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
        self.screenshot_dir = self._get_screenshot_dir()

    def _should_force_cpu(self) -> bool:
        return bool(self._config.get('force_cpu', 'no') in ('true', 'yes',))

    def _custom_clip_args(self) -> list[str] | None:
        try:
            return self._config["clip_command"].strip().split()
        except (KeyError, AttributeError):
            return None

    def _get_screenshot_dir(self):
        if (screenshot_dir := self._config.get('screenshot_dir')) and os.path.isdir(screenshot_dir):
            return screenshot_dir


def iter_commands(stream: IO) -> Iterable[OcrCommand]:
    yield from (OcrCommand(**json.loads(line)) for line in stream)


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

    def _ocr(self, file_path: str) -> str:
        return (
            self._mocr(file_path)
            .replace('...', '…')
            .replace('。。。', '…')
        )

    def _process_command(self, command: OcrCommand):
        match command:
            case OcrCommand("stop", _):
                raise StopRequested()
            case OcrCommand(action=action, file_path=file_path) if os.path.isfile(file_path):
                match action:
                    case "hold":
                        text = self._ocr(file_path)
                        self._on_hold.append(text)
                        notify_send(f"Holding {text}")
                    case "recognize":
                        text = JOIN.join((*self._on_hold, self._ocr(file_path)))
                        to_clip(text, custom_clip_args=self._config.clip_args)
                        notify_send(f"Copied {text}")
                        self._on_hold.clear()
                        self._maybe_save_result(file_path, text)
                os.remove(file_path)

    def _maybe_save_result(self, file_path, text):
        if self._config.screenshot_dir:
            name_pattern = datetime.datetime.now().strftime("trocr_%Y%m%d_%H%M%S")
            text_file_path = os.path.join(self._config.screenshot_dir, f'{name_pattern}.gt.txt')
            png_file_path = os.path.join(self._config.screenshot_dir, f'{name_pattern}.png')
            with open(text_file_path, 'w', encoding='utf8') as of:
                of.write(text)
            shutil.copy(file_path, png_file_path)

    def loop(self):
        try:
            while True:
                with open(PIPE_PATH) as fifo:
                    for command in iter_commands(fifo):
                        self._process_command(command)
        except StopRequested:
            return notify_send("Stopped listening.")


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
    print(f"{status_str()}, {CURRENT_PLATFORM.name}.")


def download_manga_ocr():
    print("Downloading manga-ocr...")
    os.makedirs(MANGA_OCR_PREFIX, exist_ok=True)
    subprocess.run(
        ("python3", "-m", "venv", "--system-site-packages", "--symlinks", MANGA_OCR_PYENV_PATH,),
        check=True,
    )
    subprocess.run(
        (MANGA_OCR_PYENV_PIP_PATH, "install", "--upgrade", "pip",),
        check=True,
    )
    subprocess.run(
        (MANGA_OCR_PYENV_PIP_PATH, "install", "--upgrade", "manga-ocr",),
        check=True,
    )
    print("Downloaded manga-ocr.")


def prog_name():
    return os.path.basename(sys.argv[0])


def purge_manga_ocr_data():
    shutil.rmtree(MANGA_OCR_PREFIX, ignore_errors=True)
    shutil.rmtree(HUGGING_FACE_CACHE_PATH, ignore_errors=True)
    print("Purged all downloaded manga-ocr data.")


def create_args_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="An OCR tool that uses Transformers.",
        formatter_class=RawTextHelpFormatter,
    )
    parser.epilog = f"""
Platform: {CURRENT_PLATFORM.name}
You need to run '{prog_name()} download' once after installation.
{prog_name()} home page: https://github.com/Ajatt-Tools/transformers_ocr"""

    subparsers = parser.add_subparsers(title="commands")

    recognize_parser = subparsers.add_parser("recognize", help="OCR a part of the screen.", aliases=["ocr"])
    recognize_parser.set_defaults(func=lambda _args: run_ocr("recognize"))

    hold_parser = subparsers.add_parser("hold", help="OCR and hold a part of the screen.")
    hold_parser.set_defaults(func=lambda _args: run_ocr("hold"))

    download_parser = subparsers.add_parser("download", help="Download OCR files.")
    download_parser.set_defaults(func=lambda _args: download_manga_ocr())

    start_parser = subparsers.add_parser("start", help="Start listening.", aliases=["listen"])
    start_parser.add_argument("--foreground", action="store_true")
    start_parser.set_defaults(func=start_listening)

    stop_parser = subparsers.add_parser("stop", help="Stop listening.")
    stop_parser.set_defaults(func=lambda _args: stop_listening())

    status_parser = subparsers.add_parser("status", help="Print listening status.")
    status_parser.set_defaults(func=lambda _args: print_status())

    restart_parser = subparsers.add_parser("restart", help="Restart the program.")
    restart_parser.set_defaults(func=lambda _args: restart_listener())

    nuke_parser = subparsers.add_parser("purge", help="Purge all manga-ocr data.", aliases=["nuke"])
    nuke_parser.set_defaults(func=lambda _args: purge_manga_ocr_data())

    return parser


def main():
    prepare_pipe()
    parser = create_args_parser()
    if len(sys.argv) < 2:
        return parser.print_help()
    args = parser.parse_args()
    try:
        args.func(args)
    except MissingProgram as ex:
        notify_send(str(ex))
    except ScreenshotCancelled:
        notify_send("Screenshot cancelled.")


if __name__ == "__main__":
    main()
