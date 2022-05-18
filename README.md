# transformers_ocr

> https://tatsumoto.neocities.org/blog/mining-from-manga.html

[![AUR](https://img.shields.io/badge/AUR-install-blue)](https://aur.archlinux.org/packages/transformers_ocr)
[![Chat](https://img.shields.io/badge/chat-join-green)](https://tatsumoto-ren.github.io/blog/join-our-community.html)
![GitHub](https://img.shields.io/github/license/Ajatt-Tools/transformers_ocr)

An OCR tool using maim with Transformers.

## Installation

Install [from the AUR](https://aur.archlinux.org/packages/transformers_ocr).

<details>

<summary>To install manually</summary>

The steps below are for people who can't access the AUR.

```
mkdir -p ~/.local/share/transformers_ocr
git clone 'https://github.com/Ajatt-Tools/transformers_ocr.git' ~/.local/share/transformers_ocr
ln -s ~/.local/share/transformers_ocr/transformers_ocr.sh ~/.local/bin/transformers_ocr
```

`transformers_ocr` depends on:

* [pip](https://pypi.org/project/pip/)
* [maim](https://github.com/naelstrof/maim)
* [xclip](https://github.com/astrand/xclip)

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

The first run will take longer than usual.
There's additional files that will be downloaded and saved to `~/.cache/huggingface`.

On the first run `transformers_ocr` launches a listener process that is running is the background
and reads any new screenshots passed to it.
To speed up the first run, add the command below to autostart (using `~/.profile`, `~/.xinitrc`, etc.).

```
transformers_ocr start
```
