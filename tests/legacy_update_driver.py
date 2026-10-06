"""CI only: exercise the unmodified 0.22.4 update flow using a local installer.

Only the download source and log destination are supplied by the test harness.
The old download/hash/install/relaunch implementation is preserved verbatim.
Build as DeporiaQUpdate.exe so Restart Manager reproduces the reported failure.
"""
import hashlib
import subprocess
import sys
from pathlib import Path
import notifier_0_22_4
import notifier_0_22_5
legacy = notifier_0_22_5 if "--from-0.22.5" in sys.argv else notifier_0_22_4

setup, log, returned = map(Path, sys.argv[1:4])
original_run = subprocess.run


def run_with_log(args, **kwargs):
    if args and str(args[0]).lower().endswith(".exe") and "/VERYSILENT" in args:
        args = [*args, f"/LOG={log}"]
    return original_run(args, **kwargs)


legacy.subprocess.run = run_with_log
window = legacy.Bildirim({
    "version": "0.23.0", "url": setup.resolve().as_uri(),
    "sha256": hashlib.sha256(setup.read_bytes()).hexdigest(),
    "notes": "Isolated CI upgrade test",
})
window.root.after(200, window.indir)
window.calistir()
returned.write_text("Legacy updater survived and returned", encoding="utf-8")
