"""Verify the release EXE embeds the actual warehouse image bytes."""
from pathlib import Path
from PyInstaller.archive.readers import CArchiveReader

root = Path(__file__).resolve().parents[1]
archive = CArchiveReader(str(root / "dist" / "DeporiaQ.exe"))
name = "dashboard_background.jpg"
assert name in archive.toc, "Warehouse photo missing from frozen application"
assert archive.extract(name) == (root / name).read_bytes(), "Frozen photo differs from tested photo"
print("PASS: frozen EXE contains the tested warehouse image")

for name in ['whatsapp_icon.svg','x_icon.svg','chevron_up.svg']+[str(p.relative_to(root)).replace('\\','/') for p in (root/'backgrounds').glob('*.svg')]:
    assert name in archive.toc, 'Missing asset: '+name
    assert archive.extract(name)==(root/name).read_bytes()
print('PASS: social icons and all built-in backgrounds are bundled')
