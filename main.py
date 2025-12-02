"""
Hex Generator for AES 256 DMR radios
"""

import secrets
import sys
import time
import random
import colorama
from colorama import Fore, Style
import os
import pyperclip

def generate_aes256_key():
    key = secrets.token_bytes(32)
    return key.hex()
def clear_console():
    import os
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
clear_console()
colorama.init()

if __name__ == "__main__":
    try:
        while True:
            hexKey = generate_aes256_key()
            print(
                Fore.GREEN + "♦───────⟨ " +
                Style.BRIGHT + Fore.LIGHTGREEN_EX + "AES 256-bit Hex Generator " +
                Style.RESET_ALL + Fore.GREEN + "⟩───────♦" +
                Style.RESET_ALL
            )
            for i in range(101):
                bar = '█' * (i // 2) + '-' * (50 - i // 2)
                sys.stdout.write(f"{Style.BRIGHT}\r|{Fore.LIGHTMAGENTA_EX}{bar}{Fore.RESET}| {i}%{Style.RESET_ALL}")
                sys.stdout.flush()
                time.sleep(random.uniform(0.0025, 0.01))
            print(f"\n"
                  f""
                  f"[ {Style.BRIGHT}{Fore.LIGHTGREEN_EX}{hexKey}{Style.RESET_ALL} ]\n"
                  f"The key has been copied to your clipboard!")
            pyperclip.copy(hexKey)
            wait_for_keypress()
    except KeyboardInterrupt:
        print("\nGoodbye!")
        colorama.deinit()