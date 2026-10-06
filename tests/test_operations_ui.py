import os
import sys
from pathlib import Path
import tempfile
import sqlite3
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
# Import production paths only after selecting a disposable user directory.
_sandbox=tempfile.TemporaryDirectory(prefix='deporiaq-ui-test-')
os.environ['LOCALAPPDATA']=_sandbox.name
import deporiaq_qt as ui
from deporiaq_analiz import REPORTS
from deporiaq_analiz_ui import AnalysisWindow, CommandPalette
from PySide6.QtTest import QTest

@pytest.fixture(scope='module')
def application():
    app=ui.QApplication.instance() or ui.QApplication([])
    app.setStyleSheet(ui.STIL)
    yield app

@pytest.fixture
def window(application,tmp_path,monkeypatch):
    errors=[]
    monkeypatch.setattr(sys,'excepthook',lambda *x:errors.append(x))
    db=ui.Veritabani(tmp_path/'fixture.db')
    db.ilk_kurulumu_tamamla('ÖRNEK İŞLETME · TEST VERİSİ','Kitabevi','Merkez Depo','TL','TEST_ADMIN','Fixture!Password2026')
    user=db.baglanti.execute('SELECT * FROM kullanicilar LIMIT 1').fetchone()
    monkeypatch.setattr(ui.AnaPencere,'cloud_oturumunu_yenile',lambda self:None)
    monkeypatch.setattr(ui.AnaPencere,'kurlari_yenile',lambda self:None)
    w=ui.AnaPencere(db,user,None);w.yenile()
    db.urun_ekle('0012345','İzmir Kitap',120,70,10)
    uid=db.baglanti.execute('SELECT id FROM urunler LIMIT 1').fetchone()[0]
    db.merkeze_stok_girisi(uid,35)
    yield w
    for timer in (w.canli_zamanlayici,w.senkron_zamanlayici,w.kur_zamanlayici):timer.stop()
    w.close();db.kapat()
    assert not errors,errors

def test_all_reports_filter_and_render(application,window):
    out=Path(__file__).resolve().parents[1]/'test-results';out.mkdir(exist_ok=True)
    dlg=AnalysisWindow(window.vt,window);dlg.show()
    for kind,_ in REPORTS:
        dlg.report_type.setCurrentIndex(dlg.report_type.findData(kind));application.processEvents()
        assert dlg.table.columnCount()>0 and dlg.note.text()
    dlg.report_type.setCurrentIndex(0)
    dlg.search.setText('izmir');QTest.qWait(220)
    assert dlg.table.rowCount()>0
    assert dlg.grab().save(str(out/'operations-1120x760.png'))
    dlg.resize(760,560);application.processEvents()
    assert dlg.grab().save(str(out/'operations-760x560.png'))
    dlg.search.setText('not present');QTest.qWait(220)
    assert dlg.table.rowCount()==0
    dlg.close()

def test_csv_pdf_real_exports(application,window,tmp_path,monkeypatch):
    dlg=AnalysisWindow(window.vt,window)
    monkeypatch.setattr(ui.QMessageBox,'information',lambda *args:None)
    dest=tmp_path/'report.csv'
    monkeypatch.setattr(ui.QFileDialog,'getSaveFileName',lambda *args:(str(dest),'CSV'))
    dlg.csv();assert 'İzmir Kitap' in dest.read_text(encoding='utf-8-sig')
    dest=tmp_path/'report.pdf';dlg.pdf();assert dest.read_bytes().startswith(b'%PDF')
    dlg.close()

def test_backup_reads_wal_and_preserves_source(window,tmp_path,monkeypatch):
    db=window.vt.baglanti
    db.execute('PRAGMA journal_mode=WAL')
    db.execute("UPDATE urunler SET ad='WAL son değişiklik'");db.commit()
    backup=tmp_path/'safe.db'
    monkeypatch.setattr(ui.QFileDialog,'getSaveFileName',lambda *args:(str(backup),'db'))
    monkeypatch.setattr(ui.QMessageBox,'information',lambda *args:None)
    window.yedek_al()
    with sqlite3.connect(backup) as copy:
        assert copy.execute('SELECT ad FROM urunler LIMIT 1').fetchone()[0]=='WAL son değişiklik'
        assert copy.execute('PRAGMA quick_check').fetchone()[0]=='ok'

def test_palette_calls_selected_action(application):
    calls=[]
    dlg=CommandPalette([('Stok Transferi',lambda:calls.append('transfer')),('Ürün Yönetimi',lambda:calls.append('product'))])
    dlg.search.setText('urun');dlg.run();application.processEvents()
    assert calls==['product']

def test_analysis_access_rechecked_for_license(window):
    dlg=AnalysisWindow(window.vt,window)
    window.lisans_kilitli=True
    assert not dlg.allowed()
    dlg.reload();assert dlg.result()==0
    dlg.close()

def test_viewer_cannot_load_analysis(application,window):
    window.kullanici={'rol':'GORUNTULEYICI'}
    dlg=AnalysisWindow(window.vt,window)
    assert not hasattr(dlg,'analysis')
    dlg.close()
