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
import subprocess
import ctypes
import gc

# ---------------------------
# Secure primitives
# ---------------------------

def secure_clipboard_clear():
    if os.name == "nt":
        secure_clipboard_clear_windows()
    elif sys.platform == "darwin":
        secure_clipboard_clear_macos()
    else:
        secure_clipboard_clear_linux()

def secure_clipboard_clear_windows():
    try:
        import win32clipboard  # pywin32
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText("[CLEARED]")
            win32clipboard.EmptyClipboard()
        finally:
            win32clipboard.CloseClipboard()
    except ImportError:
        try:
            pyperclip.copy("")
        except pyperclip.PyperclipException:
            print("Clipboard clear failed (pyperclip).")

def secure_clipboard_clear_macos():
    try:
        subprocess.run(["/usr/bin/pbcopy"], input=b"", check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        try:
            pyperclip.copy("")
        except pyperclip.PyperclipException:
            print("Clipboard clear failed (pyperclip).")

def secure_clipboard_clear_linux():
    cleared = False
    try:
        subprocess.run(["xclip", "-selection", "clipboard"], input=b"", check=True)
        subprocess.run(["xclip", "-selection", "primary"], input=b"", check=True)
        cleared = True
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    if not cleared:
        try:
            subprocess.run(["xsel", "--clipboard", "--clear"], check=True)
            subprocess.run(["xsel", "--primary", "--clear"], check=True)
            cleared = True
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass

    if not cleared:
        try:
            pyperclip.copy("")
        except pyperclip.PyperclipException:
            print("Clipboard clear failed (pyperclip).")

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
        for i in range(len(b)):
            b[i] = 0

def secure_wipe_strong(b: bytearray):
    """
    Strong zeroization using OS-native functions where available.
    - On Windows: RtlSecureZeroMemory from ntdll.dll
    - On Linux/macOS: explicit_bzero (libc), fallback to two-pass overwrite
    """
    if not isinstance(b, bytearray):
        return
    size = len(b)
    if size == 0:
        return

    try:
        addr = ctypes.addressof(ctypes.c_char.from_buffer(b))
    except (TypeError, ValueError):
        for i in range(len(b)):
            b[i] = 0
        return

    if os.name == "nt":
        try:
            rtl_secure_zero_memory = ctypes.WinDLL("ntdll").RtlSecureZeroMemory
            rtl_secure_zero_memory.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
            rtl_secure_zero_memory.restype = ctypes.c_void_p
            rtl_secure_zero_memory(addr, size)
            return
        except (AttributeError, OSError):
            for i in range(len(b)):
                b[i] = 0
            return

    # Try libc explicit_bzero or memset_s inline
    for lib_name in ("libc.so.6", "libc.dylib", "libSystem.B.dylib"):
        try:
            libc = ctypes.CDLL(lib_name)
            try:
                explicit_bzero = libc.explicit_bzero
                explicit_bzero.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
                explicit_bzero.restype = None
                explicit_bzero(addr, size)
                return
            except AttributeError:
                pass
            try:
                memset_s = libc.memset_s
                memset_s.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int, ctypes.c_size_t]
                memset_s.restype = ctypes.c_int
                res = memset_s(addr, size, 0, size)
                if res == 0:
                    return
            except AttributeError:
                pass
        except OSError:
            continue

    # Fallback: random pass + zero pass
    mv = memoryview(b)
    mv[:] = secrets.token_bytes(size)
    mv[:] = b"\x00" * size
    del mv

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
        secure_wipe_strong(ephemeral_key)
    globals()['ephemeral_key'] = None
    globals()['ephemeral_hex'] = None
    try:
        secure_clipboard_clear()
    except pyperclip.PyperclipException:
        pass
    try:
        colorama.deinit()
    except RuntimeError:
        pass

def _signal_handler(signum, _frame):
    print(f"\nSignal {signum} received, performing secure cleanup...")
    _final_cleanup()
    sys.exit(1)

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
            try:
                pyperclip.copy(ephemeral_hex)
            except pyperclip.PyperclipException:
                print("Clipboard unavailable (best-effort).")
            clipboard_self_destruct(delay=args.clipboard_delay)

            # Wipe ephemeral memory immediately after use (strong wipe)
            secure_wipe_strong(ephemeral_key)
            ephemeral_key = None
            ephemeral_hex = None

            # Aggressive collection
            gc.collect()

            # Handle clipboard self-destruct flow
            if args.count > 1:
                wait_for_keypress()
                print('\033[3J\033c')
            else:
                clipboard_self_destruct_blocking(delay=args.clipboard_delay)

    except KeyboardInterrupt:
        print("\nGoodbye!")
        _final_cleanup()
        sys.exit(0)
    except (OSError, ValueError) as e:
        print(f"\nError occurred: {e}\nPerforming secure cleanup...")
        _final_cleanup()
        sys.exit(1)
    finally:
        _final_cleanup()