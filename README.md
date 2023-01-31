# transformers ocr

> https://tatsumoto.neocities.org/blog/mining-from-manga.html

[![AUR](https://img.shields.io/badge/AUR-install-blue)](https://aur.archlinux.org/packages/transformers_ocr)
[![Chat](https://img.shields.io/badge/chat-join-green)](https://tatsumoto-ren.github.io/blog/join-our-community.html)
![GitHub](https://img.shields.io/github/license/Ajatt-Tools/transformers_ocr)

An OCR tool using `maim` with `Transformers`.

https://user-images.githubusercontent.com/69171671/177458117-ba858b79-0b2e-4605-9985-5801d9685bd6.mp4

## Installation

### Arch Linux and Arch-based distros

Install [from the AUR](https://aur.archlinux.org/packages/transformers_ocr).

### To install manually

The steps below are for people who can't access the AUR.

Install the following dependencies if they are not installed.

* [pip](https://pypi.org/project/pip/)
* [maim](https://github.com/naelstrof/maim)
* [xclip](https://github.com/astrand/xclip)

<details>

<summary>Install using Makefile</summary>

```
git clone 'https://github.com/Ajatt-Tools/transformers_ocr.git'
cd -- 'transformers_ocr'
sudo make install
```

</details>

<details>

<summary>Install without Makefile</summary>

These steps install the program to `~/.local/bin`.
`~/.local/bin` should be added to the PATH.

```
mkdir -p ~/.local/share/transformers_ocr
git clone 'https://github.com/Ajatt-Tools/transformers_ocr.git' ~/.local/share/transformers_ocr
ln -sr ~/.local/share/transformers_ocr/transformers_ocr.sh ~/.local/bin/transformers_ocr
```

</details>

## Setup

Before you start,
download `manga-ocr` data:

```
transformers_ocr download
```

The files will be saved to `~/.local/share/manga_ocr`.

## Usage

To OCR text in on a manga page, run:

```
transformers_ocr recognize
```

Bind the command to a keyboard shortcut using your WM's config.
This enables you to call the OCR from anywhere, as shown in the demo video.

For example, if you use [i3wm](https://i3wm.org/),
add this line to the [config file](https://i3wm.org/docs/userguide.html#configuring).

```
bindsym $mod+o  exec --no-startup-id transformers_ocr recognize
```

The first run will take longer than usual.
There are additional files that will be downloaded and saved to `~/.cache/huggingface`.

On the first run `transformers_ocr` launches a listener process
that is running is the background and reads any new screenshots passed to it.
To speed up the first run, add the command below to autostart (using `~/.profile`, `~/.xinitrc`, etc.).

```
transformers_ocr start
```
