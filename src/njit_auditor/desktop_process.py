"""Desktop child containment. Windows uses an unnamed kill-on-close Job Object."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from typing import Any


def prepare_containment() -> None:
    """On Linux, adopt orphaned descendants so shutdown can reap its whole group."""
    if sys.platform == "linux":
        import ctypes

        libc = ctypes.CDLL(None, use_errno=True)
        libc.prctl.argtypes = [
            ctypes.c_int,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_ulong,
        ]
        libc.prctl.restype = ctypes.c_int
        if libc.prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
            raise OSError("Desktop descendant containment is unavailable")


class ProcessTree:
    """Own a process tree until it has been stopped and the root reaped."""

    def __init__(self, process: subprocess.Popen[bytes]):
        self.process = process
        self._lock = threading.Lock()
        self._closed = False
        self._job: Any = None
        self._kernel: Any = None
        if os.name == "nt":
            self._attach_windows_job()

    def _attach_windows_job(self) -> None:
        import ctypes
        from ctypes import wintypes

        class BasicLimits(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_longlong),
                ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class IOCounters(ctypes.Structure):
            _fields_ = [
                (name, ctypes.c_ulonglong)
                for name in (
                    "ReadOperationCount",
                    "WriteOperationCount",
                    "OtherOperationCount",
                    "ReadTransferCount",
                    "WriteTransferCount",
                    "OtherTransferCount",
                )
            ]

        class ExtendedLimits(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", BasicLimits),
                ("IoInfo", IOCounters),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        kernel = getattr(ctypes, "WinDLL")("kernel32", use_last_error=True)
        kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        kernel.CreateJobObjectW.restype = wintypes.HANDLE
        kernel.SetInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        kernel.SetInformationJobObject.restype = wintypes.BOOL
        kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        kernel.AssignProcessToJobObject.restype = wintypes.BOOL
        kernel.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        kernel.TerminateJobObject.restype = wintypes.BOOL
        kernel.QueryInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.c_void_p,
        ]
        kernel.QueryInformationJobObject.restype = wintypes.BOOL
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        job = kernel.CreateJobObjectW(None, None)
        if not job:
            raise OSError("Could not create desktop process containment")
        limits = ExtendedLimits()
        limits.BasicLimitInformation.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE
        try:
            if not kernel.SetInformationJobObject(
                job, 9, ctypes.byref(limits), ctypes.sizeof(limits)
            ):
                raise OSError("Could not configure desktop process containment")
            handle = wintypes.HANDLE(int(getattr(self.process, "_handle")))
            if not kernel.AssignProcessToJobObject(job, handle):
                raise OSError("Could not contain desktop audit process")
        except BaseException:
            kernel.CloseHandle(job)
            raise
        self._kernel, self._job = kernel, job

    def _stop_windows_job(self) -> None:
        import ctypes
        from ctypes import wintypes

        class Accounting(ctypes.Structure):
            _fields_ = [
                ("TotalUserTime", ctypes.c_longlong),
                ("TotalKernelTime", ctypes.c_longlong),
                ("ThisPeriodTotalUserTime", ctypes.c_longlong),
                ("ThisPeriodTotalKernelTime", ctypes.c_longlong),
                ("TotalPageFaultCount", wintypes.DWORD),
                ("TotalProcesses", wintypes.DWORD),
                ("ActiveProcesses", wintypes.DWORD),
                ("TotalTerminatedProcesses", wintypes.DWORD),
            ]

        if not self._kernel.TerminateJobObject(self._job, 1):
            raise OSError("Could not terminate desktop process containment")
        end = time.monotonic() + 2
        while True:
            info = Accounting()
            if not self._kernel.QueryInformationJobObject(
                self._job, 1, ctypes.byref(info), ctypes.sizeof(info), None
            ):
                raise OSError("Could not confirm desktop process termination")
            if info.ActiveProcesses == 0:
                break
            if time.monotonic() >= end:
                raise OSError("Desktop descendants did not stop")
            time.sleep(0.01)
        if not self._kernel.CloseHandle(self._job):
            raise OSError("Could not release desktop process containment")
        self._job = None

    def stop(self) -> None:
        """Kill descendants even if the root already exited; never cancel a Python thread."""
        with self._lock:
            if self._closed:
                return
            if self._job is not None:
                self._stop_windows_job()
            elif os.name != "nt":
                try:
                    os.killpg(self.process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            elif self.process.poll() is None:
                self.process.kill()
            self.process.wait(timeout=2)
            if sys.platform == "darwin":
                # launchd reaps orphaned children on macOS; confirm the entire
                # group disappeared before claiming cleanup or releasing files.
                end = time.monotonic() + 2
                while True:
                    try:
                        os.killpg(self.process.pid, 0)
                    except ProcessLookupError:
                        break
                    if time.monotonic() >= end:
                        raise OSError("Desktop descendants did not stop")
                    time.sleep(0.01)
            if sys.platform == "linux":
                end = time.monotonic() + 1
                while True:
                    try:
                        pid, _status = os.waitpid(-self.process.pid, os.WNOHANG)
                    except ChildProcessError:
                        break
                    if pid == 0:
                        if time.monotonic() >= end:
                            raise OSError("Desktop descendants did not stop")
                        time.sleep(0.01)
            self._closed = True
