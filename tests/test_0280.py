import copy,time,json,ast
from decimal import Decimal
from pathlib import Path
import pytest
from PySide6.QtCore import Qt,QRect,QPoint,QTimer
from PySide6.QtTest import QTest
from test_operations_ui import application,window
from retail_fixture import fixture
from deporiaq_retail_model import warehouse_scene,free_shelves,find_products,offer_totals
from deporiaq_retail_ui import OffersDialog,CustomersDialog,FinanceDialog,LocationsDialog
from deporiaq_warehouse import WarehouseDialog,LayoutEditor,PlacementDialog
from deporiaq_commerce_ui import ServerDialog
from deporiaq_panels import PanelsDialog

def wait_job(app,widget):
    until=time.monotonic()+4
    while time.monotonic()<until:
        app.processEvents();QTest.qWait(20)
        if widget.job is None:return
    raise AssertionError('UI job did not finish')

@pytest.fixture
def retail(window,monkeypatch):
    hub=window.retail_hub;data=fixture();hub.timer.stop();calls=[]
    def read(action,payload=None):
        payload=payload or {};calls.append((action,copy.deepcopy(payload)))
        if action=='retail_snapshot':return data
        if action=='retail_customers':return []
        if action=='retail_finance':return {'totals':dict(sales=1200,returns=100,revenue=1100,cost=600,expenses=80,missing_cost_lines=0),'rows':[dict(period='2026-10-25',location='Örnek Şube',channel_name='Mağaza / Doğrudan',revenue=1100,cost=600)],'expenses':[]}
        if action=='retail_quote':return dict(fingerprint='fixture-price',total=120*sum(x['quantity'] for x in payload['items']),lines=[dict(product_id=x['product_id'],quantity=x['quantity'],price=120,bundle_id=None) for x in payload['items']])
        raise AssertionError(action)
    monkeypatch.setattr(hub.client,'read',read);hub.accept(data)
    return hub,data,calls

def test_grid_has_uniform_gaps_and_no_overlap(application,window):
    window.resize(1600,1000);window.show();application.processEvents();canvas=window.panel_canvas
    def verify():
        visible=[p for p in canvas.panels.values() if not p.isHidden()]
        for i,a in enumerate(visible):
            for b in visible[i+1:]:assert not a.geometry().intersects(b.geometry())
        a=canvas.panels['products'];b=canvas.panels['stock'];assert b.x()-(a.x()+a.width())==canvas.GAP
    verify();window.resize(1250,850);application.processEvents();verify()
    panel=canvas.panels['users'];other={k:p.geometry() for k,p in canvas.panels.items() if p is not panel}
    canvas.place(panel,QRect(0,0,400,220));canvas.remember(panel);verify()
    assert other=={k:p.geometry() for k,p in canvas.panels.items() if p is not panel}
    assert all(canvas.panels['retail_'+k].isHidden() for k in window.retail_hub.panels)
    canvas.set_visible('retail_warehouse',True);verify();canvas.reset()
    assert canvas.panels['retail_warehouse'].isHidden()

def test_hidden_panels_open_without_pinning(application,window,monkeypatch):
    canvas=window.panel_canvas;panel=canvas.panels['retail_accounts'];opened=[]
    canvas.openers['retail_accounts']=lambda:opened.append(True)
    canvas.open_panel('retail_accounts');assert opened and panel.isHidden()
    dialog=PanelsDialog(canvas,window);dialog.show();application.processEvents();assert len(dialog.checks)==16;dialog.close()

def test_warehouse_geometry_and_lookup_are_based_on_actual_assignments():
    data=fixture();layout=data['layouts'][0];scene=warehouse_scene(layout,data['shelves'],data['products'])
    assert 0<scene['occupancy']<100 and scene['placed']==sum(x['quantity'] for x in data['shelves'])
    assert len(scene['labels'])==20 and all(x['w']>0 and x['h']>0 and x['d']>0 for x in scene['parts'])
    matches=find_products(data['products'],'olasiliksiz');assert len(matches)==1 and matches[0]['name']=='Olasılıksız'
    assert find_products(data['products'],data['products'][0]['barcode'])==matches
    assert free_shelves(layout,data['shelves'],80,2) and not free_shelves(layout,data['shelves'],81,2)
    highlight=warehouse_scene(layout,data['shelves'],data['products'],matches[0]['id']);assert any(x['color']=='#35d8d1' for x in highlight['parts'])
    normal,total,cost=offer_totals(data['products'],[{'product_id':matches[0]['id'],'quantity':20}],10)
    assert (normal,total,cost)==(Decimal(2400),Decimal(2160),Decimal(1400))

def test_barcode_repeat_quantity_and_authoritative_quote(application,window,retail):
    hub,data,calls=retail;pane=hub.panels['pos'];code=data['products'][0]['barcode'];pane.lines=[]
    pane.barcode.setText(code);pane.add();pane.barcode.setText(code);pane.add();pane.qty.setValue(3);pane.barcode.setText('olasılıksız');pane.add()
    assert len(pane.lines)==1 and pane.lines[0]['quantity']==5
    pane.debounce.stop();pane.request_quote();wait_job(application,pane);assert pane.quote['total']==600
    assert pane.sell_button.isEnabled();pane.fill('card');assert pane.card.value()==600
    payload=pane.payload();assert payload['items'][0]['quantity']==5 and payload['location_id']==data['locations'][0]['id']
    pane.debounce.stop();pane.lines=[];pane.quote=None;pane.persist()

def test_stale_async_quote_cannot_enable_checkout(application,window,retail):
    hub,data,calls=retail;pane=hub.panels['pos'];code=data['products'][0]['barcode']
    pane.barcode.setText(code);pane.add();pane.debounce.stop();pane.request_quote()
    pane.barcode.setText(code);pane.add();wait_job(application,pane)
    assert not pane.sell_button.isEnabled() and pane.quote is None
    pane.debounce.stop();pane.request_quote();wait_job(application,pane);assert pane.quote['total']==240
    pane.lines=[];pane.quote=None;pane.persist()

def test_editors_reports_and_light_theme_render(application,window,retail):
    hub,data,calls=retail;window.show();out=Path('test-results/0280');out.mkdir(parents=True,exist_ok=True)
    window.toggle_mode();application.processEvents();window.grab().save(str(out/'light-dashboard.png'))
    dialogs=[OffersDialog(hub,False,window),OffersDialog(hub,True,window),CustomersDialog(hub,window),FinanceDialog(hub,window),WarehouseDialog(hub,window),LayoutEditor(hub.client,data['locations'][0]['id'],data['layouts'][0],window),PlacementDialog(hub.client,data['layouts'][0],data,None,window),LocationsDialog(hub,window)]
    for n,dialog in enumerate(dialogs):
        dialog.show();application.processEvents();wait_job(application,dialog)
        if isinstance(dialog,OffersDialog):dialog.name.setText('Örnek Kampanya' if not dialog.bundle else 'Polisiye Seti');dialog.add();dialog.remember_saved()
        dialog.grab().save(str(out/f'panel-{n}.png'));dialog.close();dialog.deleteLater()
    window.toggle_mode()
    assert not hub.panels['pos'].lines
