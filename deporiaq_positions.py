"""Manual product addresses and server-backed, time-limited role delegation."""
from datetime import datetime,timezone
from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import QHBoxLayout,QFormLayout,QDateTimeEdit
from deporiaq_i18n import T,QLabel,QLineEdit,QComboBox,QCheckBox,QMessageBox
from deporiaq_commerce_ui import ServerDialog,table,rows
from deporiaq_workspace_ui import EditableDialog
from deporiaq_retail_model import find_products

class PositionsDialog(EditableDialog):
    def __init__(self,hub,parent=None):
        super().__init__(hub.client,T('Ürün Konumları'),parent);self.hub=hub;self.data={};self.record=None;self.records=[];self.resize(1100,760)
        row=QHBoxLayout();self.query=QLineEdit();self.query.setPlaceholderText(T('Barkod veya ürün adı yazın…'));self.location=QComboBox();row.addWidget(self.query,2);row.addWidget(self.location,1);self.body.addLayout(row)
        self.info=QLabel(T('Yalnız personelin kaydettiği konumlar gösterilir. Kat ve bölüm adları serbesttir; bina şekli veya ölçü gerekmez.'));self.info.setWordWrap(True);self.body.addWidget(self.info)
        self.grid=table([T('Ürün'),T('Barkod'),T('Depo / Şube'),T('Bina Katı'),T('Bölüm'),T('Raf'),T('Göz / Kat'),T('Not')]);self.body.addWidget(self.grid,1);self.grid.cellClicked.connect(self.select)
        self.address=QLabel();self.address.setWordWrap(True);self.body.addWidget(self.address)
        form=QFormLayout();self.product=QComboBox();self.product.setEditable(True);self.product.setInsertPolicy(QComboBox.InsertPolicy.NoInsert);self.destination=QComboBox();form.addRow(T('Ürün'),self.product);form.addRow(T('Depo / Şube'),self.destination)
        self.fields={}
        for key,label in [('floor','Bina Katı'),('area','Bölüm'),('shelf','Raf'),('compartment','Göz / Kat'),('note','Not')]:
            w=QLineEdit();w.setMaxLength(100 if key=='shelf' else 500);self.fields[key]=w;form.addRow(T(label),w)
        self.body.addLayout(form);row=QHBoxLayout();self.button(T('Yeni Konum'),self.new,row);self.save_button=self.button(T('Kaydet'),self.save,row);self.delete_button=self.button(T('Konumu Sil'),self.remove,row);self.button(T('Yenile'),hub.refresh,row);self.body.addLayout(row)
        self.query.textChanged.connect(self.render);self.location.currentIndexChanged.connect(self.render);hub.updated.connect(self.loaded);self.loaded(hub.data);hub.refresh();self.remember_saved()
    def form_state(self):return (self.product.currentData(),self.destination.currentData(),tuple(w.text() for w in self.fields.values()))
    def loaded(self,data):
        if not data:return
        self.data=data
        for combo,entries,blank in [(self.location,data.get('locations',[]),True),(self.destination,data.get('locations',[]),False),(self.product,data.get('products',[]),False)]:
            before=combo.currentData();combo.blockSignals(True);combo.clear()
            if blank:combo.addItem(T('Tüm depo ve şubeler'),None)
            for e in entries:
                if e.get('active',True):combo.addItem((e.get('barcode','')+' · ' if combo is self.product else '')+e['name'],e['id'])
            if before:combo.setCurrentIndex(max(0,combo.findData(before)))
            combo.blockSignals(False)
        allowed=data.get('capabilities',{}).get('layout',False)
        for w in [self.product,self.destination,*self.fields.values(),self.save_button,self.delete_button]:w.setEnabled(allowed)
        self.render()
    def render(self,*args):
        products={p['id']:p for p in self.data.get('products',[])};locations={l['id']:l['name'] for l in self.data.get('locations',[])}
        found={p['id'] for p in find_products(list(products.values()),self.query.text())}
        self.records=[x for x in self.data.get('positions',[]) if (not self.query.text().strip() or x['product_id'] in found) and (not self.location.currentData() or x['location_id']==self.location.currentData())]
        rows(self.grid,[(products.get(x['product_id'],{}).get('name',''),products.get(x['product_id'],{}).get('barcode',''),locations.get(x['location_id'],''),x['floor'],x['area'],x['shelf'],x['compartment'],x['note']) for x in self.records])
        self.status_label.setText(T('Kayıtlı konum bulunamadı.') if not self.records else '')
    def select(self,row,col):
        if not self.may_switch():return
        self.record=self.records[row];self.address.setText(' → '.join(str(self.record.get(k,'')) for k in ('floor','area','shelf','compartment','note') if self.record.get(k)));self.product.setCurrentIndex(self.product.findData(self.record['product_id']));self.destination.setCurrentIndex(self.destination.findData(self.record['location_id']))
        for k,w in self.fields.items():w.setText(self.record[k])
        self.remember_saved()
    def new(self):
        if not self.may_switch():return
        self.record=None
        for w in self.fields.values():w.clear()
        self.remember_saved()
    def save(self):
        pid=self.product.currentData()
        if self.product.currentText()!=self.product.itemText(self.product.currentIndex()):
            matches=find_products(self.data.get('products',[]),self.product.currentText())
            if len(matches)!=1:self.status_label.setText(T('Ürünü listeden seçin veya tam barkodunu girin.'));return
            pid=matches[0]['id']
        data={k:w.text().strip() for k,w in self.fields.items()};data.update(product_id=pid,location_id=self.destination.currentData());payload={'data':data}
        if self.record:payload.update(id=self.record['id'],version=self.record['version'])
        self.mutation('retail_position_save',payload,self.saved)
    def saved(self,result):self.record=result;self.saved_ok();self.hub.refresh()
    def remove(self):
        if not self.record:return
        if QMessageBox.question(self,T('Konumu Sil'),T('Bu adres kaydı silinsin mi? Ürün ve stok miktarı değişmez.'))!=QMessageBox.StandardButton.Yes:return
        self.mutation('retail_position_delete',{'id':self.record['id'],'version':self.record['version']},lambda _:self.deleted())
    def deleted(self):self.remember_saved();self.new();self.hub.refresh()

class AuthorityDialog(ServerDialog):
    def __init__(self,hub,parent=None):
        super().__init__(hub.client,T('Kullanıcı Rolleri ve Yetki Devri'),parent);self.hub=hub;self.members=[];self.resize(1000,700)
        note=QLabel(T('Ana yönetici kimliği sabittir. Yönetici rolü işletme işlemlerini yürütür; hesap sahipliği, abonelik satın alma ve başkasına yetki verme ana yöneticide kalır. Geçici rol sona erince önceki rol geçerli olur.'));note.setWordWrap(True);self.body.addWidget(note)
        self.grid=table([T('Kullanıcı'),T('Asıl rol'),T('Geçerli rol'),T('Bitiş')]);self.body.addWidget(self.grid,1)
        self.user=QComboBox();self.role=QComboBox()
        for key,label in [('admin','Yönetici'),('manager','Operasyon Sorumlusu'),('employee','Personel'),('warehouse','Depo Personeli'),('branch','Şube Personeli'),('viewer','Görüntüleyici')]:self.role.addItem(T(label),key)
        self.temporary=QCheckBox(T('Geçici yetki'));self.end=QDateTimeEdit(QDateTime.currentDateTime().addDays(1));self.end.setCalendarPopup(True);self.end.setDisplayFormat('dd.MM.yyyy HH:mm');self.end.setEnabled(False);self.temporary.toggled.connect(self.end.setEnabled)
        form=QFormLayout();form.addRow(T('Kullanıcı'),self.user);form.addRow(T('Rol'),self.role);form.addRow(self.temporary);form.addRow(T('Bitiş (bu bilgisayarın saati)'),self.end);self.body.addLayout(form)
        row=QHBoxLayout();self.button(T('Yetkiyi Kaydet'),self.save,row);self.button(T('Yetki Devrini Kaldır'),self.revoke,row);self.body.addLayout(row);self.user.currentIndexChanged.connect(self.select);self.refresh()
    def refresh(self):self.run(lambda:self.client.read('retail_team'),self.loaded)
    def loaded(self,data):
        self.members=data['members'];self.user.blockSignals(True);self.user.clear()
        for m in self.members:
            if m['base_role']!='owner':self.user.addItem(m['name']+' · '+m['user_id'][:8],m)
        self.user.blockSignals(False);rows(self.grid,[(m['name'],self.label(m['base_role']),self.label(m['effective_role']),(m.get('delegation') or {}).get('expires_at') or T('Süresiz')) for m in self.members]);self.select()
    def label(self,key):return T('Ana Yönetici') if key=='owner' else self.role.itemText(self.role.findData(key))
    def select(self,*args):
        m=self.user.currentData()
        if not m:return
        d=m.get('delegation') or {};self.role.setCurrentIndex(max(0,self.role.findData(m['effective_role'])));self.temporary.setChecked(bool(d.get('expires_at')))
        if d.get('expires_at'):self.end.setDateTime(QDateTime.fromSecsSinceEpoch(int(datetime.fromisoformat(d['expires_at'].replace('Z','+00:00')).timestamp())))
    def submit(self,revoke=False):
        m=self.user.currentData()
        if not m:return
        payload={'user_id':m['user_id'],'version':(m.get('delegation') or {}).get('version',0),'revoke':revoke,'role':self.role.currentData(),'expires_at':datetime.fromtimestamp(self.end.dateTime().toSecsSinceEpoch(),timezone.utc).isoformat() if self.temporary.isChecked() else None}
        if QMessageBox.question(self,T('Yetki Değişikliği'),T('Seçili kullanıcının sunucu yetkileri değiştirilsin mi?'))!=QMessageBox.StandardButton.Yes:return
        self.mutation('retail_role_save',payload,lambda _:self.refresh())
    def save(self):self.submit()
    def revoke(self):self.submit(True)
