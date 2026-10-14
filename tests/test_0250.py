from pathlib import Path
import copy,json
from decimal import Decimal
from test_operations_ui import application,window
from test_commerce_ui import DATA
from deporiaq_commerce_ui import ServerDialog
from deporiaq_workspace_ui import BasketDialog,ProductDetailsDialog,RecordsDialog,CollectionDialog,DamageDialog,BulkPricesDialog,ImportDialog
from deporiaq_visuals import NotificationButton,WorkspaceDialog
from PySide6.QtCore import QTimer,Qt
from PySide6.QtWidgets import QLabel,QPushButton

class WorkspaceClient:
    def __init__(self):self.calls=[];self.records=[]
    def snapshot(self):
        data=copy.deepcopy(DATA);data['products'][0].update(sale_price='100.00',purchase_price='60.00');data['sale_locations']=['0','1','2','3'];return data
    def read(self,action,payload=None):return {'records':self.records,'discount_limit':0}
    def mutate(self,action,payload):self.calls.append((action,copy.deepcopy(payload)));return {'id':'sale-test','total':100,'items':payload.get('items',[])}

def sync(monkeypatch):monkeypatch.setattr(ServerDialog,'run',lambda self,fn,done=None:done(fn()) if done else fn())

def test_new_screen_layouts(application,window,monkeypatch):
    sync(monkeypatch);client=WorkspaceClient();out=Path(__file__).resolve().parents[1]/'test-results';out.mkdir(exist_ok=True)
    screens=[('basket',BasketDialog(client,window)),('product',ProductDetailsDialog(client,window)),('supplier',RecordsDialog(client,'supplier',window)),('task',RecordsDialog(client,'task',window)),('batch',RecordsDialog(client,'batch',window)),('purchase',CollectionDialog(client,'purchase',window)),('bundle',CollectionDialog(client,'bundle',window)),('damage',DamageDialog(client,window)),('prices',BulkPricesDialog(client,window)),('import',ImportDialog(client,window))]
    for name,screen in screens:
        screen.show();application.processEvents();assert screen.grab().save(str(out/f'0250-{name}.png'));screen.close()

def test_basket_rounding_payment_guard_and_submit(application,window,monkeypatch):
    sync(monkeypatch);client=WorkspaceClient();d=BasketDialog(client,window)
    d.barcode.setText('9780000000001');d.quantity.setValue(2);d.add();assert d.total()==Decimal('200.00')
    d.lines[0]['discount']=10;d.render();assert d.total()==Decimal('180.00')
    d.cash.setValue(100);d.sell();assert not client.calls
    d.card.setValue(80);d.sell();assert client.calls[0][0]=='workspace_cart_sale' and not d.lines;d.close()

def test_bulk_preview_invalidates_after_filter_change(application,window,monkeypatch):
    sync(monkeypatch);d=BulkPricesDialog(WorkspaceClient(),window);d.percent.setValue(12.5);d.calculate()
    assert d.preview[0]['price']=='112.50' and d.apply_button.isEnabled()
    d.filter.setText('missing');assert not d.preview and not d.apply_button.isEnabled();d.close()

def test_import_duplicate_and_leading_zero_validation(application,window,monkeypatch):
    sync(monkeypatch);d=ImportDialog(WorkspaceClient(),window)
    from PySide6.QtWidgets import QComboBox
    for i,(key,label) in enumerate(d.HEADERS):
        c=QComboBox();c.addItem(label,i);d.columns[key]=c
    d.source=[['001234','Kitap','20.50','10','3']];d.preview();assert d.items[0]['barcode']=='001234'
    d.source.append(['001234','Diğer','30','10','3']);d.preview();assert not d.items
    d.source=[[1234,'Kitap','20','10','3']];d.preview();assert not d.items;d.close()

def test_notifications_email_and_social_geometry(application,window):
    assert isinstance(window.support_mail,QLabel) and not isinstance(window.support_mail,QPushButton)
    buttons=window.sosyal.findChildren(QPushButton);assert len({(b.width(),b.height()) for b in buttons})==1
    assert not buttons[-1].text() and not buttons[-1].icon().isNull()
    window.notify('Yeni','Test',force=True);assert window.notification_button.unread==1 and window.notification_button.timer.isActive()
    stored=json.loads(window.vt.ayar_getir(window.notification_storage_key));assert stored[-1][1:] == ['Yeni','Test']
    window.notification_button.setCount(0);assert not window.notification_button.timer.isActive()

def test_panel_allows_main_window_controls(application,window):
    d=WorkspaceDialog(window)
    def check():
        assert application.activeModalWidget() is None
        window.showNormal();d.accept()
    QTimer.singleShot(10,check);assert d.exec()==1


def test_repeated_theme_changes_keep_live_panels(application,window):
    from deporiaq_preferences import apply_appearance
    from PySide6.QtCore import QCoreApplication,QEvent
    for i in range(20):
        panel=WorkspaceDialog(window);panel.show();application.processEvents()
        window.vt.ayar_kaydet('ui_theme','Grafit' if i%2 else 'Gece Mavisi')
        apply_appearance(window);panel.close();panel.deleteLater()
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);application.processEvents()
    window.vt.baglanti.commit()

def test_unsaved_record_can_cancel_or_discard(application,window,monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    sync(monkeypatch);d=RecordsDialog(WorkspaceClient(),'supplier',window);d.show()
    d.fields['name'].setText('Unsaved');d.mark_edited();assert 'Kaydedilmemiş' in d.windowTitle()
    monkeypatch.setattr(QMessageBox,'question',lambda *a:QMessageBox.StandardButton.Cancel)
    assert not d.close() and d.isVisible()
    monkeypatch.setattr(QMessageBox,'question',lambda *a:QMessageBox.StandardButton.Discard)
    assert d.close()

def test_expired_subscription_is_not_reported_as_network_failure(window):
    window.cloud_hatasi('DPQ_LICENSE: expired')
    assert window.lisans_kilitli and window.subscription_label.text()=='Abonelik aktif değil'
    assert window.license_timer.interval()==1800000 and window.presence_timer.interval()==10000
