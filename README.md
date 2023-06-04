# Transformers OCR

> https://tatsumoto.neocities.org/blog/mining-from-manga.html

[![AUR](https://img.shields.io/badge/AUR-install-blue)](https://aur.archlinux.org/packages/transformers_ocr)
[![Chat](https://img.shields.io/badge/chat-join-green)](https://tatsumoto-ren.github.io/blog/join-our-community.html)
![GitHub](https://img.shields.io/github/license/Ajatt-Tools/transformers_ocr)

An OCR tool for the GNU operating system that uses `Transformers`.
Supports Xorg and Wayland.

https://user-images.githubusercontent.com/69171671/177458117-ba858b79-0b2e-4605-9985-5801d9685bd6.mp4

This Manga OCR application is likely the most suckless and lightweight option available.
The application is designed to work best with a tiling window manager.
It requires a minimum of dependencies, and all of them you probably already have.
However, it still has to rely on large Python libraries to work.
To isolate the bloat, these libraries are installed in a dedicated folder.
But if your computer is rather slow, use Tesseract instead.

## Installation

### Arch Linux and Arch-based distros

Install [from the AUR](https://aur.archlinux.org/packages/transformers_ocr).

### Other distros

If you want to package this program for your distribution and know how to do it,
please create a pull request.
Otherwise, read the section below.

### To install manually

The steps below are for people who can't access the AUR.

Install the following dependencies if they are not installed.

<details>

<summary>Xorg</summary>

* [pip](https://pypi.org/project/pip/)
* [maim](https://github.com/naelstrof/maim)
* [xclip](https://github.com/astrand/xclip)

</details>

<details>

<summary>Wayland</summary>

* [pip](https://pypi.org/project/pip/)
* [grim](https://git.sr.ht/~emersion/grim)
* [slurp](https://github.com/emersion/slurp)
* [wl-copy](https://github.com/bugaevc/wl-clipboard)

</details>

<details>

<summary>GNOME</summary>

* [pip](https://pypi.org/project/pip/)
* [gnome-screenshot](https://gitlab.gnome.org/GNOME/gnome-screenshot)
* [wl-copy](https://github.com/bugaevc/wl-clipboard)

</details>

<details>

<summary>KDE</summary>

* [pip](https://pypi.org/project/pip/)
* [spectacle](https://github.com/KDE/spectacle/)
* [wl-copy](https://github.com/bugaevc/wl-clipboard)

</details>

**Install using Makefile:**

```
git clone 'https://github.com/Ajatt-Tools/transformers_ocr.git'
cd -- 'transformers_ocr'
sudo make install
```

## Setup

Before you start,
download `manga-ocr` data:

```
transformers_ocr download
```

The files will be saved to `~/.local/share/manga_ocr`.

## Usage

To show a help page, run `transformers_ocr help`.

To OCR text on a manga page, run:

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

## Holding text

Quite often one sentence, phrase or a chunk of meaning
is split between two or more speech bubbles.
This is a problem because if you take a screenshot of the whole area,
including the area between the speech bubbles,
you will likely end up with junk in the results.
Processing each bubble separately is also not ideal
since you want to analyze the entire sentence in GoldenDict, add it to Anki, etc.

A solution is to have `transformers-ocr` hold text for you.
It will recognize one speech bubble, remember it, then wait for another,
and only copy the text from all bubbles altogether when you're done.

To use this feature, add a new keyboard shortcut to the config file of your WM,
for example <kbd>Mod+Shift+o</kbd>.
Example for `i3wm`:

```
bindsym $mod+Shift+o  exec --no-startup-id transformers_ocr hold
```

https://user-images.githubusercontent.com/69171671/233484898-776ea15a-5a7a-443a-ac2e-5d06fb61540b.mp4

Every time you call `hold`, a speech bubble will be recognized and saved for later.
Finally, call `recognize` using the usual keyboard shortcut
to copy the last speech bubble and all the saved ones together.
The list of saved bubbles will be emptied when calling `recognize`.

## Config file

Optionally, you can create a config file.

```
mkdir -p ~/.config/transformers_ocr
touch ~/.config/transformers_ocr/config
```

Each line must have this format: `key=value`.
Lines that start with `#` are ignored.

## Send text to an external application

Instead of copying text to the clipboard,
you may want to pass it as an argument to an external application.
In the example below `clip_command` is set to `goldendict`
which allows you to send recognized text directly to GoldenDict
and keep the system clipboard for other tasks.

```
echo 'clip_command=goldendict %TEXT%' >> ~/.config/transformers_ocr/config
transformers_ocr stop
transformers_ocr start
```

If `%TEXT%` is passed as a parameter,
it will be replaced with the actual text in the speech bubble.
If not, the text will be passed to `stdin` of the called program.

## Force CPU

If you want to force CPU.

```
echo 'force_cpu=yes' >> ~/.config/transformers_ocr/config
```
