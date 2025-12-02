# AES-256 Hex Generator for DMR Radios

This Python script generates cryptographically secure AES-256 keys suitable for use with DMR (Digital Mobile Radio) encryption. It now features **ephemeral memory handling**, **clipboard self-destruction**, and other overkill security measures.

---

## Features

- Generates **secure AES-256 keys** (32 bytes / 256 bits) in **hexadecimal format**.
- Stores keys in **ephemeral memory** (`bytearray`) and wipes them after use.
- Automatically copies generated keys to the clipboard with **30-second self-destruct**.
- Interactive **press-any-key** functionality.
- Colorful **progress bar** and terminal output.
- Clears terminal scrollback after each key generation.
- **Debugger detection**: exits if run under a debugger.
- Graceful exit on **Ctrl+C**.

---

## Requirements

The script requires Python 3.6+ and the following packages:

- [colorama](https://pypi.org/project/colorama/) – for terminal colors.
- [pyperclip](https://pypi.org/project/pyperclip/) – for clipboard support.

---

## Installation

1. Clone or download this repository.
2. Install the required packages using pip:

```bash
pip install -r requirements.txt
