from pathlib import Path
import copy,json,time
from test_operations_ui import application,window
from test_commerce_ui import Client,DATA
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt
import deporiaq_qt as ui
import deporiaq_preferences as prefs
from deporiaq_commerce_ui import ServerDialog,StockDialog,PlansDialog,SaleDialog,SubscriptionClock,quantity_text,csv_cell

def test_countdown_uses_server_time_and_never_changes_expiry():
    ticks=[10.0];data={'valid_until':'2027-09-30T21:00:00Z','server_time':'2027-09-29T21:00:00Z'};old=copy.deepcopy(data)
    clock=SubscriptionClock(data,lambda:ticks[0]);assert clock.seconds()==86400
    ticks[0]+=3661;assert clock.seconds()==82739 and '22 saat' in clock.text()
    ticks[0]+=90000;assert clock.seconds()==0 and 'doldu' in clock.text();assert data==old
    assert SubscriptionClock({'valid_until':data['valid_until']}).seconds() is None

def test_integer_display_preserves_unexpected_fraction():
    assert quantity_text(80.0)=='80' and quantity_text('0.000')=='0'
    assert quantity_text('80.50')=='80.5'
    assert csv_cell('=1+1')=="'=1+1"

def test_stock_search_filter_select_copy_and_export(application,window,monkeypatch,tmp_path):
    monkeypatch.setattr(ServerDialog,'run',lambda self,fn,done=None:done(fn()) if done else fn())
    d=StockDialog(Client(),'catalog',window);d.show();application.processEvents()
    assert d.grid.rowCount()==4 and d.grid.item(0,3).text()=='2'
    d.search.setText('978000');assert d.grid.rowCount()==4
    d.filter_state.setCurrentIndex(2);assert d.grid.rowCount()==1
    d.filter_state.setCurrentIndex(0);d.filter_location.setCurrentIndex(d.filter_location.findData('3'));assert d.grid.rowCount()==1
    d.grid.selectRow(0);assert d.location.currentData()=='3' and d.product.currentData()=='p'
    d.copy_barcode();assert application.clipboard().text()=='9780000000001'
    path=tmp_path/'stock.csv';monkeypatch.setattr(ui.QFileDialog,'getSaveFileName',lambda *a:(str(path),''));d.export_stock()
    text=path.read_text(encoding='utf-8-sig');assert 'C Şubesi' in text and 'A Şubesi' not in text
    d.search.setText('absent');assert d.grid.rowCount()==0 and '0 kayıt' in d.stock_summary.text();d.close()

def test_lock_blocks_escape_and_home_then_unlocks(application,window):
    window.show();application.processEvents();guard=window.session_guard;guard.lock();d=guard.dialog
    QTest.keyClick(d,Qt.Key.Key_Escape);assert d.isVisible()
    QTest.keyClick(d,Qt.Key.Key_1,Qt.KeyboardModifier.ControlModifier);assert d.isVisible()
    d.password.setText('incorrect');d.unlock();assert d.isVisible()
    d.retry_at=0;d.password.setText('Fixture!Password2026');d.unlock();application.processEvents();assert guard.dialog is None

def test_idle_lock_setting_is_effective(application,window):
    window.show();application.processEvents();window.vt.ayar_kaydet('otomatik_kilit_dakika','5')
    guard=window.session_guard;guard.last_activity=time.monotonic()-301;guard.check();assert guard.dialog
    guard.dialog.password.setText('Fixture!Password2026');guard.dialog.unlock();application.processEvents()
    window.vt.ayar_kaydet('otomatik_kilit_dakika','0');guard.last_activity=time.monotonic()-900;guard.check();assert guard.dialog is None

def test_ctrl1_inside_dialog_returns_home(application,window,monkeypatch):
    window.show();d=ui.QDialog(window);d.setModal(True);d.show();application.processEvents()
    monkeypatch.setattr(ui.QMessageBox,'question',lambda *a:ui.QMessageBox.StandardButton.Yes)
    QTest.keyClick(d,Qt.Key.Key_1,Qt.KeyboardModifier.ControlModifier);application.processEvents();assert not d.isVisible()

def test_preferences_save_and_render_all_tabs(application,window,monkeypatch):
    monkeypatch.setattr(ui.QMessageBox,'information',lambda *a:None)
    d=ui.AyarlarPenceresi(window.vt,window.cloud_client,window.yenile,window);d.show()
    out=Path(__file__).resolve().parents[1]/'test-results';out.mkdir(exist_ok=True)
    tabs=d.findChild(ui.QTabWidget)
    for i in (0,2,3):
        tabs.setCurrentIndex(i);application.processEvents();d.grab().save(str(out/f'0243-settings-{i}.png'))
    d.theme.setCurrentText('Grafit');d.font_size.setValue(15);d.background_enabled.setChecked(False)
    button=next(b for b in d.findChildren(ui.QPushButton) if b.text()=='Görünümü Uygula');button.click()
    assert window.vt.ayar_getir('ui_theme')=='Grafit' and not window.icerik.background_enabled
    d.notification_options['notify_cloud'].setChecked(False);d.bildirim_kaydet();window.notify('Bağlantı','Test','notify_cloud');assert not any(row[1]=='Bağlantı' for row in window.notifications)
    d.close();application.setStyleSheet(ui.STIL)

def test_diagnostics_does_not_export_secrets(application,window,monkeypatch,tmp_path):
    path=tmp_path/'diagnostics.json';window.cloud_client.access_token='TOP_SECRET'
    monkeypatch.setattr(ui.QFileDialog,'getSaveFileName',lambda *a:(str(path),''));monkeypatch.setattr(ui.QMessageBox,'information',lambda *a:None)
    prefs.export_diagnostics(window,window);report=path.read_text();assert 'TOP_SECRET' not in report and 'TEST_ADMIN' not in report
    assert json.loads(report)['local_database_check']=='ok'

def test_compact_sale_and_plans(application,window,monkeypatch):
    monkeypatch.setattr(ServerDialog,'run',lambda self,fn,done=None:done(fn()) if done else fn())
    out=Path(__file__).resolve().parents[1]/'test-results'
    for name,d in [('sale',SaleDialog(Client(),parent=window)),('plans',PlansDialog(Client(),window)),('stock',StockDialog(Client(),'count',window))]:
        d.show();application.processEvents();assert d.heading.height()<70
        d.grab().save(str(out/f'0243-{name}.png'));d.close()


def test_login_honours_disabled_update_checks(application,window,monkeypatch):
    window.vt.ayar_kaydet('notify_update','0')
    d=ui.GirisPenceresi(window.vt);d.show();application.processEvents()
    def forbidden(*args):raise AssertionError('Disabled update check started a network worker')
    monkeypatch.setattr(ui,'GuncellemeKontrolu',forbidden)
    d.guncelleme_denetle();d.close()
