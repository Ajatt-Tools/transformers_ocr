#!/usr/bin/env python3
# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU GPL, version 3 or later; http://www.gnu.org/licenses/gpl.html

import os
import signal
import shutil
import sys
import subprocess
import tempfile

PROGRAM = "transformers_ocr"
MANGA_OCR_PREFIX = os.path.join(os.environ["HOME"], ".local", "share", "manga_ocr")
PIPE_PATH = "/tmp/manga_ocr.fifo"
PID_FILE = "/tmp/manga_ocr.pid"

def this_bin_dir():
    return os.path.dirname(os.path.realpath(__file__))

def ocr_lib_dir():
    return os.path.realpath(os.path.join(this_bin_dir(), "..", "lib", PROGRAM))

def is_Xorg():
    return os.environ.get("WAYLAND_DISPLAY") is None

def is_GNOME():
    return os.environ.get("XDG_CURRENT_DESKTOP") == "GNOME"

def notify(msg):
    print(msg)
    subprocess.Popen(["notify-send", "Maim OCR", msg])

def if_installed(*programs):
    for prog in programs:
        if not shutil.which(prog) and subprocess.call(["pacman", "-Qq", prog], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
            notify(f"{prog} must be installed for {PROGRAM} to work.")
            sys.exit(1)

def download_manga_ocr():
    print("Downloading manga-ocr...")
    os.makedirs(MANGA_OCR_PREFIX, exist_ok=True)
    subprocess.run(["python3", "-m", "venv", "--system-site-packages", "--symlinks", os.path.join(MANGA_OCR_PREFIX, "pyenv")], check=True)
    subprocess.run([os.path.join(MANGA_OCR_PREFIX, "pyenv", "bin", "pip"), "install", "--upgrade", "pip"], check=True)
    subprocess.run([os.path.join(MANGA_OCR_PREFIX, "pyenv", "bin", "pip"), "install", "--upgrade", "manga-ocr"], check=True)
    print("Downloaded manga-ocr.")

def take_screenshot(screenshot_path):
    if is_Xorg():
        if_installed("maim", "xclip")
        subprocess.run(["maim", "--select", "--hidecursor", "--format=png", "--quality", "1", screenshot_path], check=True)
    elif is_GNOME():
        if_installed("gnome-screenshot", "wl-copy")
        subprocess.run(["gnome-screenshot", "-a", "-f", screenshot_path], check=True)
    else:
        if_installed("grim", "slurp", "wl-copy")
        subprocess.run(["grim", "-g", subprocess.check_output(["slurp"]).decode().strip(), screenshot_path], check=True)

def print_platform():
    if is_Xorg():
        return "Xorg"
    elif is_GNOME():
        return "GNOME"
    else:
        return "Wayland"

def prepare_pipe():
    if os.path.exists(PIPE_PATH):
        os.unlink(PIPE_PATH)
    if not os.path.exists(PIPE_PATH):
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


def print_status():
    if get_pid() is not None:
        return "Running"
    else:
        return "Stopped"


def report_status():
    print(f"{print_status()}, {print_platform()}.")

def ensure_listening():
    if os.path.exists(MANGA_OCR_PREFIX):
        if get_pid() is None:
            p = subprocess.Popen(
                [os.path.join(MANGA_OCR_PREFIX, "pyenv", "bin", "python3"), os.path.join(this_bin_dir(), "listener.py")],
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
        os.kill(pid, signal.SIGTERM)
        os.waitpid(pid, 0)
    else:
        print("Already stopped.")


def help():
    prog = os.path.basename(sys.argv[0])
    print(f"Usage: {prog} [COMMAND]\n")
    print("An OCR tool that uses Transformers.\n")
    print("Options:")
    print("  recognize|OCR a part of the screen.")
    print("  download|Download OCR files.")
    print("  start|Start listening.")
    print("  stop|Stop listening.")
    print("  status|Print listening status.")
    print("  help|Show this help screen.\n")
    print(f"Platform: {print_platform()}")
    print("You need to run 'download' once after installation.")
    print(f"{prog} home page: https://github.com/Ajatt-Tools/transformers_ocr")
