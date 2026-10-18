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
from deporiaq_assistant import AssistantPanel,ACTIONS
from deporiaq_assistant_guide import TOPICS,BY_KEY,lookup
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


def test_live_help_and_unsaved_form_titles(application,window,monkeypatch):
    sync(monkeypatch);help_dialog=ui.YardimMerkezi(window.vt,window)
    d=RecordsDialog(WorkspaceClient(),'task',window)
    d.fields['name'].setText('Satışlar');d.mark_edited()
    for code,fragment in [('en','Unsaved change'),('tr','Kaydedilmemiş değişiklik')]:
        window.change_language(code);application.processEvents()
        assert fragment.casefold() in d.windowTitle().casefold()
        assert d.fields['name'].text()=='Satışlar'
        texts=[x.toPlainText() for x in help_dialog.findChildren(ui.QPlainTextEdit)]
        assert any(('Only the primary account owner' if code=='en' else 'yalnızca ana hesap sahibi') in x for x in texts)
    d.remember_saved();d.close();help_dialog.close()


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


def test_offline_assistant_navigation_language_and_no_network(application,window,monkeypatch):
    import socket,urllib.request
    def forbidden(*args,**kwargs):raise AssertionError('Offline guide tried to use the network')
    monkeypatch.setattr(socket,'create_connection',forbidden)
    monkeypatch.setattr(urllib.request,'urlopen',forbidden)
    monkeypatch.setattr(window.cloud_client,'_istek',forbidden)
    calls=[];monkeypatch.setattr(window,'transfer_ac',lambda:calls.append('transfer'))
    before=list(window.vt.baglanti.execute('SELECT * FROM stoklar').fetchall())
    window.resize(1366,768);window.show();window.assistant_open();panel=window.assistant_panel
    assert panel.ready and panel.isVisible() and not panel.isFloating() and panel.job is None
    question='Şubeler arası transfer nasıl yapılır?'
    panel.input.setPlainText(question);QTest.keyClick(panel.input,Qt.Key.Key_Return)
    assert panel.last_topic=='transfer' and panel.history==[question] and not calls
    buttons=[b for b in panel.findChildren(QPushButton) if b.property('guide_action')=='transfer']
    assert len(buttons)==1;QTest.mouseClick(buttons[0],Qt.MouseButton.LeftButton);assert calls==['transfer']
    out=Path(__file__).resolve().parents[1]/'test-results';out.mkdir(exist_ok=True)
    for code in ['tr','en']:
        window.change_language(code);QTest.qWait(80)
        assert panel.history==[question]
        assert any(('Transfers are limited' if code=='en' else 'Transfer satılabilir') in label.text() for label in panel.findChildren(QLabel))
        for label in panel.messages.findChildren(QLabel):
            if label.wordWrap():assert label.height()>=label.heightForWidth(label.width()),(label.height(),label.heightForWidth(label.width()))
        assert all(b.height()>=38 for b in panel.messages.findChildren(QPushButton))
        assert panel.grab().save(str(out/f'0260-guide-{code}.png'))
    assert before==list(window.vt.baglanti.execute('SELECT * FROM stoklar').fetchall())
    panel.input.setPlainText('What will the weather be tomorrow?');panel.submit()
    assert any('Could you describe the screen' in label.text() for label in panel.findChildren(QLabel))
    panel.reset();assert panel.history==[] and panel.last_topic is None and panel.messages_layout.count()==1
    window.change_language('tr');panel.close()


def test_guide_actions_recheck_roles_and_subscription(application,window,monkeypatch):
    calls=[];monkeypatch.setattr(window,'yedek_al',lambda:calls.append('backup'))
    monkeypatch.setattr(window,'transfer_ac',lambda:calls.append('transfer'))
    panel=AssistantPanel(window);panel.show_topic('backup')
    button=next(b for b in panel.findChildren(QPushButton) if b.property('guide_action')=='backup')
    assert button.isEnabled()
    window.kullanici={'rol':'GORUNTULEYICI'}
    button.click();panel.navigate('transfer');panel.navigate('__class__');assert calls==[]
    panel.show_topic('transfer');assert any(not b.isEnabled() for b in panel.findChildren(QPushButton) if b.property('guide_action')=='transfer')
    window.kullanici={'rol':'ANA_YONETICI'};window.lisans_kilitli=True;panel.navigate('backup');assert not calls
    assert panel.unavailable('support') is None
    window.lisans_kilitli=False;panel.navigate('backup');assert calls==['backup'];panel.close()


def test_guide_ambiguity_limits_followup_and_clear(application,window):
    panel=AssistantPanel(window)
    panel.input.setPlainText('transfer ve rezervasyon');panel.submit()
    assert panel.last_topic is None
    assert {b.property('topic_id') for b in panel.findChildren(QPushButton)} >= {'transfer','reservation'}
    panel.show_topic('receive');panel.input.setPlainText('nereden açacağım');panel.submit();assert panel.last_topic=='receive'
    panel.input.setPlainText('a'*2001);assert not panel.send.isEnabled()
    old=len(panel.history);panel.submit();assert len(panel.history)==old
    panel.input.setPlainText('Stok');QTest.keyClick(panel.input,Qt.Key.Key_Return,Qt.KeyboardModifier.ShiftModifier)
    assert '\n' in panel.input.toPlainText()
    for _ in range(30):panel.input.setPlainText('stok ekle');panel.submit()
    assert len(panel.history)==12 and panel.messages_layout.count()<=24
    panel.reset();assert not panel.send.isEnabled();panel.close()


def test_guide_matches_reviewed_topics_in_both_languages():
    questions={
      'Ürün nasıl eklerim?':'product','How do I create a product?':'product',
      'Stokları nasıl artıracağım?':'receive','how do I add stock':'receive',
      'Transfer yapmak istiyorum':'transfer','stock transferr':'transfer',
      'Aşk kitabından kaç tane var?':'lookup','How many books are available?':'lookup',
      'Stok sayımı nasıl yapılır':'count','physical inventory count':'count',
      'Elimdeki kitabı nasıl satarım?':'sale','How do I sell a book?':'sale',
      'Kargo rezervasyonu':'reservation','reserve for pickup':'reservation',
      'İşletme adını değiştirmek':'company','change business name':'company',
      'Yedek nasıl alınır?':'backup','back up my data':'backup',
      'Şifremi unuttum':'password','forgot my password':'password',
      'Nasıl İngilizce yaparım?':'language','switch language':'language',
      'Arka plan değiştirme':'appearance','change background':'appearance',
      'Sistemden atıyor cloud kopuyor':'cloud','cloud disconnected':'cloud',
      'Excel içe aktarma':'import','import spreadsheet':'import',
      'İndirim nasıl yapılır':'discount','bulk price update':'price',
      'Abonelik ne zaman bitecek':'subscription','support email failed':'support',
    }
    for question,key in questions.items():assert key in lookup(question),(question,lookup(question),key)
    assert lookup('Mars gezegeninde hava nasıl')==()
    assert len(lookup('transfer ve rezervasyon'))==2
    assert len(TOPICS)==len(BY_KEY)
    for topic in TOPICS:
        assert topic.body and topic.body_en and topic.title_en
        assert all(action in ACTIONS for action in topic.actions)


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
