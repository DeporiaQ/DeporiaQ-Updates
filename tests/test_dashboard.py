"""Render production Qt widgets with isolated, synthetic data; no Cloud calls."""
import os
import sys
import tempfile
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
test_home = tempfile.TemporaryDirectory(prefix="deporiaq-render-")
os.environ["LOCALAPPDATA"] = test_home.name

import deporiaq_qt as ui
from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtTest import QTest


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "test-results")
    out.mkdir(parents=True, exist_ok=True)
    errors = []
    sys.excepthook = lambda *args: errors.append("".join(traceback.format_exception(*args)))
    app = ui.QApplication([])
    app.setStyleSheet(ui.STIL)
    app.setFont(ui.QFont("Segoe UI", 10))
    background = ui.DashboardArkaPlan()
    background.setObjectName("dashboardArkaPlan")
    assert not background.gorsel.isNull(), "Warehouse image failed to load"
    for width, height in [(1600, 900), (1000, 700), (760, 560)]:
        background.resize(width, height)
        background.show()
        app.processEvents()
        actual = background.grab().toImage()
        # Independent expected paint: integer-coordinate drawPixmap, no mixed overload.
        expected = QPixmap(width, height)
        expected.fill(ui.QColor("#131A26"))
        p = QPainter(expected)
        scaled = background.gorsel.scaled(background.size(), ui.Qt.KeepAspectRatioByExpanding,
                                         ui.Qt.SmoothTransformation)
        p.drawPixmap(-(scaled.width()-width)//2, -(scaled.height()-height)//2, scaled)
        p.fillRect(expected.rect(), ui.QColor(7, 15, 28, 85))
        p.end()
        reference = expected.toImage()
        for x, y in [(40, 40), (width//2, height//2), (width-40, height-40)]:
            a, b = actual.pixelColor(x, y), reference.pixelColor(x, y)
            assert max(abs(a.red()-b.red()), abs(a.green()-b.green()), abs(a.blue()-b.blue())) <= 3
    background.close()

    db = ui.Veritabani(Path(test_home.name) / "fixture.db")
    db.ilk_kurulumu_tamamla("DEPO GÖRÜNÜM TESTİ", "Kitabevi", "Merkez Depo", "TL",
                          "GORSEL_TEST", "TestFixture!2026Only")
    user = db.baglanti.execute("SELECT * FROM kullanicilar LIMIT 1").fetchone()
    # Only external services are disabled in the fixture, production paint/layout stays intact.
    ui.AnaPencere.cloud_oturumunu_yenile = lambda self: None
    ui.AnaPencere.kurlari_yenile = lambda self: None
    window = ui.AnaPencere(db, user, None)
    window.yenile()
    for width, height in [(1920, 1000), (1366, 768), (900, 650)]:
        window.resize(width, height)
        window.show()
        app.processEvents()
        window.duyarli_yerlesimi_guncelle()
        app.processEvents()
        QTest.qWait(150)
        with_photo = window.grab().toImage()
        assert with_photo.save(str(out / f"dashboard-{width}x{height}.png"))
        # Ensure the image remains visible THROUGH panels, not merely in empty margins.
        original = window.icerik.gorsel
        window.icerik.gorsel = QPixmap()
        window.icerik.update()
        app.processEvents()
        without_photo = window.grab().toImage()
        changed = 0
        samples = 0
        for x in range(210, width-20, 13):
            for y in range(150, height-70, 13):
                a, b = with_photo.pixelColor(x, y), without_photo.pixelColor(x, y)
                samples += 1
                changed += max(abs(a.red()-b.red()), abs(a.green()-b.green()), abs(a.blue()-b.blue())) > 5
        assert changed / samples > .30, f"Warehouse obscured at {width}: {changed}/{samples}"
        window.icerik.gorsel = original
        window.icerik.update()
    for timer in (window.canli_zamanlayici, window.senkron_zamanlayici, window.kur_zamanlayici):
        timer.stop()
    window.close()
    db.kapat()
    assert not errors, "\n".join(errors)
    print("PASS: background pixels, three window sizes, visible photo through panels, no Qt exceptions")


if __name__ == "__main__":
    main()
