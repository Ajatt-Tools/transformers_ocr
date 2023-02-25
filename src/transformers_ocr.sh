#!/bin/bash

# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU GPL, version 3 or later; http://www.gnu.org/licenses/gpl.html

set -euo pipefail

readonly \
	PROGRAM=transformers_ocr \
	MANGA_OCR_PREFIX=$HOME/.local/share/manga_ocr \
	PIPE_PATH='/tmp/manga_ocr.fifo' \
	PID_FILE='/tmp/manga_ocr.pid'

this_bin_dir() {
	dirname -- "$(readlink -e -- "$0")"
}

ocr_lib_dir() {
	readlink -e -- "$(this_bin_dir)/../lib/$PROGRAM"
}

is_Xorg() {
	[[ ${WAYLAND_DISPLAY:-None} == None ]]
}

notify() {
	echo "$*"
	notify-send "Maim OCR" "$*" &
}

if_installed() {
	for x in "$@"; do
		if ! which "$x" >/dev/null 2>&1 && ! pacman -Qq "$x" >/dev/null 2>&1; then
			notify "$x must be installed for $PROGRAM to work."
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

if is_Xorg; then
	if_installed maim xclip || exit 1

	take_screenshot() {
		maim --select --hidecursor --format=png --quality 1
	}

	print_platform() {
		echo "Xorg"
	}
else
	if_installed grim slurp wl-copy || exit 1

	take_screenshot() {
		grim -g "$(slurp)" -
	}

	print_platform() {
		echo "Wayland"
	}
fi

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
	take_screenshot >"$screenshot_path"
	echo "$screenshot_path" >"$PIPE_PATH" &
}

get_pid() {
	local -r pid=$(cat -- "$PID_FILE")
	if [[ -n $pid ]] && kill -0 "$pid" >/dev/null 2>&1; then
		echo "$pid"
	else
		echo "None"
	fi
}

print_status() {
	if [[ $(get_pid) != None ]]; then
		echo "Running"
	else
		echo "Stopped"
	fi
}

report_status() {
	echo "$(print_status), $(print_platform)."
}

ensure_listening() {
	if [[ -d $MANGA_OCR_PREFIX ]]; then
		if [[ $(get_pid) == None ]]; then
			"$MANGA_OCR_PREFIX/pyenv/bin/python3" "$(ocr_lib_dir)/listener.py" &
			echo $! >"$PID_FILE"
			echo "Started manga_ocr listener."
			disown -a
		else
			echo "Already running."
		fi
	else
		notify "manga-ocr is not downloaded."
		exit 1
	fi
}

stop_listening() {
	local -r pid=$(get_pid)
	if [[ $pid != None ]]; then
		echo '[[stop]]' >"$PIPE_PATH" &
		(sleep 1s && kill -SIGTERM "$pid") >/dev/null 2>&1
	else
		notify "Already stopped."
	fi
}

help() {
	local -r prog=$(basename -- "$0")

	echo "Usage: $prog [COMMAND]"
	echo
	echo "An OCR tool that uses Transformers."
	echo
	echo "Options:"
	column -t -s'|' <<-EOF
		recognize|OCR a part of the screen.
		download|Download OCR files.
		start|Start listening.
		stop|Stop listening.
		status|Print listening status.
		help|Show this help screen.
	EOF
	echo
	echo "Platform: $(print_platform)"
	echo "You need to run '$prog download' once after installation."
	echo "$prog home page: https://github.com/Ajatt-Tools/transformers_ocr"
}

main() {
	prepare_pipe
	case ${1-} in
	download) download_manga_ocr ;;
	start | listen) ensure_listening ;;
	stop) stop_listening ;;
	status) report_status ;;
	recognize) run_ocr ;;
	help | -h | --help) help ;;
	*) echo "Unknown command." && help ;;
	esac
}

main "$@"
