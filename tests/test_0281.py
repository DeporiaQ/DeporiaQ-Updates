from pathlib import Path
from PySide6.QtQuickWidgets import QQuickWidget
from test_operations_ui import application,window
from test_0280 import retail,wait_job
from deporiaq_positions import PositionsDialog,AuthorityDialog
from deporiaq_retail_ui import OffersDialog

def test_text_addresses_search_and_no_3d(application,window,retail,monkeypatch):
    hub,data,calls=retail
    data['positions']=[dict(id='position',version=1,product_id=data['products'][0]['id'],location_id=data['locations'][0]['id'],floor='2. Kat',area='L koridoru',shelf='Polisiye A',compartment='Üst göz',note='Merdivenin solu')]
    d=PositionsDialog(hub,window);d.show();application.processEvents()
    assert not d.findChildren(QQuickWidget)
    d.query.setText(data['products'][0]['barcode']);assert d.grid.rowCount()==1
    assert d.grid.item(0,3).text()=='2. Kat'
    d.query.setText('no-such-book');assert d.grid.rowCount()==0
    d.query.clear();d.select(0,0);assert d.fields['shelf'].text()=='Polisiye A'
    out=Path('test-results/0281');out.mkdir(parents=True,exist_ok=True);d.grab().save(str(out/'product-locations.png'));d.close()
    assert window.pet_dock.isHidden()
    assert not hub.panels['warehouse'].findChildren(QQuickWidget)

def test_offer_delete_and_authority_form(application,window,retail,monkeypatch):
    hub,data,calls=retail
    d=OffersDialog(hub,False,window);d.show();wait_job(application,d)
    assert d.delete_button.isEnabled();d.delete_offer();assert 'seçin' in d.status_label.text();d.close()
    old_read=hub.client.read
    def read(action,payload=None):
        if action=='retail_team':return {'members':[{'user_id':'owner','name':'Owner','base_role':'owner','effective_role':'owner','delegation':None},{'user_id':'staff','name':'Staff','base_role':'employee','effective_role':'admin','delegation':{'version':1,'expires_at':'2099-01-01T00:00:00+00:00'}}]}
        return old_read(action,payload)
    monkeypatch.setattr(hub.client,'read',read)
    a=AuthorityDialog(hub,window);a.show();wait_job(application,a)
    assert a.user.count()==1 and a.user.currentData()['user_id']=='staff'
    assert a.temporary.isChecked() and a.end.isEnabled() and a.role.currentData()=='admin'
    out=Path('test-results/0281');out.mkdir(parents=True,exist_ok=True);a.grab().save(str(out/'authority.png'));a.close()
