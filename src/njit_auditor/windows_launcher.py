"""Stock Unicode Win32 launcher, imported only for an interactive Windows launch.

Like the qualified prototype, controls use the system accessibility providers and
messages pass through IsDialogMessage. A real modeless dialog supplies Windows'
default-button and focus bookkeeping (including Enter on the focused Quit button).
No GUI framework or optional Python package is required.
"""

from __future__ import annotations

import ctypes as c
import struct
import webbrowser
from ctypes import wintypes as w

from njit_auditor.desktop_metadata import DESKTOP_VERSION, desktop_build_info
from njit_auditor.resource_paths import resource_path

TITLE = "NJIT Thesis Auditor"
STARTING = "Starting the local auditor…"
READY = "Ready to open in your browser."
OPENED = "Auditor ready in your browser."
BROWSER_ERROR = "Could not open your browser. Check your default browser and try again."
STOPPING = "Stopping the local auditor…"
STOP_ERROR = "Could not stop the audit yet. Try Quit again."
OPEN_ID, QUIT_ID = 101, 102
WM_COMMAND, WM_CLOSE, WM_TIMER, WM_DPICHANGED = 0x111, 0x10, 0x113, 0x2E0


class WindowsLauncher:
    """Own the dialog on the calling thread; retain the existing shutdown controller."""

    def __init__(self, server, thread, open_auditor, request_quit):
        self.server, self.thread = server, thread
        self.open_auditor, self.request_quit = open_auditor, request_quit
        self.user = c.WinDLL("user32", use_last_error=True)
        self.gdi = c.WinDLL("gdi32", use_last_error=True)
        self.kernel = c.WinDLL("kernel32", use_last_error=True)
        self.hwnd = None
        self.font = None
        self.icon = None
        self.controls = {}
        self.status = STARTING
        self.was_ready = False
        self.stopping = False
        self.callback_error = None
        self._bind()
        # Thread-local awareness works with existing packaging manifests and does
        # not change desktop settings. Restore it when this window is retired.
        self.old_context = self.user.SetThreadDpiAwarenessContext(c.c_void_p(-4))
        self._proc = self.dialog_proc_type(self._dispatch)
        # Empty, DWORD-aligned DLGTEMPLATE; child controls are created below.
        template = struct.pack("<IIHhhhhHHH", 0x10CA0000, 0x10000, 0, 0, 0, 480, 224, 0, 0, 0)
        self._template = c.create_string_buffer(template)
        try:
            self.hwnd = self.user.CreateDialogIndirectParamW(
                self.kernel.GetModuleHandleW(None), self._template, None, self._proc, 0
            )
            if not self.hwnd:
                raise c.WinError(c.get_last_error())
            self.user.SetWindowTextW(self.hwnd, TITLE)
            for name, kind, text, identifier in (
                ("title", "STATIC", TITLE, 0),
                ("description", "STATIC", "Check thesis formatting in your browser.", 0),
                ("status", "STATIC", STARTING, 0),
                ("open", "BUTTON", "&Open auditor", OPEN_ID),
                ("quit", "BUTTON", "&Quit", QUIT_ID),
                (
                    "version",
                    "STATIC",
                    "Version "
                    + str(desktop_build_info().get("build_version", DESKTOP_VERSION))
                    + " · Runs on this computer",
                    0,
                ),
            ):
                # BS_NOTIFY reports focus changes from UIA/SetFocus as well as
                # dialog navigation, so Enter follows the focused button.
                style = 0x50000000 | (0x14000 if kind == "BUTTON" else 0)
                if name == "quit":
                    style |= 1  # BS_DEFPUSHBUTTON while Open is disabled
                child = self.user.CreateWindowExW(
                    0,
                    kind,
                    text,
                    style,
                    0,
                    0,
                    1,
                    1,
                    self.hwnd,
                    identifier,
                    self.kernel.GetModuleHandleW(None),
                    None,
                )
                if not child:
                    raise c.WinError(c.get_last_error())
                self.controls[name] = child
            self.user.EnableWindow(self.controls["open"], False)
            self.user.SendMessageW(self.hwnd, 0x401, QUIT_ID, 0)  # DM_SETDEFID
            self.icon = self.user.LoadImageW(
                None,
                str(resource_path("assets", "icons", "njit-auditor.ico")),
                1,
                0,
                0,
                0x10 | 0x40,  # IMAGE_ICON, LR_LOADFROMFILE | LR_DEFAULTSIZE
            )
            if self.icon:
                self.user.SendMessageW(self.hwnd, 0x80, 1, self.icon)
                self.user.SendMessageW(self.hwnd, 0x80, 0, self.icon)
            self.layout(self.user.GetDpiForWindow(self.hwnd) or 96)
            self.user.SetTimer(self.hwnd, 1, 100, None)
            self.user.ShowWindow(self.hwnd, 5)
            self.user.SetFocus(self.controls["quit"])
            self.user.UpdateWindow(self.hwnd)
        except BaseException:
            self.destroy()
            raise

    def _bind(self):
        self.dialog_proc_type = c.WINFUNCTYPE(c.c_ssize_t, w.HWND, w.UINT, w.WPARAM, w.LPARAM)
        # Explicit pointer-sized signatures are essential on 64-bit Windows.
        declarations = {
            "CreateDialogIndirectParamW": (
                w.HWND,
                [w.HINSTANCE, c.c_void_p, w.HWND, self.dialog_proc_type, w.LPARAM],
            ),
            "CreateWindowExW": (
                w.HWND,
                [
                    w.DWORD,
                    w.LPCWSTR,
                    w.LPCWSTR,
                    w.DWORD,
                    c.c_int,
                    c.c_int,
                    c.c_int,
                    c.c_int,
                    w.HWND,
                    w.HMENU,
                    w.HINSTANCE,
                    c.c_void_p,
                ],
            ),
            "SetThreadDpiAwarenessContext": (c.c_void_p, [c.c_void_p]),
            "GetDpiForWindow": (w.UINT, [w.HWND]),
            "SetWindowTextW": (w.BOOL, [w.HWND, w.LPCWSTR]),
            "SendMessageW": (c.c_ssize_t, [w.HWND, w.UINT, w.WPARAM, w.LPARAM]),
            "EnableWindow": (w.BOOL, [w.HWND, w.BOOL]),
            "SetFocus": (w.HWND, [w.HWND]),
            "ShowWindow": (w.BOOL, [w.HWND, c.c_int]),
            "UpdateWindow": (w.BOOL, [w.HWND]),
            "DestroyWindow": (w.BOOL, [w.HWND]),
            "SetTimer": (c.c_size_t, [w.HWND, c.c_size_t, w.UINT, c.c_void_p]),
            "KillTimer": (w.BOOL, [w.HWND, c.c_size_t]),
            "IsDialogMessageW": (w.BOOL, [w.HWND, c.POINTER(w.MSG)]),
            "GetMessageW": (c.c_int, [c.POINTER(w.MSG), w.HWND, w.UINT, w.UINT]),
            "PeekMessageW": (w.BOOL, [c.POINTER(w.MSG), w.HWND, w.UINT, w.UINT, w.UINT]),
            "TranslateMessage": (w.BOOL, [c.POINTER(w.MSG)]),
            "DispatchMessageW": (c.c_ssize_t, [c.POINTER(w.MSG)]),
            "MoveWindow": (w.BOOL, [w.HWND, c.c_int, c.c_int, c.c_int, c.c_int, w.BOOL]),
            "GetWindowRect": (w.BOOL, [w.HWND, c.POINTER(w.RECT)]),
            "AdjustWindowRectExForDpi": (
                w.BOOL,
                [c.POINTER(w.RECT), w.DWORD, w.BOOL, w.DWORD, w.UINT],
            ),
            "MonitorFromWindow": (w.HANDLE, [w.HWND, w.DWORD]),
            "GetMonitorInfoW": (w.BOOL, [w.HANDLE, c.c_void_p]),
            "LoadImageW": (w.HANDLE, [w.HINSTANCE, w.LPCWSTR, w.UINT, c.c_int, c.c_int, w.UINT]),
            "DestroyIcon": (w.BOOL, [w.HANDLE]),
            "MessageBoxW": (c.c_int, [w.HWND, w.LPCWSTR, w.LPCWSTR, w.UINT]),
        }
        for name, (result, args) in declarations.items():
            fn = getattr(self.user, name)
            fn.restype, fn.argtypes = result, args
        self.kernel.GetModuleHandleW.restype = w.HINSTANCE
        self.kernel.GetModuleHandleW.argtypes = [w.LPCWSTR]
        self.gdi.CreateFontW.restype = w.HANDLE
        self.gdi.CreateFontW.argtypes = [c.c_int] * 5 + [w.DWORD] * 8 + [w.LPCWSTR]
        self.gdi.DeleteObject.restype = w.BOOL
        self.gdi.DeleteObject.argtypes = [w.HANDLE]

    def layout(self, dpi, suggested=None):
        """Scale logical coordinates and font; never change system DPI/settings.

        Qualification may call this with simulated DPI; WM_DPICHANGED supplies
        the actual per-monitor DPI and suggested physical rectangle in production.
        """
        self.dpi = max(96, min(int(dpi), 768))
        def scale(value):
            return round(value * self.dpi / 96)
        font = self.gdi.CreateFontW(
            -round(10 * self.dpi / 72), 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 5, 0, "Segoe UI"
        )
        if not font:
            raise c.WinError(c.get_last_error())
        old_font, self.font = self.font, font
        positions = {
            "title": (16, 12, 448, 24),
            "description": (16, 40, 448, 24),
            "status": (16, 72, 448, 48),
            "open": (16, 128, 160, 34),
            "quit": (188, 128, 116, 34),
            "version": (16, 180, 448, 32),
        }
        for name, rect in positions.items():
            child = self.controls[name]
            self.user.SendMessageW(child, 0x30, font, 1)  # WM_SETFONT
            self.user.MoveWindow(child, *(scale(v) for v in rect), True)
        if old_font:
            self.gdi.DeleteObject(old_font)
        rect = w.RECT(0, 0, scale(480), scale(224))
        self.user.AdjustWindowRectExForDpi(c.byref(rect), 0x10CA0000, False, 0x10000, self.dpi)
        current = w.RECT()
        self.user.GetWindowRect(self.hwnd, c.byref(current))
        origin = suggested or current

        class MonitorInfo(c.Structure):
            _fields_ = [
                ("size", w.DWORD),
                ("monitor", w.RECT),
                ("work", w.RECT),
                ("flags", w.DWORD),
            ]

        info = MonitorInfo()
        info.size = c.sizeof(info)
        self.user.GetMonitorInfoW(self.user.MonitorFromWindow(self.hwnd, 2), c.byref(info))
        width, height = rect.right - rect.left, rect.bottom - rect.top
        x = max(info.work.left, min(origin.left, info.work.right - width))
        y = max(info.work.top, min(origin.top, info.work.bottom - height))
        self.user.MoveWindow(self.hwnd, x, y, width, height, True)

    def set_status(self, text):
        self.status = text
        self.user.SetWindowTextW(self.controls["status"], text)

    def open_browser(self):
        if not self.server.started or self.server.should_exit or self.stopping:
            return
        try:
            opened = self.open_auditor()
        except (OSError, webbrowser.Error):
            opened = False
        self.set_status(OPENED if opened else BROWSER_ERROR)

    def close(self):
        self.stopping = True
        self.user.EnableWindow(self.controls["open"], False)
        self.set_status(STOPPING)
        self.user.UpdateWindow(self.controls["status"])
        self.user.UpdateWindow(self.hwnd)
        if not self.request_quit():
            self.stopping = False
            self.set_status(STOP_ERROR)
            self.user.EnableWindow(self.controls["open"], self.server.started)

    def poll(self):
        if not self.thread.is_alive():
            self.destroy()
        elif self.server.should_exit:
            self.stopping = True
            self.user.EnableWindow(self.controls["open"], False)
            self.set_status(STOPPING)
        elif self.server.started and not self.was_ready and not self.stopping:
            self.was_ready = True
            self.user.EnableWindow(self.controls["open"], True)
            self.user.SendMessageW(self.hwnd, 0x401, OPEN_ID, 0)
            self.user.SetFocus(self.controls["open"])
            if self.status == STARTING:
                self.set_status(READY)

    def _dispatch(self, hwnd, message, wp, lp):
        try:
            if message == WM_COMMAND:
                identifier = wp & 0xFFFF
                notification = (wp >> 16) & 0xFFFF
                if notification == 6 and identifier in (OPEN_ID, QUIT_ID):  # BN_SETFOCUS
                    self.user.SendMessageW(hwnd, 0x401, identifier, 0)
                    return 1
                if notification != 0:  # Only BN_CLICKED activates callbacks.
                    return 0
                if identifier == OPEN_ID:
                    self.open_browser()
                    return 1
                if identifier in (QUIT_ID, 2):  # IDCANCEL / Escape uses the same controller
                    self.close()
                    return 1
            elif message == WM_CLOSE:
                self.close()
                return 1
            elif message == WM_TIMER:
                self.poll()
                return 1
            elif message == WM_DPICHANGED:
                self.layout(wp & 0xFFFF, c.cast(lp, c.POINTER(w.RECT)).contents)
                return 1
        except BaseException as exc:
            # Exceptions must never escape a ctypes callback (ctypes discards them).
            self.callback_error = exc
            if self.hwnd:
                self.user.DestroyWindow(self.hwnd)
                self.hwnd = None
        return 0

    def _message(self, msg):
        if not self.user.IsDialogMessageW(self.hwnd, c.byref(msg)):
            self.user.TranslateMessage(c.byref(msg))
            self.user.DispatchMessageW(c.byref(msg))

    def update(self):
        msg = w.MSG()
        while self.hwnd and self.user.PeekMessageW(c.byref(msg), self.hwnd, 0, 0, 1):
            self._message(msg)
        self._raise_callback_error()

    def mainloop(self):
        self.poll()
        msg = w.MSG()
        while self.hwnd:
            result = self.user.GetMessageW(c.byref(msg), None, 0, 0)
            if result == -1:
                raise c.WinError(c.get_last_error())
            if result == 0:
                break
            self._message(msg)
            self._raise_callback_error()

    def _raise_callback_error(self):
        if self.callback_error:
            raise self.callback_error

    def startup_error(self):
        self.user.MessageBoxW(self.hwnd, "The local auditor could not start.", TITLE, 0x10)

    def destroy(self):
        if self.hwnd:
            self.user.KillTimer(self.hwnd, 1)
            self.user.DestroyWindow(self.hwnd)
            self.hwnd = None
        if self.font:
            self.gdi.DeleteObject(self.font)
            self.font = None
        if self.icon:
            self.user.DestroyIcon(self.icon)
            self.icon = None
        if self.old_context:
            self.user.SetThreadDpiAwarenessContext(self.old_context)
            self.old_context = None
