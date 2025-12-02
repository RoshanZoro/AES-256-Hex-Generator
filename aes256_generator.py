"""
AES-256 Hex Generator for DMR Radios – Overkill Security Edition
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
import argparse

def generate_ephemeral_aes256_key():
    """Generate AES-256 key in ephemeral memory and return as bytearray."""
    return bytearray(secrets.token_bytes(32))

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
        input("Press Enter to continue...\n")
    print()

def clipboard_self_destruct(delay=30):
    """Wipe clipboard after delay seconds."""
    def wipe():
        time.sleep(delay)
        pyperclip.copy("")
    threading.Thread(target=wipe, daemon=True).start()

def clipboard_self_destruct_blocking(delay=30):
    """Wipe clipboard after delay seconds, blocking until done."""
    print(f"Clipboard will self-destruct in {delay} seconds...")
    time.sleep(delay)
    pyperclip.copy("")
    print("Clipboard cleared.")

def wipe_bytearray(b: bytearray):
    """Overwrite sensitive memory."""
    for i in range(len(b)):
        b[i] = 0

def print_hex_from_bytes(b: bytearray):
    """Print the bytearray as hex directly without creating a permanent string."""
    hex_parts = (f"{byte:02x}" for byte in b)
    hex_str = ''.join(hex_parts)
    print(f"[ {Style.BRIGHT}{Fore.LIGHTGREEN_EX}{hex_str}{Style.RESET_ALL} ]")
    return hex_str  # for clipboard, only exists briefly

def progress_bar():
    for progress in range(101):
        bar = '█' * (progress // 2) + '-' * (50 - progress // 2)
        sys.stdout.write(f"{Style.BRIGHT}\r|{Fore.LIGHTMAGENTA_EX}{bar}{Fore.RESET}| {progress}%{Style.RESET_ALL}")
        sys.stdout.flush()
        time.sleep(random.uniform(0.0025, 0.01))
    print()

# Initialize
clear_console()
colorama.init()

# Detect debugger
if sys.gettrace() is not None:
    print("Debugger detected!")
    exit()

# CLI argument parsing
parser = argparse.ArgumentParser(description="AES-256 Hex Generator for DMR radios")
parser.add_argument("--count", type=int, default=8, help="Number of keys to generate")
parser.add_argument("--clipboard-delay", type=int, default=30, help="Clipboard self-destruct delay in seconds")
args = parser.parse_args()

if __name__ == "__main__":
    try:
        for _ in range(args.count):
            # Generate ephemeral key
            ephemeral_key = generate_ephemeral_aes256_key()

            # Display banner
            print(
                Fore.GREEN + "♦───────⟨ " +
                Style.BRIGHT + Fore.LIGHTGREEN_EX + "AES 256-bit Hex Generator " +
                Style.RESET_ALL + Fore.GREEN + "⟩───────♦" +
                Style.RESET_ALL
            )

            # Show progress bar
            progress_bar()

            # Print key and copy to clipboard
            ephemeral_hex = print_hex_from_bytes(ephemeral_key)
            pyperclip.copy(ephemeral_hex)
            clipboard_self_destruct(delay=args.clipboard_delay)

            # Wipe ephemeral memory
            wipe_bytearray(ephemeral_key)
            del ephemeral_key
            del ephemeral_hex
            import gc;gc.collect()

            # Handle clipboard self-destruct
            if args.count > 1:
                wait_for_keypress()
                print('\033[3J\033c')
            else:
                # For a single key, block until clipboard clears
                clipboard_self_destruct_blocking(delay=args.clipboard_delay)

    except KeyboardInterrupt:
        print("\nGoodbye!")
        colorama.deinit()
