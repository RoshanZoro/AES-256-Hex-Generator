"""
Hex Generator for AES 256 DMR radios
"""

import secrets
import sys
import threading
import time
import random
import colorama
from colorama import Fore, Style
import os
import pyperclip

def generate_ephemeral_aes256_key():
    """Generate AES-256 key in ephemeral memory and return it as a bytearray."""
    key_bytes = bytearray(secrets.token_bytes(32))
    return key_bytes

def clear_console():
    try:
        if os.name == 'nt':
            os.system('cls')
        else:
            if 'TERM' not in os.environ:
                os.environ['TERM'] = 'xterm'
            os.system('clear')
    except OSError:
        pass

def wait_for_keypress():
    try:
        # Windows
        if os.name == 'nt':
            import msvcrt
            print("Press any key to continue...\n", end='', flush=True)
            msvcrt.getch()
        else:
            import termios
            import tty

            print("Press any key to continue...\n", end='', flush=True)
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    except (EOFError, KeyboardInterrupt):
        input("Press Enter to continue...\n")  # fallback
    print()

def clipboard_self_destruct(delay=30):
    """Wipe clipboard after delay seconds."""
    def wipe():
        time.sleep(delay)
        pyperclip.copy("")
    threading.Thread(target=wipe, daemon=True).start()

def wipe_bytearray(b: bytearray):
    """Overwrite sensitive memory."""
    for i in range(len(b)):
        b[i] = 0

# Initialize
clear_console()
colorama.init()

# Detect debugger
if sys.gettrace() is not None:
    print("Debugger detected!")
    exit()

if __name__ == "__main__":
    try:
        while True:
            # Generate ephemeral key
            key_bytes = generate_ephemeral_aes256_key()
            key_hex = key_bytes.hex()  # Temporary string for display and clipboard

            # Display banner
            print(
                Fore.GREEN + "♦───────⟨ " +
                Style.BRIGHT + Fore.LIGHTGREEN_EX + "AES 256-bit Hex Generator " +
                Style.RESET_ALL + Fore.GREEN + "⟩───────♦" +
                Style.RESET_ALL
            )

            # Progress bar
            for i in range(101):
                bar = '█' * (i // 2) + '-' * (50 - i // 2)
                sys.stdout.write(f"{Style.BRIGHT}\r|{Fore.LIGHTMAGENTA_EX}{bar}{Fore.RESET}| {i}%{Style.RESET_ALL}")
                sys.stdout.flush()
                time.sleep(random.uniform(0.0025, 0.01))

            # Display key and copy to clipboard
            print(f"\n[ {Style.BRIGHT}{Fore.LIGHTGREEN_EX}{key_hex}{Style.RESET_ALL} ]\n"
                  f"The key has been copied to your clipboard!")
            pyperclip.copy(key_hex)

            # Start clipboard self-destruct
            clipboard_self_destruct(delay=30)

            # Wipe ephemeral memory
            wipe_bytearray(key_bytes)
            del key_bytes
            del key_hex
            import gc; gc.collect()

            # Wait for user
            wait_for_keypress()

            # Clear screen and scrollback
            print('\033[3J\033c')

    except KeyboardInterrupt:
        print("\nGoodbye!")
        colorama.deinit()
