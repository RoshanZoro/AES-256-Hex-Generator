
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import ctypes
import gc
import logging
import os
import secrets
import signal
import shutil
import sys
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

import pyperclip  # type: ignore
import tkinter as tk
from tkinter import messagebox, ttk

_BG = "#000000"
_RED = "#ff0000"
_RED_DARK = "#990000"
_BTN_TEXT = "#000000"


def _attempt_mlock(buf: bytearray) -> bool:
    try:
        length = len(buf)
        if length == 0:
            return False
        if os.name == "posix":
            libc = ctypes.CDLL("libc.so.6", use_errno=True)
            addr = ctypes.addressof(ctypes.c_char.from_buffer(buf))
            res = libc.mlock(ctypes.c_void_p(addr), ctypes.c_size_t(length))
            return res == 0
        if os.name == "nt":
            kernel32 = ctypes.windll.kernel32
            addr = ctypes.addressof(ctypes.c_char.from_buffer(buf))
            res = kernel32.VirtualLock(ctypes.c_void_p(addr), ctypes.c_size_t(length))
            return res != 0
    except Exception:
        return False


def _attempt_munlock(buf: bytearray) -> bool:
    try:
        length = len(buf)
        if length == 0:
            return False
        if os.name == "posix":
            libc = ctypes.CDLL("libc.so.6", use_errno=True)
            addr = ctypes.addressof(ctypes.c_char.from_buffer(buf))
            res = libc.munlock(ctypes.c_void_p(addr), ctypes.c_size_t(length))
            return res == 0
        if os.name == "nt":
            kernel32 = ctypes.windll.kernel32
            addr = ctypes.addressof(ctypes.c_char.from_buffer(buf))
            res = kernel32.VirtualUnlock(ctypes.c_void_p(addr), ctypes.c_size_t(length))
            return res != 0
    except Exception:
        return False


def _memset_s_available() -> Optional[ctypes.CDLL]:
    candidates = []
    if os.name == "posix":
        candidates = ["libc.so.6", "libc.dylib", "libSystem.B.dylib"]
    for lib in candidates:
        try:
            libc = ctypes.CDLL(lib)
            return libc
        except Exception:
            continue
    return None


def secure_wipe_strong(buf: bytearray, passes: int = 3) -> None:
    if not isinstance(buf, bytearray):
        raise TypeError("secure_wipe_strong expects a bytearray")
    length = len(buf)
    if length == 0:
        return
    locked = _attempt_mlock(buf)
    try:
        try:
            if os.name == "nt":
                ntdll = ctypes.WinDLL("ntdll")
                if hasattr(ntdll, "RtlSecureZeroMemory"):
                    func = ntdll.RtlSecureZeroMemory
                    func.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
                    func.restype = ctypes.c_void_p
                    addr = ctypes.addressof(ctypes.c_char.from_buffer(buf))
                    func(ctypes.c_void_p(addr), ctypes.c_size_t(length))
                    return
        except Exception:
            pass
        libc = _memset_s_available()
        if libc is not None:
            try:
                if hasattr(libc, "explicit_bzero"):
                    explicit_bzero = libc.explicit_bzero
                    explicit_bzero.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
                    explicit_bzero.restype = None
                    addr = ctypes.addressof(ctypes.c_char.from_buffer(buf))
                    explicit_bzero(ctypes.c_void_p(addr), ctypes.c_size_t(length))
                    return
                if hasattr(libc, "memset_s"):
                    memset_s = libc.memset_s
                    memset_s.argtypes = [
                        ctypes.c_void_p,
                        ctypes.c_size_t,
                        ctypes.c_int,
                        ctypes.c_size_t,
                    ]
                    memset_s.restype = ctypes.c_int
                    addr = ctypes.addressof(ctypes.c_char.from_buffer(buf))
                    res = memset_s(
                        ctypes.c_void_p(addr),
                        ctypes.c_size_t(length),
                        ctypes.c_int(0),
                        ctypes.c_size_t(length),
                    )
                    if res == 0:
                        return
            except Exception:
                pass
        patterns = [0xFF, 0x00, 0xA5]
        for p in range(passes):
            pat = patterns[p % len(patterns)]
            for i in range(length):
                buf[i] = pat
            time.sleep(0.001)
        mv = memoryview(buf)
        mv[:] = secrets.token_bytes(length)
        mv[:] = b"\x00" * length
        del mv
    finally:
        if locked:
            _attempt_munlock(buf)
        gc.collect()


def generate_ephemeral_aes256_key() -> bytearray:
    key_bytes = secrets.token_bytes(32)
    key_buf = bytearray(key_bytes)
    del key_bytes
    gc.collect()
    _attempt_mlock(key_buf)
    return key_buf


@dataclass
class ClipboardTask:
    content: str
    delay: int
    blocking: bool = False
    notify: bool = True


def _clear_clipboard_os_specific() -> None:
    try:
        overwrite = secrets.token_hex(16)
        try:
            pyperclip.copy(overwrite)  # type: ignore
        except Exception:
            pass
        time.sleep(0.05)
        try:
            pyperclip.copy("")  # type: ignore
        except Exception:
            pass
    except Exception:
        pass
    try:
        if sys.platform.startswith("win"):
            user32 = ctypes.windll.user32
            if user32.OpenClipboard(None):
                user32.EmptyClipboard()
                user32.CloseClipboard()
        elif sys.platform.startswith("darwin"):
            with os.popen("pbcopy", "w") as p:
                p.write("")
        else:
            if shutil.which("xclip"):
                os.system("printf '' | xclip -selection clipboard")
                os.system("printf '' | xclip -selection primary")
            elif shutil.which("xsel"):
                os.system("printf '' | xsel --clipboard --input")
                os.system("printf '' | xsel --primary --input")
    except Exception:
        pass


def copy_to_clipboard_with_self_destruct(
    task: ClipboardTask,
    on_cleared: Optional[Callable[[], None]] = None,
    tk_root: Optional[tk.Tk] = None,
) -> threading.Thread:
    def worker() -> None:
        try:
            pyperclip.copy(task.content)  # type: ignore
        except Exception:
            return
        remaining = task.delay
        while remaining > 0:
            time.sleep(0.5)
            remaining -= 0.5
        _clear_clipboard_os_specific()
        if on_cleared:
            try:
                if tk_root is not None:
                    try:
                        tk_root.after(0, on_cleared)
                    except Exception:
                        try:
                            on_cleared()
                        except Exception:
                            pass
                else:
                    try:
                        on_cleared()
                    except Exception:
                        pass
            except Exception:
                pass
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return thread


def copy_to_clipboard_blocking(task: ClipboardTask, tk_root: Optional[tk.Tk] = None) -> None:
    try:
        pyperclip.copy(task.content)  # type: ignore
    except Exception:
        return
    root = tk.Tk()
    root.withdraw()
    try:
        remaining = task.delay
        win = tk.Toplevel()
        win.title("Clipboard Self-Destruct")
        win.configure(bg=_BG)
        win.transient(root)
        win.grab_set()
        lbl = tk.Label(win, text="Clipboard will be cleared in:", bg=_BG, fg=_RED, font=("Helvetica", 12, "bold"))
        lbl.pack(padx=12, pady=(12, 6))
        counter = tk.Label(win, text=f"{remaining}s", bg=_BG, fg=_RED, font=("Helvetica", 18, "bold"))
        counter.pack(padx=12, pady=(0, 12))
        def tick() -> None:
            nonlocal remaining
            remaining -= 1
            if remaining <= 0:
                try:
                    win.grab_release()
                except Exception:
                    pass
                win.destroy()
                _clear_clipboard_os_specific()
                if tk_root is not None:
                    try:
                        tk_root.after(0, lambda: None)
                    except Exception:
                        pass
                root.destroy()
                return
            counter.config(text=f"{remaining}s")
            win.after(1000, tick)
        win.after(1000, tick)
        root.mainloop()
    finally:
        try:
            root.destroy()
        except Exception:
            pass


def _make_button(
    parent: tk.Widget,
    text: str,
    command: Callable[[], None],
    *,
    bg: str = _RED,
    fg: str = _BTN_TEXT,
    activebg: str = _RED_DARK,
    activefg: str = _BTN_TEXT,
    **kwargs,
) -> tk.Button:
    btn = tk.Button(
        parent,
        text=text,
        command=command,
        bg=bg,
        fg=fg,
        activebackground=activebg,
        activeforeground=activefg,
        relief="flat",
        bd=0,
        highlightthickness=0,
        **kwargs,
    )
    try:
        btn.configure(takefocus=False)
    except Exception:
        pass
    return btn


class NumericSpinner(tk.Frame):
    def __init__(self, parent: tk.Widget, value: int = 1, minval: int = 1, maxval: int = 100, width: int = 6, **kwargs) -> None:
        super().__init__(parent, bg=_BG)
        self._min = int(minval)
        self._max = int(maxval)
        self._var = tk.IntVar(value=int(value))
        self._entry = tk.Entry(self, textvariable=self._var, width=width, justify="center",
                               bg=_BG, fg=_RED, insertbackground=_RED, bd=0, highlightthickness=0)
        self._entry.pack(side="left", fill="y")
        btn_frame = tk.Frame(self, bg=_BG)
        btn_frame.pack(side="left", fill="y", padx=(4, 0))
        up_btn = tk.Button(btn_frame, text="▲", command=self._inc, bg=_RED, fg=_BTN_TEXT,
                           activebackground=_RED_DARK, activeforeground=_BTN_TEXT, relief="flat", bd=0, highlightthickness=0)
        down_btn = tk.Button(btn_frame, text="▼", command=self._dec, bg=_RED, fg=_BTN_TEXT,
                             activebackground=_RED_DARK, activeforeground=_BTN_TEXT, relief="flat", bd=0, highlightthickness=0)
        up_btn.pack(side="top", fill="x")
        down_btn.pack(side="top", fill="x")
        try:
            up_btn.configure(takefocus=False)
            down_btn.configure(takefocus=False)
            self._entry.configure(takefocus=True)
        except Exception:
            pass

    def _inc(self) -> None:
        try:
            v = int(self._var.get())
        except Exception:
            v = self._min
        v = min(self._max, v + 1)
        self._var.set(v)

    def _dec(self) -> None:
        try:
            v = int(self._var.get())
        except Exception:
            v = self._min
        v = max(self._min, v - 1)
        self._var.set(v)

    def get(self) -> int:
        try:
            return int(self._var.get())
        except Exception:
            return self._min

    def set(self, value: int) -> None:
        self._var.set(max(self._min, min(self._max, int(value))))


class SecureAESGui(tk.Tk):
    def __init__(self, count: int = 8, clipboard_delay: int = 30) -> None:
        super().__init__()
        self.title("AES-256 Hex Generator — SECURE")
        self.configure(bg=_BG)
        self._fg = _RED
        self._accent = _RED
        self._count = max(1, int(count))
        self._clipboard_delay = max(1, int(clipboard_delay))
        self._generated_keys: list[bytearray] = []
        self._clipboard_threads: list[threading.Thread] = []
        self._key_rows: list[dict] = []
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        if sys.gettrace() is not None:
            try:
                messagebox.showwarning("Debugger detected", "Debugger attached. Exit for maximum security.")
            except Exception:
                pass
        self._register_signal_handlers()

    def _build_ui(self) -> None:
        banner = tk.Label(self, text="AES-256 Hex Generator", bg=_BG, fg=self._fg, font=("Helvetica", 16, "bold"), pady=12)
        banner.pack(fill="x", padx=12, pady=(12, 6))
        frm = tk.Frame(self, bg=_BG)
        frm.pack(fill="x", padx=12, pady=6)
        tk.Label(frm, text="Count:", bg=_BG, fg=self._fg).grid(row=0, column=0, sticky="w")
        self.count_spinner = NumericSpinner(frm, value=self._count, minval=1, maxval=100, width=6)
        self.count_spinner.grid(row=0, column=1, sticky="w", padx=(6, 0))
        tk.Label(frm, text="Clipboard delay (s):", bg=_BG, fg=self._fg).grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.delay_spinner = NumericSpinner(frm, value=self._clipboard_delay, minval=1, maxval=3600, width=6)
        self.delay_spinner.grid(row=1, column=1, sticky="w", padx=(6, 0), pady=(6, 0))
        gen_btn = _make_button(frm, "Generate", self._on_generate, bg=_RED, fg=_BTN_TEXT, activebg=_RED_DARK)
        gen_btn.grid(row=2, column=0, columnspan=2, pady=(12, 0))
        self.keys_frame = tk.Frame(self, bg=_BG)
        self.keys_frame.pack(fill="both", expand=True, padx=12, pady=12)
        footer = tk.Frame(self, bg=_BG)
        footer.pack(fill="x", padx=12, pady=(0, 12))
        quit_btn = _make_button(footer, "Quit", self._on_close, bg="#660000", fg="#ffdddd", activebg="#440000")
        quit_btn.pack(side="right")

    def _on_generate(self) -> None:
        self._wipe_all_generated_keys()
        count = max(1, self.count_spinner.get())
        delay = max(1, self.delay_spinner.get())
        progress = ProgressDialog(self, total=count, title="Generating keys")
        progress.show()
        def worker() -> None:
            try:
                for i in range(count):
                    key = generate_ephemeral_aes256_key()
                    self._generated_keys.append(key)
                    self.after(0, lambda k=key, idx=i: self._add_key_row(k, idx, delay))
                    progress.increment()
                    time.sleep(0.05)
            except Exception:
                pass
            finally:
                self.after(0, progress.close)
        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def _add_key_row(self, key: bytearray, index: int, delay: int) -> None:
        row = tk.Frame(self.keys_frame, bg=_BG)
        row.pack(fill="x", pady=6)
        masked = "•" * 8
        lbl = tk.Label(row, text=f"Key {index + 1}: {masked}", bg=_BG, fg=self._fg)
        lbl.pack(side="left", padx=(0, 8))
        def on_show() -> None:
            hex_key = key.hex()
            ShowKeyDialog(self, hex_key).show()
        def on_copy() -> None:
            hex_str = key.hex()
            def on_cleared_callback() -> None:
                try:
                    secure_wipe_strong(key)
                except Exception:
                    pass
                try:
                    if key in self._generated_keys:
                        self._generated_keys.remove(key)
                except Exception:
                    pass
                try:
                    lbl.config(text=f"Key {index + 1}: [wiped]")
                except Exception:
                    pass
                gc.collect()
            try:
                thr = copy_to_clipboard_with_self_destruct(ClipboardTask(content=hex_str, delay=delay), on_cleared=on_cleared_callback, tk_root=self)
                self._clipboard_threads.append(thr)
            finally:
                try:
                    hex_str = ""
                except Exception:
                    pass
                gc.collect()
            try:
                lbl.config(text=f"Key {index + 1}: [copied]")
            except Exception:
                pass
        def on_wipe() -> None:
            try:
                secure_wipe_strong(key)
            except Exception:
                pass
            try:
                if key in self._generated_keys:
                    self._generated_keys.remove(key)
            except Exception:
                pass
            lbl.config(text=f"Key {index + 1}: [wiped]")
            gc.collect()
        show_btn = _make_button(row, "Show", on_show, bg="#330000", fg="#ffdddd", activebg="#220000")
        show_btn.pack(side="left", padx=(0, 6))
        copy_btn = _make_button(row, "Copy", on_copy, bg="#660000", fg="#ffdddd", activebg="#440000")
        copy_btn.pack(side="left", padx=(0, 6))
        wipe_btn = _make_button(row, "Wipe", on_wipe, bg="#990000", fg="#ffffff", activebg="#660000")
        wipe_btn.pack(side="left", padx=(0, 6))
        self._key_rows.append({"key": key, "label": lbl, "row": row})

    def _notify(self, message: str) -> None:
        win = tk.Toplevel(self)
        win.overrideredirect(True)
        win.configure(bg=_BG)
        x = self.winfo_rootx() + 20
        y = self.winfo_rooty() + 20
        win.geometry(f"+{x}+{y}")
        lbl = tk.Label(win, text=message, bg=_BG, fg=self._fg, padx=10, pady=6)
        lbl.pack()
        self.after(2000, win.destroy)

    def _wipe_all_generated_keys(self) -> None:
        for k in list(self._generated_keys):
            try:
                secure_wipe_strong(k)
            except Exception:
                pass
        self._generated_keys.clear()
        gc.collect()
        for child in self.keys_frame.winfo_children():
            child.destroy()
        self._key_rows.clear()

    def _register_signal_handlers(self) -> None:
        def handler(signum, frame) -> None:
            try:
                self._wipe_all_generated_keys()
                _clear_clipboard_os_specific()
            finally:
                os._exit(0)
        try:
            signal.signal(signal.SIGINT, handler)
            signal.signal(signal.SIGTERM, handler)
        except Exception:
            pass

    def _on_close(self) -> None:
        try:
            self._wipe_all_generated_keys()
            _clear_clipboard_os_specific()
        except Exception:
            pass
        self.destroy()


class ProgressDialog:
    def __init__(self, parent: tk.Tk, total: int = 1, title: str = "Progress") -> None:
        self.parent = parent
        self.total = max(1, int(total))
        self.count = 0
        self.win = tk.Toplevel(parent)
        self.win.title(title)
        self.win.configure(bg=_BG)
        self.win.transient(parent)
        self.win.grab_set()
        self.win.geometry("420x110")
        self.lbl = tk.Label(self.win, text="Working...", bg=_BG, fg=_RED)
        self.lbl.pack(pady=(12, 6))
        self.pb = ttk.Progressbar(self.win, maximum=self.total, mode="determinate", length=360)
        self.pb.pack(pady=(6, 12))
        style = ttk.Style(self.win)
        try:
            style.theme_use("clam")
            style.configure("TProgressbar", troughcolor="#111111", background=_RED)
        except Exception:
            pass

    def show(self) -> None:
        self.win.deiconify()
        self.parent.update_idletasks()

    def increment(self) -> None:
        self.count += 1
        self.pb["value"] = self.count
        self.parent.update_idletasks()

    def close(self) -> None:
        try:
            self.win.grab_release()
        except Exception:
            pass
        self.win.destroy()


class ShowKeyDialog:
    def __init__(self, parent: tk.Tk, hex_key: str, timeout: int = 8) -> None:
        self.parent = parent
        self.hex_key = hex_key
        self.timeout = max(1, int(timeout))
        self.win = tk.Toplevel(parent)
        self.win.title("Ephemeral Key")
        self.win.configure(bg=_BG)
        self.win.transient(parent)
        self.win.grab_set()
        self.win.geometry("640x140")
        lbl = tk.Label(self.win, text="Ephemeral Key (will auto-hide)", bg=_BG, fg=_RED)
        lbl.pack(pady=(8, 4))
        font_spec = ("Helvetica", 12, "bold")
        try:
            txt = tk.Text(self.win, height=2, width=80, bg=_BG, fg=_RED, font=font_spec, bd=0, highlightthickness=0)
        except Exception:
            txt = tk.Text(self.win, height=2, width=80, bg=_BG, fg=_RED, font=("Arial", 12, "bold"), bd=0, highlightthickness=0)
        txt.insert("1.0", self.hex_key)
        txt.configure(state="disabled")
        txt.pack(padx=12, pady=(0, 8))
        self._countdown_label = tk.Label(self.win, text=f"Closing in {self.timeout}s", bg=_BG, fg=_RED)
        self._countdown_label.pack()
        self._remaining = self.timeout
        self._tick()

    def _tick(self) -> None:
        self._remaining -= 1
        if self._remaining <= 0:
            try:
                self.win.grab_release()
            except Exception:
                pass
            self.win.destroy()
            self.hex_key = ""
            gc.collect()
            return
        self._countdown_label.config(text=f"Closing in {self._remaining}s")
        self.win.after(1000, self._tick)

    def show(self) -> None:
        self.win.deiconify()
        self.parent.update_idletasks()


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AES-256 Hex Generator (GUI, secure, monochrome red)")
    parser.add_argument("--count", type=int, default=8, help="Number of keys to generate")
    parser.add_argument("--clipboard-delay", type=int, default=30, help="Clipboard self-destruct delay in seconds")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging (hidden by default)")
    return parser.parse_args(argv)


def _final_cleanup(generated_keys: Optional[list[bytearray]] = None) -> None:
    try:
        if generated_keys:
            for k in generated_keys:
                try:
                    secure_wipe_strong(k)
                except Exception:
                    pass
            generated_keys.clear()
    except Exception:
        pass
    try:
        _clear_clipboard_os_specific()
    except Exception:
        pass
    gc.collect()


def main(argv: Optional[list[str]] = None) -> None:
    args = parse_args(argv)
    if args.debug:
        logger = logging.getLogger("secure_aes_gui_mono_red")
        logger.setLevel(logging.DEBUG)
        if not logger.handlers:
            handler = logging.StreamHandler()
            logger.addHandler(handler)
    if sys.gettrace() is not None and not args.debug:
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showwarning("Debugger detected", "Debugger attached. Exit for maximum security.")
            root.destroy()
        except Exception:
            pass
    app = SecureAESGui(count=args.count, clipboard_delay=args.clipboard_delay)
    def _signal_handler(signum, _frame):
        try:
            _final_cleanup(app._generated_keys)
        finally:
            os._exit(0)
    try:
        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)
    except Exception:
        pass
    try:
        app.mainloop()
    finally:
        _final_cleanup(app._generated_keys)


if __name__ == "__main__":
    main()
