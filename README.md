
# AES-256 Hex Generator for DMR Radios – Overkill Security Edition

![AES-256](https://img.shields.io/badge/Encryption-AES--256-brightgreen)

A **secure, ephemeral AES-256 key generator** for DMR radio users who want maximum privacy. This tool generates one or multiple AES-256 keys, displays them in a colorful terminal interface, copies them to your clipboard, and automatically wipes sensitive data.

> ⚠️ **Security-first**: Keys exist only briefly in memory and clipboard to minimize the risk of leaks.

---

## Features

- **AES-256 key generation** – Cryptographically secure 256-bit keys.  
- **Multiple keys** – Generate multiple keys in one run (`--count`).  
- **Clipboard self-destruct** – Keys copied to clipboard are cleared automatically (`--clipboard-delay`).  
- **Ephemeral memory handling** – Keys exist temporarily in memory and are securely wiped.  
- **Progress bar** – Fun visual indicator while generating keys.  
- **Cross-platform** – Works on Windows, Linux, and macOS terminals.  
- **Debugger detection** – Exits immediately if run under a debugger for extra security.  
- **Terminal-friendly output** – Colorful key display without leaving permanent traces.  

---

## Installation

1. Clone this repository:  

```bash
git clone https://github.com/RoshanZoro/AES-256-Hex-Generator.git
cd AES-256-Hex-Generator
````

2. Install dependencies (Python 3.8+ required):

```bash
pip install -r requirements.txt
```

> **Dependencies:** `colorama`, `pyperclip`

---

## Usage

Generate **one key** (default clipboard self-destruct: 30s):

```bash
python aes256_generator.py
```

Generate **multiple keys** (e.g., 5 keys) with a custom clipboard delay:

```bash
python aes256_generator.py --count 5 --clipboard-delay 60
```

* `--count` – Number of keys to generate (default: 8).
* `--clipboard-delay` – Seconds before clipboard is cleared (default: 30).

---

## Security Notes

* Keys are stored in memory **only temporarily** and wiped immediately after use.
* Clipboard data is automatically erased after the specified delay.
* Debugger detection prevents key generation in insecure environments.
* For maximum security, avoid screenshots or logging your terminal output.

---

## Example

*Example key output:*

```
[ 1a2b3c4d5e6f7g8h9i0j... ]
```

*Color-coded terminal display and progress bar shown during generation.*

---
