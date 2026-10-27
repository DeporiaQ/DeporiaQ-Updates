import json,sqlite3,time
from pathlib import Path
from types import SimpleNamespace
import pytest
from test_operations_ui import application,window
from test_commerce_ui import DATA
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from deporiaq_catalog import ProductEditor,ProductCatalogDialog,clean_barcode,expected_product
from deporiaq_commerce_ui import ServerDialog
from deporiaq_commerce import CommerceClient
from stok_programi_v2 import Veritabani

class CatalogClient:
    def __init__(self,role='owner'):
        self.cloud=SimpleNamespace(role=role);self.calls=[]
        self.data=json.loads(json.dumps(DATA))
        self.data['products'][0].update(sale_price=100,purchase_price=60,critical_stock=3)
        self.data['products'].append(dict(self.data['products'][0],id='unused',name='Empty card',barcode='0002'))
    def snapshot(self):return self.data
    def mutate(self,action,payload):self.calls.append((action,payload));return {'id':payload.get('product_id','new-id')}

def test_catalog_shows_empty_products_and_edit_preserves_id(application,window,monkeypatch):
    monkeypatch.setattr(ServerDialog,'run',lambda self,fn,done=None:done(fn()) if done else fn())
    client=CatalogClient();dialog=ProductCatalogDialog(client,window);dialog.show();application.processEvents()
    assert dialog.grid.rowCount()==2
    dialog.search.setText('Empty');assert dialog.grid.rowCount()==1
    dialog.grid.selectRow(0);assert dialog.edit_button.isEnabled() and dialog.delete_button.isEnabled()
    product=client.data['products'][0];editor=ProductEditor(client,product,dialog)
    assert editor.barcode.text()==product['barcode'] and editor.sale.value()==100 and editor.cost.value()==60 and editor.critical.value()==3
    editor.barcode.setText('0003\n');editor.name.setText('Corrected');editor.save()
    assert client.calls[-1][1]['product_id']=='p' and client.calls[-1][1]['barcode']=='0003'
    assert client.calls[-1][1]['expected']==expected_product(product)
    assert editor.saved=='p'
    out=Path(__file__).resolve().parents[1]/'test-results';out.mkdir(exist_ok=True)
    assert dialog.grab().save(str(out/'0271-catalog.png'));dialog.close()

def test_catalog_viewer_cannot_change_and_editor_retains_failed_input(application,window):
    client=CatalogClient('viewer');dialog=ProductCatalogDialog(client,window)
    for _ in range(60):
        application.processEvents()
        if dialog.job is None:break
        QTest.qWait(10)
    dialog.grid.selectRow(0)
    assert not any(b.isEnabled() for b in [dialog.create_button,dialog.edit_button,dialog.delete_button,dialog.archive_button,dialog.restore_button])
    dialog.close()
    client=CatalogClient();client.mutate=lambda *args:(_ for _ in ()).throw(RuntimeError('DPQ_CONFLICT'))
    editor=ProductEditor(client,client.data['products'][0],window);editor.show();editor.name.setText('My correction');editor.save()
    for _ in range(60):
        application.processEvents()
        if editor.job is None:break
        QTest.qWait(10)
    assert editor.isVisible() and editor.name.text()=='My correction' and 'DPQ_CONFLICT' in editor.status_label.text()
    editor.close()

def test_barcode_keeps_leading_zeroes_and_rejects_hidden_characters():
    assert clean_barcode(' 00123\r\n')=='00123'
    for value in ['','12 34','12\n34','12\u200b34','12\x0034']:
        with pytest.raises(ValueError):clean_barcode(value)

def test_duplicate_names_cache_rename_archive_and_delete(tmp_path):
    db=Veritabani(tmp_path/'cache.db');db.ilk_kurulumu_tamamla('TEST','Books','Merkez Depo','TL','TEST','Fixture!Password2026')
    client=CommerceClient(SimpleNamespace(vt=db,company_id='company',cihaz_kimligi='device'))
    p={'id':'a','barcode':'001','name':'Same name','sale_price':100,'purchase_price':60,'critical_stock':0,'active':True}
    data={'products':[p,dict(p,id='b',barcode='002')],'locations':[{'id':'l','name':'Merkez Depo','location_type':'center','active':True}],
      'inventory':[{'product_id':'a','location_id':'l','quantity':10,'available':10}],'sales':[]}
    client.snapshot=lambda:data;client.sync_cache()
    local_id=db.baglanti.execute("select id from urunler where barkod='001'").fetchone()[0]
    p['barcode']='003';data['catalog_aliases']=[{'id':'a','barcode':'001'}];client.sync_cache()
    assert db.baglanti.execute("select id from urunler where barkod='003'").fetchone()[0]==local_id
    assert db.baglanti.execute('select sum(miktar) from stoklar').fetchone()[0]==10
    p['active']=False;data['inventory']=[];data['products']=[p];client.sync_cache()
    assert db.baglanti.execute('select count(*) from urunler where aktif=1').fetchone()[0]==0
    assert db.baglanti.execute('select sum(miktar) from stoklar').fetchone()[0]==0
    assert db.baglanti.execute('select count(*) from senkron_kuyrugu').fetchone()[0]==0
    db.kapat()

def test_legacy_name_constraint_migration_preserves_rows_and_relations(tmp_path):
    path=tmp_path/'legacy.db';db=sqlite3.connect(path)
    db.executescript("CREATE TABLE urunler(id INTEGER PRIMARY KEY AUTOINCREMENT,barkod TEXT NOT NULL UNIQUE,ad TEXT NOT NULL UNIQUE,fiyat REAL NOT NULL CHECK(fiyat>=0),aktif INTEGER NOT NULL DEFAULT 1); INSERT INTO urunler VALUES(17,'001','Old',10,1);")
    db.commit();db.close();vt=Veritabani(path)
    assert vt.baglanti.execute('select ad from urunler where id=17').fetchone()[0]=='Old'
    vt.baglanti.execute("insert into urunler(barkod,ad,fiyat) values('002','Old',12)");vt.baglanti.commit()
    assert not vt.baglanti.execute('pragma foreign_key_check').fetchall()
    assert vt.baglanti.execute('pragma foreign_keys').fetchone()[0]==1
    assert path.with_name('legacy.before-0.27.1.db').exists()
    assert len(vt.baglanti.execute("select name from sqlite_master where type='trigger' and tbl_name='urunler'").fetchall())==2
    vt.kapat();vt=Veritabani(path);assert vt.baglanti.execute('select count(*) from urunler').fetchone()[0]==2;vt.kapat()

def test_companion_stays_seated_and_food_and_signs_persist(window):
    pet=window.companion;pet.timer.stop();pet.state.last_fed=0
    assert 'Acıktım' in str(pet.message())
    pet.feed();assert pet.mode=='eat';pet.mode_until=0;pet.tick()
    assert pet.mode=='happy' and not pet.state.hungry()
    pet.mode_until=0;pet.tick();assert pet.mode=='idle'
    pet.set_mode('sleep',1);assert pet.mode=='idle'
    pet.state.messages=False;pet.save();assert json.loads(window.vt.ayar_getir(pet.key))['messages'] is False

def test_guide_knows_delete_edit_and_archive():
    from deporiaq_assistant_guide import lookup
    for query,key in [('bir ürünü silmek istiyorum','product_delete'),('Barkod düzelt','product_edit'),('Ürün arşivle','product_archive')]:assert key in lookup(query)

def test_sidebar_keeps_companion_visible_at_small_window(application,window):
    from PySide6.QtWidgets import QWidget
    from PySide6.QtCore import QPoint,QRect
    pet=window.companion;pet.timer.stop()
    # Exercise the widget layout without requiring an offscreen 3D renderer.
    pet.view=QWidget(window.companion_host);pet.state.size=240;pet.apply()
    window.resize(1000,720);window.show();application.processEvents();pet.home()
    assert pet.dock.isHidden()
    for widget in (pet.view,window.language_flags['tr'],window.support_mail):
        assert window.rect().contains(QRect(widget.mapTo(window,QPoint()),widget.size()))
        assert not widget.visibleRegion().isEmpty()
    assert pet.view.parentWidget().rect().contains(pet.view.geometry())
    assert window.menu_kaydir.verticalScrollBar().maximum()>0

def test_companion_sign_resolves_selected_language(window):
    from deporiaq_i18n import set_language,render
    pet=window.companion;pet.timer.stop();pet.mode='idle';pet.message_index=1
    try:
        set_language('en');assert render(pet.message())=='You can rename me in Settings.'
    finally:set_language('tr')
