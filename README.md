# transformers_ocr

An OCR tool using maim with Transformers.

## Installation

To install manually, run:

```
mkdir -p ~/.local/share/transformers_ocr
git clone 'https://github.com/Ajatt-Tools/transformers_ocr.git' ~/.local/share/transformers_ocr
ln -s ~/.local/share/transformers_ocr/transformers_ocr.sh ~/.local/bin/transformers_ocr
```

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
