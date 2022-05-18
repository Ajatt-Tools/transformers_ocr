#!/bin/bash

# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU GPL, version 3 or later; http://www.gnu.org/licenses/gpl.html

set -euo pipefail

readonly \
	THIS_DIR=$(dirname -- "$(readlink -f "$0")") \
	MANGA_OCR_PREFIX=$HOME/.local/share/manga_ocr \
	PIPE_PATH='/tmp/manga_ocr.fifo' \
	PID_FILE='/tmp/manga_ocr.pid'

notify() {
	echo "$*"
	notify-send "Maim OCR" "$*"
}

if_installed() {
	for x in "$@"; do
		if ! which "$x" >/dev/null 2>&1 && ! pacman -Qq "$x" >/dev/null 2>&1; then
			notify "$x must be installed for this function."
			return 1
		fi
	done
}

download_manga_ocr() {
	echo "Downloading manga-ocr..."
	mkdir -p -- "$MANGA_OCR_PREFIX"
	cd -- "$MANGA_OCR_PREFIX"
	python3 -m venv pyenv
	pyenv/bin/pip install --upgrade 'pip'
	pyenv/bin/pip install --upgrade 'manga-ocr'
	echo "Downloaded manga-ocr."
}

take_screenshot() {
	maim --select --hidecursor --format=png --quality 1 |
		convert png:- -alpha off -bordercolor White -border 10x10 png:-
}

prepare_pipe() {
	if [[ -f $PIPE_PATH ]]; then
		rm -- "$PIPE_PATH"
	fi
	if ! [[ -p $PIPE_PATH ]]; then
		mkfifo -- "$PIPE_PATH"
	fi
}

run_ocr() {
	ensure_listening
	local -r screenshot_path=$(mktemp /tmp/screenshot.XXXXXX)
	if [[ -d $MANGA_OCR_PREFIX ]]; then
		take_screenshot >"$screenshot_path"
		echo "$screenshot_path" >"$PIPE_PATH" &
	else
		notify "manga-ocr is not downloaded."
	fi
}

ensure_listening() {
	local -r pid=$(cat -- "$PID_FILE")
	if ! kill -0 "$pid"; then
		echo "Starting manga_ocr listener."
		"$MANGA_OCR_PREFIX/pyenv/bin/python3" "$THIS_DIR/listener.py" &
		echo $! >"$PID_FILE"
	fi
}

stop_listening() {
	local -r pid=$(cat -- "$PID_FILE")
	if [[ -n $pid ]] && kill -0 "$pid"; then
		echo '[[stop]]' >"$PIPE_PATH" &
		(sleep 1s && kill -SIGTERM "$pid")
	fi
}

help() {
	echo "Usage: $(basename -- "$0") [COMMAND]"
	echo
	echo "An OCR script that uses maim and manga-ocr."
	echo
	echo "Options:"
	column -t -s'|' <<-EOF
		recognize|OCR a part of the screen.
		download|Download manga-ocr files.
		start|Start listening.
		stop|Stop listening.
		help|Show this help screen.
	EOF
}

main() {
	if_installed maim convert xclip || exit 1
	prepare_pipe
	case ${1-} in
		download) download_manga_ocr ;;
		start) ensure_listening ;;
		stop) stop_listening ;;
		recognize) run_ocr ;;
		help|-h|--help) help ;;
		*) echo "Unknown command." && help ;;
	esac
}

main "$@"
