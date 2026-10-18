import json
import time
from pathlib import Path
import pytest
from test_operations_ui import application,window,ui
from PySide6.QtCore import Qt,QPoint,QEvent
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QDialog,QComboBox,QWidget
from PySide6.QtTest import QTest
from deporiaq_panels import PanelCanvas
from deporiaq_companion import PetState
from deporiaq_onboarding import RegistrationClient,validated_payment_url,CheckoutDialog

def test_panels_drag_resize_hide_without_reflow_and_persist(application,window):
    window.resize(1500,950);window.show();QTest.qWait(120);application.processEvents()
    canvas=window.panel_canvas;keys=list(canvas.panels);panel=canvas.panels[keys[-1]]
    others={k:p.geometry() for k,p in canvas.panels.items() if p is not panel}
    original=panel.geometry();start=panel.bar.rect().center()
    QTest.mousePress(panel.bar,Qt.MouseButton.LeftButton,pos=start)
    QTest.mouseMove(panel.bar,start+QPoint(-50,-40));QTest.mouseRelease(panel.bar,Qt.MouseButton.LeftButton,pos=start)
    assert panel.geometry()!=original
    moved=panel.geometry();corner=panel.corner
    QTest.mousePress(corner,Qt.MouseButton.LeftButton,pos=QPoint(5,5));QTest.mouseMove(corner,QPoint(35,35));QTest.mouseRelease(corner,Qt.MouseButton.LeftButton,pos=QPoint(5,5))
    assert panel.width()>=moved.width() and panel.height()>=moved.height()
    assert others=={k:p.geometry() for k,p in canvas.panels.items() if p is not panel}
    canvas.set_visible(panel.key,False);window.yenile();application.processEvents()
    assert panel.isHidden() and panel.content.parentWidget() is panel
    assert others=={k:p.geometry() for k,p in canvas.panels.items() if p is not panel}
    saved=json.loads(window.vt.ayar_getir(canvas.key));assert saved[panel.key]['visible'] is False
    restored=PanelCanvas(window);restored.resize(canvas.size());copy=restored.add(panel.key,panel.title,QWidget(),canvas.defaults[panel.key],panel.minimum)
    assert copy.isHidden() and copy.geometry()==panel.geometry();restored.deleteLater()
    canvas.set_locked(True);locked=panel.geometry();panel.show()
    QTest.mousePress(panel.bar,Qt.MouseButton.LeftButton,pos=start);QTest.mouseMove(panel.bar,start+QPoint(-80,-60));QTest.mouseRelease(panel.bar,Qt.MouseButton.LeftButton,pos=start)
    assert panel.geometry()==locked
    canvas.reset();assert all(not p.isHidden() for p in canvas.panels.values())

def test_compact_assistant_does_not_resize_dashboard(application,window):
    window.resize(1366,768);window.show();application.processEvents();size=window.kaydir.viewport().size()
    window.assistant_open();application.processEvents();panel=window.assistant_panel
    assert window.kaydir.viewport().size()==size
    assert panel.width()<=430 and panel.height()<=530
    assert not panel.findChildren(QComboBox) and panel.messages_layout.count()==1
    panel.close()

def test_companion_remembers_food_name_and_hunger_without_clock_cheats():
    state=PetState(now=1000);assert not state.hungry(4599) and state.hungry(4600)
    state.food=True;state.name='Pamuk';saved=PetState(state.export(),now=4600)
    assert saved.name=='Pamuk' and saved.food and saved.eat(4600)
    assert not saved.food and not saved.hungry(4601) and not saved.eat(4601)
    assert PetState({'last_fed':float('nan')},now=10).last_fed==10
    assert PetState({'last_fed':999},now=10).last_fed==10

def test_cancelled_close_keeps_companion_alive(application,window):
    class RefuseClose(ui.QDialog):
        def closeEvent(self,event):event.ignore()
    window.show();dialog=RefuseClose(window);dialog.show();application.processEvents()
    event=QCloseEvent();window.closeEvent(event)
    assert not event.isAccepted() and window.companion.timer.isActive()
    dialog.hide();dialog.deleteLater()

def test_registration_uses_verified_session_and_never_supplies_company_or_role(window,monkeypatch):
    cloud=window.cloud_client;client=RegistrationClient(cloud);calls=[]
    def request(path,method,payload,**kw):
        calls.append((path,payload,kw))
        if path.endswith('/verify'):return {'access_token':'test-token','refresh_token':'test-refresh','user':{'id':'verified-user'}}
        return {'company_id':'created-on-server'}
    monkeypatch.setattr(cloud,'_istek',request)
    with pytest.raises(ValueError):client.signup('bad','short')
    for password in ('Short!123', 'lowercaseonly12345', 'LongPassword! 2026'):
        with pytest.raises(ValueError):client.signup('test@example.invalid',password)
    assert not calls
    client.signup('test@example.invalid','LongPassword!2026');client.verify('test@example.invalid','123456');client.enroll('My Store')
    assert calls[-1][1]=={'p_name':'My Store'} and cloud.user_id=='verified-user'
    assert calls[0][2]['auth'] is False
    assert all('role' not in payload and 'company_id' not in payload for _,payload,_ in calls)
    cloud.cikis_yap()

def test_payment_browser_only_accepts_provider_hosts():
    assert validated_payment_url('https://payment.iyzipay.com/pay?token=abc','live')
    for url in ['https://payment.iyzipay.com.evil.test/pay','https://evil.test/','file:///tmp/file','http://payment.iyzipay.com/pay','https://user@payment.iyzipay.com/pay','https://sandbox-payment.iyzipay.com/pay']:
        with pytest.raises(ValueError):validated_payment_url(url,'live')

def test_checkout_is_closed_without_catalog_configuration(application,window,monkeypatch):
    monkeypatch.setattr(window.cloud_client,'_istek',lambda *a,**kw:{'enabled':False,'can_buy':True,'offers':[],'environment':'sandbox'})
    dialog=CheckoutDialog(window.cloud_client,window);dialog.show()
    for _ in range(50):
        application.processEvents()
        if dialog.job is None:break
        QTest.qWait(10)
    assert dialog.job is None and not dialog.pay.isEnabled() and not dialog.offers
    dialog.close()

def test_guide_question_forms_are_not_miscounted_as_topics():
    from deporiaq_assistant_guide import TOPICS,GUIDE_INDEX,lookup
    from deporiaq_assistant import ACTIONS
    root=Path(__file__).resolve().parents[1]
    assert GUIDE_INDEX.question_count>=1000 and GUIDE_INDEX.topic_count==len(TOPICS)
    assert GUIDE_INDEX.topic_count<GUIDE_INDEX.question_count
    for topic in TOPICS:
        assert (root/topic.source).is_file(),topic.source
        assert all(a in ACTIONS for a in topic.actions)
        for question in GUIDE_INDEX.questions[topic.key]:assert topic.key in lookup(question),(topic.key,question)

def test_guide_handles_specific_problems_and_declines_unrelated_questions():
    from deporiaq_assistant_guide import lookup
    pairs={
      'Paneli büyütmek istiyorum':'panel_resize','Kediye mama ver':'pet_feed',
      'Kedinin ismini nasıl değiştirebilirim':'pet_name','Kediyi gizlemek istiyorum':'pet_hide',
      'DPQ_CONFLICT hatası aldım':'edit_conflict','Excel formül kabul etmiyor':'import_formula',
      'Barkodun başındaki sıfır kayboldu':'import_zero','Nakit kart toplamı uyuşmuyor':'payment_split',
      'Stok tükenme tahmini kesin mi':'analysis_runway','What does gross net profit mean':'analysis_profit',
      'How do I archive a channel':'channel_archive','I need to resize a panel':'panel_resize',
      'feed the cat':'pet_feed','What is the device limit':'device_limit',
    }
    for question,key in pairs.items():assert key in lookup(question),(question,lookup(question))
    for question in ['Mars gezegeninde yağmur yağar mı','Write a romantic poem','', 'a'*2001]:assert lookup(question)==()

def test_guide_index_scales_to_more_than_one_thousand_authored_records():
    from dataclasses import replace
    from deporiaq_assistant_guide import TOPICS,fold
    from deporiaq_knowledge_index import GuideIndex
    # Synthetic capacity fixture, never shipped as purported product knowledge.
    cards=[replace(TOPICS[0],key=f'fixture_{i}',title=f'Deneme işlem {i}',title_en=f'Fixture operation {i}',phrases=(f'fixture{i}',)) for i in range(1500)]
    index=GuideIndex(cards,fold);started=time.monotonic()
    assert index.lookup('Help me with Fixture operation 1499')==('fixture_1499',)
    assert index.lookup('fixture1499')==('fixture_1499',)
    assert time.monotonic()-started<1.5
