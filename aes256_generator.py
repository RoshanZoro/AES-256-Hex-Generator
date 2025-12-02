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
import signal

# ---------------------------
# Secure primitives
# ---------------------------

def generate_ephemeral_aes256_key():
    """Generate AES-256 key in ephemeral memory and return as bytearray."""
    return bytearray(secrets.token_bytes(32))

def secure_wipe(b: bytearray):
    """Deterministically overwrite sensitive memory (random pass + zero pass)."""
    if not isinstance(b, bytearray):
        return
    try:
        mv = memoryview(b)
        mv[:] = secrets.token_bytes(len(mv))  # random pass
        mv[:] = b"\x00" * len(mv)             # zero pass
        step = max(1, len(b) // 8)
        for i in range(0, len(b), step):
            b[i] = 0
        del mv
    except (TypeError, BufferError):
        # fallback wipe
        for i in range(len(b)):
            b[i] = 0

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
        try:
            time.sleep(delay)
            pyperclip.copy("")
        except pyperclip.PyperclipException:
            pass
    threading.Thread(target=wipe, daemon=True).start()

def clipboard_self_destruct_blocking(delay=30):
    """Wipe clipboard after delay seconds, blocking until done."""
    print(f"Clipboard will self-destruct in {delay} seconds...")
    try:
        time.sleep(delay)
        pyperclip.copy("")
        print("Clipboard cleared.")
    except pyperclip.PyperclipException:
        print("Clipboard clear failed (best-effort).")

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

# ---------------------------
# Initialization
# ---------------------------

clear_console()
colorama.init()

# Detect debugger
if sys.gettrace() is not None:
    print("Debugger detected!")
    sys.exit(1)

# Disable core dumps (best-effort)
try:
    import resource
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
except (ImportError, ValueError):
    pass

# CLI argument parsing
parser = argparse.ArgumentParser(description="AES-256 Hex Generator for DMR radios")
parser.add_argument("--count", type=int, default=8, help="Number of keys to generate")
parser.add_argument("--clipboard-delay", type=int, default=30, help="Clipboard self-destruct delay in seconds")
args = parser.parse_args()

# ---------------------------
# Main with hardened cleanup
# ---------------------------

ephemeral_key = None
ephemeral_hex = None

def _final_cleanup():
    """Final safety net: wipe memory and clear clipboard."""
    if ephemeral_key is not None:
        secure_wipe(ephemeral_key)
    # Drop references
    globals()['ephemeral_key'] = None
    globals()['ephemeral_hex'] = None
    # Clipboard best-effort clear
    try:
        pyperclip.copy("")
    except pyperclip.PyperclipException:
        pass
    # De-init color
    try:
        colorama.deinit()
    except RuntimeError:
        pass

def _signal_handler(_signum, _frame):
    print("\nSignal received, performing secure cleanup...")
    _final_cleanup()
    sys.exit(1)

# Trap SIGINT/SIGTERM to guarantee cleanup
for _sig in (getattr(signal, "SIGINT", None), getattr(signal, "SIGTERM", None)):
    if _sig is not None:
        try:
            signal.signal(_sig, _signal_handler)
        except (ValueError, OSError):
            pass

if __name__ == "__main__":
    try:
        for _ in range(args.count):
            # Generate ephemeral key
            ephemeral_key = generate_ephemeral_aes256_key()

            # Display banner (styling preserved)
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
            try:
                pyperclip.copy(ephemeral_hex)
            except pyperclip.PyperclipException:
                print("Clipboard unavailable (best-effort).")
            clipboard_self_destruct(delay=args.clipboard_delay)

            # Wipe ephemeral memory immediately after use
            secure_wipe(ephemeral_key)
            ephemeral_key = None
            ephemeral_hex = None

            # Aggressive collection (best-effort)
            try:
                import gc;gc.collect()
            except ImportError:
                gc = None

            # Handle clipboard self-destruct flow
            if args.count > 1:
                wait_for_keypress()
                print('\033[3J\033c')  # styling preserved
            else:
                clipboard_self_destruct_blocking(delay=args.clipboard_delay)

    except KeyboardInterrupt:
        print("\nGoodbye!")
        _final_cleanup()
        sys.exit(0)
    except (OSError, ValueError) as e:
        # Fail closed: perform cleanup on any unexpected error
        print(f"\nError occurred: {e}\nPerforming secure cleanup...")
        _final_cleanup()
        sys.exit(1)
    finally:
        # Final safety net
        _final_cleanup()
