# AES-256 Hex Generator for DMR Radios

This Python script generates cryptographically secure AES-256 keys suitable for use with DMR (Digital Mobile Radio) encryption. It provides a colorful progress bar, automatically copies generated keys to the clipboard, and allows you to generate multiple keys interactively.

---

## Features

- Generates secure AES-256 keys (32 bytes / 256 bits) in hexadecimal format.
- Automatically copies the generated key to the clipboard.
- Interactive “press any key to continue” functionality.
- Colorful progress bar for a nicer UI.
- Works on Windows, Linux, and macOS terminals.

---

## Requirements

The script requires Python 3.6+ and the following Python packages:

- [colorama](https://pypi.org/project/colorama/) – for terminal colors.
- [pyperclip](https://pypi.org/project/pyperclip/) – for clipboard support.

---

## Installation

1. Clone or download this repository to your computer.

2. Install the required packages using `pip`:

```bash
pip install -r requirements.txt
