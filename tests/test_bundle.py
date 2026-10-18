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
    entries={key.replace('\\','/'):key for key in archive.toc}
    assert name in entries, 'Missing asset: '+name
    assert archive.extract(entries[name])==(root/name).read_bytes()
print('PASS: social icons and all built-in backgrounds are bundled')

for name in ('companion/Cat.qml','deporiaq_icon.svg'):
    assert name in entries,'Missing asset: '+name
    assert archive.extract(entries[name])==(root/name).read_bytes()
assert any(name.endswith('QtQuick3D/qmldir') for name in entries),'QtQuick3D QML module is missing'
assert any('QtQuick3D' in name and name.endswith('.dll') for name in entries),'QtQuick3D runtime is missing'
assert any('QtQuickWidgets' in name and name.endswith('.pyd') for name in entries),'QQuickWidget Python binding is missing'
print('PASS: exact companion scene, brand icon and Qt Quick 3D runtime are bundled')
