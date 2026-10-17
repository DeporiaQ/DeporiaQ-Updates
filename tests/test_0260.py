"""0.26 behaviour checks: live language without data loss, ownership and discovery."""
import json,time,threading
from pathlib import Path
from types import SimpleNamespace
from test_operations_ui import application,window
from test_0250 import WorkspaceClient,sync
import deporiaq_qt as ui
from deporiaq_i18n import T,Text,render,set_language,language,QLabel,QPushButton,QComboBox
from deporiaq_workspace_ui import BasketDialog,RecordsDialog
from deporiaq_commerce_ui import PlansDialog,ServerDialog
from deporiaq_assistant import AssistantPanel,ask_server
from PySide6.QtCore import Qt,QCoreApplication,QEvent
from PySide6.QtTest import QTest


def finish(application,predicate,seconds=3):
    end=time.monotonic()+seconds
    while predicate() and time.monotonic()<end:QTest.qWait(10)
    assert not predicate()


def test_language_preserves_customer_data_and_unsaved_basket(application,window,monkeypatch):
    sync(monkeypatch);d=BasketDialog(WorkspaceClient(),window);d.show()
    d.barcode.setText('9780000000001');d.add();d.barcode.setText('00007001');d.cash.setValue(12.50)
    before=json.dumps(d.lines);combo=QComboBox();combo.addItems([T('Yapılacak'),T('Tamamlandı')]);combo.setCurrentIndex(1)
    customer=QLabel('Satışlar');label=QLabel(T('Satışlar'));plans=PlansDialog(None,window)
    for code in ['en','tr','en']:
        window.change_language(code);application.processEvents()
        assert json.dumps(d.lines)==before and d.barcode.text()=='00007001' and d.cash.value()==12.50
        assert customer.text()=='Satışlar' and combo.currentText()=='Tamamlandı' and combo.currentIndex()==1
        assert label.text()==('Sales' if code=='en' else 'Satışlar')
        assert d.grid.horizontalHeaderItem(1).text()==('Product' if code=='en' else 'Ürün')
        assert window.header.search.placeholderText()==('Search products, barcodes or menus…' if code=='en' else 'Ürün, barkod veya menü ara…')
    assert 'Multi-Item Sale' in d.windowTitle()
    assert any('including the administrator' in x.text() for x in plans.findChildren(ui.QTableWidget)[0].findItems('administrator',Qt.MatchFlag.MatchContains))
    d.lines=[];d.close();plans.close();window.change_language('tr')


def test_task_status_remains_server_enum_in_english(application,window,monkeypatch):
    sync(monkeypatch);window.change_language('en');client=WorkspaceClient();d=RecordsDialog(client,'task',window)
    d.fields['name'].setText('Test task');d.fields['status'].setCurrentText('Tamamlandı')
    assert d.fields['status'].currentText()=='Tamamlandı'
    # str()/JSON/database calls must receive the stable Turkish contract.
    assert str(d.fields['status'].currentText())=='Tamamlandı'
    d.fields['name'].clear();d.remember_saved();d.close();window.change_language('tr')


def test_header_geometry_light_and_flags(application,window):
    out=Path(__file__).resolve().parents[1]/'test-results';out.mkdir(exist_ok=True)
    for code in ['tr','en']:
        window.change_language(code)
        for width,height in [(1920,1000),(1366,768),(900,650)]:
            window.resize(width,height);window.show();application.processEvents();h=window.header
            assert abs(h.search.geometry().center().x()-h.width()/2)<=1
            assert not h.search.geometry().intersects(h.profile.geometry())
            assert not h.assistant.geometry().intersects(h.controls.geometry())
            assert h.search.geometry().right()<h.assistant.geometry().left()
            assert all(not b.text() for b in window.language_flags.values())
            assert 'kayıtlı cihaz' not in window.cloud.text() and 'registered device' not in window.cloud.text()
            assert window.grab().save(str(out/f'0260-{code}-{width}.png'))
    window.toggle_mode();application.processEvents();assert window.icerik.light_mode
    assert window.grab().save(str(out/'0260-en-light.png'));window.toggle_mode();window.change_language('tr')


def test_name_save_is_owner_only_and_server_confirmed(application,window,monkeypatch):
    cloud=window.cloud_client;cloud.access_token='test';cloud.company_id='fixture';cloud.company_name='Original';calls=[]
    def request(path,method,payload):calls.append(payload.copy());return {'name':payload.get('p_name','Original')}
    monkeypatch.setattr(cloud,'_istek',request)
    for role in ['admin','manager','viewer','employee']:
        cloud.role=role;d=ui.AyarlarPenceresi(window.vt,cloud,lambda:None,window)
        assert d.isletme.isReadOnly() and not d.company_save.isEnabled()
        d.isletme.setText('Not allowed');d.genel_kaydet();assert not calls;d.close()
    cloud.role='owner';d=ui.AyarlarPenceresi(window.vt,cloud,lambda:None,window);d.isletme.setText('İzmir Kitap Dünyası');d.genel_kaydet()
    finish(application,lambda:d.job is not None)
    assert window.company_label.text()=='İzmir Kitap Dünyası'
    assert window.vt.ayar_getir('isletme_adi')=='İzmir Kitap Dünyası' and cloud.company_name=='İzmir Kitap Dünyası'
    assert calls[-1]['p_expected_name']=='Original';d.close()
    def fail(*args):raise RuntimeError('DPQ_CONFLICT')
    monkeypatch.setattr(cloud,'_istek',fail);d=ui.AyarlarPenceresi(window.vt,cloud,lambda:None,window);d.isletme.setText('Rejected');d.genel_kaydet();finish(application,lambda:d.job is not None)
    assert window.company_label.text()=='İzmir Kitap Dünyası';d.close();cloud.access_token=''


def test_search_ignores_stale_network_results_and_supports_both_languages(application,window,monkeypatch):
    cloud=window.cloud_client;cloud.access_token='test';cloud.company_id='fixture';started=threading.Event();release=threading.Event()
    def request(path,method,payload):
        if payload['p_query']=='old':started.set();release.wait(2)
        return [{'kind':'product','id':'test','title':payload['p_query'],'subtitle':'001234'}]
    monkeypatch.setattr(cloud,'_istek',request);c=window.search_controller;c.changed('old');c.timer.stop();c.lookup()
    finish(application,lambda:not started.is_set());c.changed('izmir');release.set();finish(application,lambda:c.job is not None)
    c.timer.stop();c.lookup();finish(application,lambda:c.job is not None)
    assert [r['title'] for r in c.records]==['izmir']
    cloud.access_token='';window.change_language('en');c.changed('stok');assert any(render(r['title'])=='Products & Stock' for r in c.records)
    c.changed('settings');assert any(render(r['title'])=='Settings' for r in c.records)
    c.timer.stop();c.hide();window.change_language('tr')


def test_assistant_inside_app_and_failure_is_not_fake_answer(application,window,monkeypatch):
    import deporiaq_assistant as mod
    calls=[]
    def fake(cloud,action,messages=None,locale=None):
        calls.append((action,messages,locale))
        if action=='status':return {'ready':True}
        raise ValueError('Service unavailable')
    monkeypatch.setattr(mod,'ask_server',fake);window.show();window.assistant_open();panel=window.assistant_panel
    finish(application,lambda:panel.job is not None);assert panel.ready and panel.isVisible() and not panel.isFloating()
    panel.input.setPlainText('Transfer nasıl yapılır?');panel.submit();finish(application,lambda:panel.job is not None)
    assert panel.history==[] and panel.status.text()=='Service unavailable'
    assert calls[-1][1]==[{'role':'user','content':'Transfer nasıl yapılır?'}]
    assert panel.messages_layout.count()==1
    panel.close()


def test_catalogue_covers_all_explicit_translations():
    import ast,string
    from deporiaq_translations import EN
    root=Path(__file__).resolve().parents[1];missing=[]
    for p in root.glob('deporiaq*.py'):
        if p.name in ('deporiaq_i18n.py','deporiaq_translations.py'):continue
        for n in ast.walk(ast.parse(p.read_text(encoding='utf-8'))):
            if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='T' and n.args and isinstance(n.args[0],ast.Constant):
                source=n.args[0].value
                if source not in EN and any(c.isalpha() for c in source) and not source.startswith('{'):missing.append((p.name,n.lineno,source))
    assert not missing,missing
    fields=lambda s:{name for _,name,_,_ in string.Formatter().parse(s) if name is not None}
    for a,b in EN.items():assert fields(a)==fields(b),(a,b)
