"""Real Windows installer and 0.22.4 frozen-updater regression, isolated CI only.

Never execute on a customer's desktop: the legacy code uses taskkill /IM.
"""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import psutil


def configure_console():
    """GitHub logs are UTF-8; Windows may otherwise select cp1252 for pipes."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "test-results"


def stage_processes(stage):
    result = []
    for process in psutil.process_iter(["pid", "exe"]):
        try:
            exe = process.info["exe"]
            if exe and Path(exe).resolve().parent == stage.resolve():
                result.append(process)
        except (psutil.Error, OSError):
            pass
    return result


def stop_stage(stage):
    processes = stage_processes(stage)
    for process in processes:
        try:
            process.kill()
        except psutil.Error:
            pass
    psutil.wait_procs(processes, timeout=15)


def visible_windows(stage):
    pids = {p.pid for p in stage_processes(stage) if p.name().lower() == "deporiaq.exe"}
    result = []
    user32 = ctypes.windll.user32
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]

    @callback_type
    def callback(hwnd, _):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in pids and user32.IsWindowVisible(hwnd):
            text = ctypes.create_unicode_buffer(1024)
            user32.GetWindowTextW(hwnd, text, len(text))
            if "DeporiaQ 0.22.5" in text.value:
                result.append({"pid": pid.value, "title": text.value})
        return True

    user32.EnumWindows(callback, 0)
    return result


def wait_for_window(stage, label):
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        found = visible_windows(stage)
        if found:
            time.sleep(3)
            found = visible_windows(stage)
            if len(found) != 1:
                raise AssertionError(f"{label}: expected one stable window, found {found}")
            print(f"PASS {label}: {found}", flush=True)
            from PIL import ImageGrab
            ImageGrab.grab().save(OUT / f"windows-{label}.png")
            return found
        time.sleep(1)
    raise AssertionError(f"{label}: Setup did not open a visible DeporiaQ 0.22.5 window")


def main():
    if os.name != "nt" or os.environ.get("GITHUB_ACTIONS") != "true":
        raise RuntimeError("Run only on the isolated Windows GitHub Actions runner")
    if not ctypes.windll.shell32.IsUserAnAdmin():
        raise RuntimeError("Installer regression requires the runner's administrator account")
    OUT.mkdir(exist_ok=True)
    stage = Path(os.environ["RUNNER_TEMP"]) / "DeporiaQ Install Regression"
    stage.mkdir(exist_ok=True)
    setup = ROOT / "kurulum" / "DeporiaQ_Setup_0.22.5.exe"
    legacy = ROOT / "test-old-dist" / "DeporiaQUpdate.exe"
    report = {"platform": sys.getwindowsversion().build, "tests": {}}
    try:
        # Fresh silent install must launch too; no test code starts DeporiaQ.exe.
        result = subprocess.run([str(setup), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
                                 f"/DIR={stage}", f"/LOG={OUT / 'fresh-install.log'}"], timeout=180)
        assert result.returncode == 0, result.returncode
        report["tests"]["fresh"] = wait_for_window(stage, "fresh")
        stop_stage(stage)

        # Install the exact old notifier implementation over the new notifier.
        # It launches Setup, which must terminate that frozen executable to replace it.
        shutil.copy2(legacy, stage / "DeporiaQUpdate.exe")
        returned = OUT / "legacy-returned.txt"
        returned.unlink(missing_ok=True)
        old = subprocess.Popen([str(stage / "DeporiaQUpdate.exe"), str(setup),
                                str(OUT / "legacy-upgrade.log"), str(returned)])
        report["tests"]["legacy-upgrade"] = wait_for_window(stage, "legacy-upgrade")
        old.wait(timeout=20)
        report["legacy_exit_code"] = old.returncode
        report["legacy_mainloop_returned"] = returned.exists()
        log = (OUT / "legacy-upgrade.log").read_text(encoding="utf-8-sig", errors="replace")
        assert "Shutting down applications using our files" in log, "Missing Restart Manager shutdown"
        assert "DeporiaQUpdate" in log, "Old updater not found by Restart Manager"
        assert "Installation process succeeded" in log, "Upgrade did not finish"
        assert f"Filename: {stage / 'DeporiaQ.exe'}" in log, "Setup did not own relaunch"
        # Also check that installed bytes are exactly the newly built applications.
        import hashlib
        for name in ("DeporiaQ.exe", "DeporiaQUpdate.exe"):
            digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
            assert digest(stage / name) == digest(ROOT / "dist" / name), name
        time.sleep(8)
        assert len(visible_windows(stage)) == 1, "Duplicate application window after upgrade"
        report["status"] = "passed"
    finally:
        (OUT / "windows-result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        stop_stage(stage)
    print("PASS: actual installer relaunch after forced termination of the frozen 0.22.4 updater")


if __name__ == "__main__":
    configure_console()
    main()
