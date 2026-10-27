"""Retail editors and reports. All business mutations use the checked retail RPC."""
from decimal import Decimal
from datetime import datetime,date,timedelta,timezone
from zoneinfo import ZoneInfo
import copy,csv
from PySide6.QtCore import Qt,QDate,QDateTime,QTimer
from PySide6.QtWidgets import (QHBoxLayout,QVBoxLayout,QFormLayout,QDoubleSpinBox,QSpinBox,
 QDateTimeEdit,QDateEdit,QListWidget,QAbstractItemView,QSplitter,QWidget,QTableWidgetItem,QGridLayout)
from deporiaq_i18n import T,render,QLabel,QPushButton,QLineEdit,QComboBox,QCheckBox,QMessageBox,QInputDialog,QFileDialog
from deporiaq_commerce_ui import ServerDialog,table,rows,csv_cell
from deporiaq_workspace_ui import EditableDialog
from deporiaq_retail_model import money,offer_totals

class OffersDialog(EditableDialog):
    def __init__(self,hub,bundle=False,parent=None):
        super().__init__(hub.client,T('Set ve Paketler') if bundle else T('Kampanyalar'),parent);self.hub=hub;self.bundle=bundle;self.record=None;self.items=[];self.data={};self.records=[];self.resize(1160,860)
        self.grid=table([T('Ad'),T('İndirim %'),T('Başlangıç'),T('Bitiş'),T('Durum')]);self.grid.setMaximumHeight(180);self.body.addWidget(self.grid);self.grid.cellClicked.connect(self.select)
        form=QFormLayout();self.name=QLineEdit();self.discount=QDoubleSpinBox();self.discount.setRange(.01,99.99);self.discount.setValue(10);self.discount.setSuffix(' %')
        self.starts=QDateTimeEdit(QDateTime.currentDateTime());self.ends=QDateTimeEdit(QDateTime.currentDateTime().addDays(3650 if bundle else 7))
        for field in (self.starts,self.ends):field.setCalendarPopup(True);field.setDisplayFormat('dd.MM.yyyy HH:mm')
        self.scope=QComboBox();self.active=QCheckBox(T('Etkin'));self.active.setChecked(True);self.member=QCheckBox(T('Yalnız üyeler yararlanabilir'))
        for label,widget in [(T('Ad'),self.name),(T('İndirim oranı'),self.discount),(T('Başlangıç (bu bilgisayarın saati)'),self.starts),(T('Bitiş (bu bilgisayarın saati)'),self.ends),(T('Kapsam'),self.scope)]:form.addRow(label,widget)
        row=QHBoxLayout();row.addWidget(self.active);row.addWidget(self.member);form.addRow(row);self.body.addLayout(form)
        self.product=QComboBox();self.product.setEditable(True);self.product.setInsertPolicy(QComboBox.InsertPolicy.NoInsert);self.qty=QSpinBox();self.qty.setRange(1,1000000);self.qty.setVisible(bundle)
        row=QHBoxLayout();row.addWidget(self.product,1);row.addWidget(self.qty);self.button(T('Ürün Ekle'),self.add,row);self.button(T('Seçili Ürünü Kaldır'),self.remove,row);self.body.addLayout(row)
        self.items_grid=table([T('Ürün'),T('Adet'),T('Normal toplam'),T('İndirimli toplam')]);self.body.addWidget(self.items_grid,1)
        self.preview=QLabel();self.preview.setWordWrap(True);self.body.addWidget(self.preview)
        note=QLabel(T('İndirimler üst üste eklenmez. Tek ürün için en yüksek uygun kampanya, set için yalnız set indirimi uygulanır. Süre ve maliyet satışta yeniden kontrol edilir.'));note.setWordWrap(True);self.body.addWidget(note)
        row=QHBoxLayout();self.button(T('Yeni'),self.new,row);self.save_button=self.button(T('Kaydet'),self.save,row);self.delete_button=self.button(T('Sil'),self.delete_offer,row);self.button(T('Yetkili Bilgisayarlar'),lambda:GrantsDialog(hub,self).exec(),row);self.body.addLayout(row)
        self.discount.valueChanged.connect(self.render_items);self.hub.updated.connect(self.loaded);self.loaded(hub.data)
        self.run(lambda:self.client.read('retail_snapshot'),hub.accept)
    def delete_offer(self):
        if not self.record:
            self.status_label.setText(T('Önce listeden silinecek kaydı seçin.'));return
        if QMessageBox.question(self,T('Kaydı Sil'),T('Seçili kampanya veya set silinsin mi? Geçmiş satış ve iade kayıtları korunur.'))!=QMessageBox.StandardButton.Yes:return
        self.mutation('retail_offer_delete',{'id':self.record['id'],'version':self.record['version']},self.deleted)
    def deleted(self,result):
        self.remember_saved();self.new();self.status_label.setText(T('Silindi. Geçmiş satış kayıtları korundu.'));self.hub.refresh()
    def form_state(self):return (self.name.text(),self.discount.value(),self.starts.dateTime().toSecsSinceEpoch(),self.ends.dateTime().toSecsSinceEpoch(),self.scope.currentData(),self.active.isChecked(),self.member.isChecked(),str(self.items))
    def loaded(self,data):
        if not data:return
        self.data=data;previous=self.scope.currentData();self.scope.clear();self.scope.addItem(T('Tüm depo ve şubeler'),None)
        for loc in data.get('locations',[]):
            if loc['active']:self.scope.addItem(loc['name'],loc['id'])
        if previous:self.scope.setCurrentIndex(max(0,self.scope.findData(previous)))
        self.product.clear()
        for p in data['products']:
            if p['active']:self.product.addItem(p['barcode']+' · '+p['name'],p['id'])
        self.records=[o for o in data.get('offers',[]) if o['kind']==('bundle' if self.bundle else 'campaign')]
        rows(self.grid,[(o['name'],o['discount'],o['starts_at'],o['ends_at'],T('Etkin') if o['active'] else T('Pasif')) for o in self.records])
        self.save_button.setEnabled(data.get('capabilities',{}).get('offers',False));self.delete_button.setEnabled(data.get('capabilities',{}).get('offers',False));self.render_items()
        if not hasattr(self,'_baseline'):self.remember_saved()
    def new(self):
        if not self.may_switch():return
        self.record=None;self.name.clear();self.items=[];self.active.setChecked(True);self.member.setChecked(False);self.discount.setValue(10);self.starts.setDateTime(QDateTime.currentDateTime());self.ends.setDateTime(QDateTime.currentDateTime().addDays(3650 if self.bundle else 7));self.render_items();self.remember_saved()
    def select(self,row,col):
        if not self.may_switch():return
        self.record=self.records[row];r=self.record;self.name.setText(r['name']);self.discount.setValue(float(r['discount']));self.items=copy.deepcopy(r['items']);self.active.setChecked(r['active']);self.member.setChecked(r['member_only'])
        for control,key in [(self.starts,'starts_at'),(self.ends,'ends_at')]:control.setDateTime(QDateTime.fromSecsSinceEpoch(int(datetime.fromisoformat(r[key].replace('Z','+00:00')).timestamp())))
        self.scope.setCurrentIndex(max(0,self.scope.findData(r['location_ids'][0] if r['location_ids'] else None)));self.render_items();self.remember_saved()
    def add(self):
        pid=self.product.currentData()
        if not pid:return
        item=next((x for x in self.items if x['product_id']==pid),None)
        if item:item['quantity']+=self.qty.value() if self.bundle else 0
        else:self.items.append({'product_id':pid,'quantity':self.qty.value() if self.bundle else 1})
        self.render_items()
    def remove(self):
        row=self.items_grid.currentRow()
        if row>=0:self.items.pop(row);self.render_items()
    def render_items(self,*args):
        products={p['id']:p for p in self.data.get('products',[])};display=[]
        try:
            for item in self.items:
                p=products[item['product_id']];normal,total,cost=offer_totals(self.data['products'],[item],self.discount.value());display.append((p['name'],item['quantity'],money(normal),money(total)))
            normal,total,cost=offer_totals(self.data.get('products',[]),self.items,self.discount.value())
            self.preview.setText(T('Normal: {normal} · İndirimli: {total} · Maliyet: {cost} · Brüt kâr: {profit}',normal=money(normal),total=money(total),cost=money(cost),profit=money(total-cost)))
            self.preview.setStyleSheet('color:#dc6574;' if total<cost else '')
        except KeyError:self.preview.setText(T('Tanımda bulunamayan ürün var. Ürün listesini yenileyin.'))
        rows(self.items_grid,display)
    def save(self):
        locations=[self.scope.currentData()] if self.scope.currentData() else []
        # Keep multi-location definitions intact unless the scope is deliberately changed.
        if self.record and self.scope.currentData()==(self.record['location_ids'][0] if self.record['location_ids'] else None):locations=self.record['location_ids']
        data=dict(kind='bundle' if self.bundle else 'campaign',name=self.name.text().strip(),items=self.items,discount=str(self.discount.value()),
                  starts_at=datetime.fromtimestamp(self.starts.dateTime().toSecsSinceEpoch(),timezone.utc).isoformat(),ends_at=datetime.fromtimestamp(self.ends.dateTime().toSecsSinceEpoch(),timezone.utc).isoformat(),
                  location_ids=locations,active=self.active.isChecked(),member_only=self.member.isChecked())
        payload={'data':data}
        if self.record:payload.update(id=self.record['id'],version=self.record['version'])
        self.mutation('retail_offer_save',payload,self.saved)
    def saved(self,result):
        self.record=result;self.saved_ok();self.status_label.setText(T('Kaydedildi.'));self.hub.refresh()

class CustomerPicker(ServerDialog):
    def __init__(self,client,parent=None):
        super().__init__(client,T('Müşteri Seç'),parent);self.chosen=None;self.records=[]
        self.query=QLineEdit();self.query.setPlaceholderText(T('Ad, telefon veya e-posta'));self.body.addWidget(self.query);self.query.returnPressed.connect(self.refresh);self.button(T('Ara'),self.refresh)
        self.grid=table([T('Ad'),T('Telefon'),T('Üyelik')]);self.body.addWidget(self.grid,1);self.grid.cellDoubleClicked.connect(self.select)
        self.button(T('Seç'),self.select);self.button(T('Müşterisiz Satış'),self.clear_customer);self.refresh()
    def refresh(self):self.run(lambda:self.client.read('retail_customers',{'query':self.query.text()}),self.loaded)
    def loaded(self,data):self.records=[x for x in data if x['active']];rows(self.grid,[(x['name'],x['phone'],T('Üye') if x['member'] else '—') for x in self.records])
    def select(self,*args):
        row=self.grid.currentRow()
        if row>=0:self.chosen=self.records[row];self.accept()
    def clear_customer(self):self.chosen={};self.accept()

class CustomersDialog(EditableDialog):
    def __init__(self,hub,parent=None):
        super().__init__(hub.client,T('Müşteriler ve Üyelik'),parent);self.hub=hub;self.record=None;self.records=[];self.offset=0;self.resize(1060,820)
        row=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText(T('Ad, telefon veya e-posta'));row.addWidget(self.search,1);self.button(T('Ara'),self.search_new,row);self.body.addLayout(row);self.search.returnPressed.connect(self.search_new)
        self.grid=table([T('Ad'),T('Telefon'),T('E-posta'),T('Üyelik'),T('İletişim izni')]);self.body.addWidget(self.grid,1);self.grid.cellClicked.connect(self.select)
        row=QHBoxLayout();self.button(T('Önceki'),lambda:self.page(-100),row);self.button(T('Sonraki'),lambda:self.page(100),row);self.body.addLayout(row)
        form=QFormLayout();self.name=QLineEdit();self.phone=QLineEdit();self.email=QLineEdit();self.note=QLineEdit();self.note.setPlaceholderText(T('İzin tarihi, yöntemi ve kanıt/kayıt açıklaması'))
        for label,widget in [(T('Ad Soyad'),self.name),(T('Telefon'),self.phone),(T('E-posta'),self.email),(T('İzin kaynağı'),self.note)]:form.addRow(label,widget)
        self.member=QCheckBox(T('Müşteri üyeliği kabul etti'));self.email_ok=QCheckBox(T('Kampanya e-postası izni'));self.sms_ok=QCheckBox(T('Kampanya SMS izni'));self.active=QCheckBox(T('Etkin müşteri'));self.active.setChecked(True)
        for widget in (self.member,self.email_ok,self.sms_ok,self.active):form.addRow(widget)
        self.body.addLayout(form);note=QLabel(T('Üyelik ve iletişim izinleri birbirinden ayrıdır. İzinler varsayılan olarak kapalıdır; müşteri vazgeçtiğinde işaretleri kaldırıp kaydedin. Bu ekran otomatik mesaj göndermez.'));note.setWordWrap(True);self.body.addWidget(note)
        row=QHBoxLayout();self.button(T('Yeni Müşteri'),self.new,row);self.save_button=self.button(T('Kaydet'),self.save,row);self.body.addLayout(row)
        self.save_button.setEnabled(hub.data.get('capabilities',{}).get('customers',False));self.remember_saved();self.refresh()
    def form_state(self):return (self.name.text(),self.phone.text(),self.email.text(),self.note.text(),self.member.isChecked(),self.email_ok.isChecked(),self.sms_ok.isChecked(),self.active.isChecked())
    def page(self,delta):self.offset=max(0,self.offset+delta);self.refresh()
    def search_new(self):self.offset=0;self.refresh()
    def refresh(self):self.run(lambda:self.client.read('retail_customers',{'query':self.search.text(),'offset':self.offset}),self.loaded)
    def loaded(self,data):
        self.records=data;rows(self.grid,[(x['name'],x['phone'],x['email'],T('Üye') if x['member'] else '—',('E-posta ' if x['email_consent'] else '')+('SMS' if x['sms_consent'] else '')) for x in data])
    def new(self):
        if not self.may_switch():return
        self.record=None
        for field in (self.name,self.phone,self.email,self.note):field.clear()
        for field in (self.member,self.email_ok,self.sms_ok):field.setChecked(False)
        self.active.setChecked(True);self.remember_saved()
    def select(self,row,col):
        if not self.may_switch():return
        self.record=self.records[row];r=self.record
        for widget,key in [(self.name,'name'),(self.phone,'phone'),(self.email,'email'),(self.note,'consent_note')]:widget.setText(r[key])
        for widget,key in [(self.member,'member'),(self.email_ok,'email_consent'),(self.sms_ok,'sms_consent'),(self.active,'active')]:widget.setChecked(r[key])
        self.remember_saved()
    def save(self):
        data=dict(name=self.name.text().strip(),phone=self.phone.text().strip(),email=self.email.text().strip(),consent_note=self.note.text().strip(),member=self.member.isChecked(),email_consent=self.email_ok.isChecked(),sms_consent=self.sms_ok.isChecked(),active=self.active.isChecked())
        payload={'data':data}
        if self.record:payload.update(id=self.record['id'],version=self.record['version'])
        self.mutation('retail_customer_save',payload,self.saved)
    def saved(self,result):self.record=result;self.saved_ok();self.refresh()

class FinanceDialog(ServerDialog):
    def __init__(self,hub,parent=None):
        super().__init__(hub.client,T('Mali Tablo'),parent);self.hub=hub;self.report={};self.resize(1250,850)
        row=QHBoxLayout()
        for label,period in [(T('Bugün'),'day'),(T('Bu Hafta'),'week'),(T('Bu Ay'),'month'),(T('Bu Yıl'),'year')]:self.button(label,lambda checked=False,p=period:self.period(p),row)
        self.body.addLayout(row);row=QHBoxLayout();self.start=QDateEdit();self.end=QDateEdit()
        for field in (self.start,self.end):field.setCalendarPopup(True);field.setDisplayFormat('dd.MM.yyyy');row.addWidget(field)
        self.location=QComboBox();self.location.addItem(T('Tüm şube ve depolar'),None);self.channel=QComboBox();self.channel.addItem(T('Tüm satış kanalları'),None)
        for combo,key in [(self.location,'locations'),(self.channel,'channels')]:
            for item in hub.data.get(key,[]):combo.addItem(item['name']+('' if item['active'] else ' · '+render(T('Kapalı'))),item['id'])
            row.addWidget(combo)
        self.button(T('Göster'),self.refresh,row);self.body.addLayout(row)
        self.summary=QLabel();self.summary.setObjectName('retailSummary');self.summary.setWordWrap(True);self.body.addWidget(self.summary)
        self.grid=table([T('Tarih'),T('Şube / Depo'),T('Satış Kanalı'),T('Net Satış'),T('Satılan Malın Maliyeti'),T('Brüt Kâr')]);self.body.addWidget(self.grid,1)
        self.expenses=table([T('Tarih'),T('Gider'),T('Tutar')]);self.expenses.setMaximumHeight(160);self.body.addWidget(self.expenses)
        row=QHBoxLayout();self.button(T('Gider Ekle'),self.expense,row);self.button(T('Seçili Gideri İptal Et'),self.void,row);self.button(T('Şube ve Kanalları Yönet'),self.locations,row);self.button(T('CSV Dışa Aktar'),self.export,row);self.body.addLayout(row)
        note=QLabel(T('Tarihler Türkiye saatine göredir. Brüt kâr = iade sonrası satış − satılan malın maliyeti. Faaliyet sonucu = brüt kâr − girilmiş giderler; vergi ve henüz girilmemiş giderleri içermez. Geçmiş fiyat ve maliyetler korunur.'));note.setWordWrap(True);self.body.addWidget(note)
        self.period('month')
    def period(self,period):
        today=datetime.now(ZoneInfo('Europe/Istanbul')).date();first=today
        if period=='week':first=today-timedelta(days=today.weekday())
        elif period=='month':first=today.replace(day=1)
        elif period=='year':first=today.replace(month=1,day=1)
        self.start.setDate(QDate(first.year,first.month,first.day));self.end.setDate(QDate(today.year,today.month,today.day));self.refresh()
    def refresh(self):
        payload=dict(from_=self.start.date().toString('yyyy-MM-dd'),to=self.end.date().toString('yyyy-MM-dd'),location_id=self.location.currentData(),channel_id=self.channel.currentData());payload['from']=payload.pop('from_');self.run(lambda:self.client.read('retail_finance',payload),self.loaded)
    def loaded(self,data):
        self.report=data;t=data['totals'];profit=Decimal(str(t['revenue']))-Decimal(str(t['cost']));operating=profit-Decimal(str(t['expenses']))
        self.summary.setText(T('Satış: {sales}   İade: {returns}   Net satış: {revenue}\nMaliyet: {cost}   Brüt kâr: {profit}   Gider: {expenses}   Faaliyet sonucu: {operating}',**{k:money(t[k]) for k in ['sales','returns','revenue','cost','expenses']},profit=money(profit),operating=money(operating)))
        rows(self.grid,[(x['period'],x['location'],x['channel_name'],money(x['revenue']),money(x['cost']),money(Decimal(str(x['revenue']))-Decimal(str(x['cost'])))) for x in data['rows']]);rows(self.expenses,[(x['incurred_on'],x['name'],money(x['amount'])) for x in data['expenses']])
        if t.get('missing_cost_lines'):self.status_label.setText(T('{count} satış/iade satırında maliyet 0 kayıtlı. Kârı yorumlamadan önce maliyet kayıtlarını kontrol edin.',count=t['missing_cost_lines']))
    def expense(self):
        dlg=ExpenseDialog(self.hub,self);dlg.exec();dlg.deleteLater();self.refresh()
    def void(self):
        row=self.expenses.currentRow()
        if row<0:return
        if QMessageBox.question(self,T('Gider İptali'),T('Seçili gider iptal edilsin mi? İşlem izi korunacak.'))==QMessageBox.StandardButton.Yes:self.mutation('retail_expense_void',{'id':self.report['expenses'][row]['id']},lambda _:self.refresh())
    def locations(self):
        dlg=LocationsDialog(self.hub,self);dlg.exec();dlg.deleteLater();self.hub.refresh()
    def export(self):
        path,_=QFileDialog.getSaveFileName(self,T('Mali Tabloyu Kaydet'),'DeporiaQ_Mali_Tablo.csv','CSV (*.csv)')
        if not path:return
        with open(path,'w',encoding='utf-8-sig',newline='') as file:
            writer=csv.writer(file,delimiter=';');writer.writerow([self.grid.horizontalHeaderItem(c).text() for c in range(self.grid.columnCount())])
            for row in range(self.grid.rowCount()):writer.writerow([csv_cell(self.grid.item(row,c).text()) for c in range(self.grid.columnCount())])
        self.status_label.setText(T('Kaydedildi.'))

class ExpenseDialog(ServerDialog):
    def __init__(self,hub,parent=None):
        super().__init__(hub.client,T('Gider Ekle'),parent);self.resize(650,500);self.name=QLineEdit();self.amount=QDoubleSpinBox();self.amount.setRange(.01,100000000);self.amount.setDecimals(2);self.date=QDateEdit(QDate.currentDate());self.date.setCalendarPopup(True);self.location=QComboBox();self.channel=QComboBox();self.location.addItem(T('Genel gider'),None);self.channel.addItem(T('Genel gider'),None)
        for combo,key in [(self.location,'locations'),(self.channel,'channels')]:
            for x in hub.data.get(key,[]):combo.addItem(x['name'],x['id'])
        form=QFormLayout()
        for label,widget in [(T('Açıklama'),self.name),(T('Tutar'),self.amount),(T('Tarih'),self.date),(T('Şube / Depo'),self.location),(T('Satış Kanalı'),self.channel)]:form.addRow(label,widget)
        self.body.addLayout(form);self.button(T('Kaydet'),self.save)
    def save(self):self.mutation('retail_expense',dict(name=self.name.text().strip(),amount=str(self.amount.value()),incurred_on=self.date.date().toString('yyyy-MM-dd'),location_id=self.location.currentData(),channel_id=self.channel.currentData()),lambda _:self.accept())

class LocationsDialog(ServerDialog):
    def __init__(self,hub,parent=None):
        super().__init__(hub.client,T('Şube ve Satış Kanalları'),parent);self.hub=hub;self.selected=None;self.records=[]
        self.mode=QComboBox();self.mode.addItem(T('Şube / Depo'),'locations');self.mode.addItem(T('Satış Kanalı'),'channels');self.body.addWidget(self.mode)
        self.grid=table([T('Ad'),T('Tür'),T('Durum')]);self.body.addWidget(self.grid,1);self.grid.cellClicked.connect(self.select)
        form=QFormLayout();self.name=QLineEdit();self.kind=QComboBox()
        for label,key in [(T('Şube'),'branch'),(T('Depo'),'warehouse'),(T('Merkez'),'center')]:self.kind.addItem(label,key)
        self.active=QCheckBox(T('Etkin'));self.active.setChecked(True);form.addRow(T('Ad'),self.name);form.addRow(T('Tür'),self.kind);form.addRow(self.active);self.body.addLayout(form)
        row=QHBoxLayout();self.button(T('Yeni'),self.new,row);self.button(T('Kaydet'),self.save,row);self.body.addLayout(row)
        note=QLabel(T('Kapatılan şube veya kanalın geçmişi mali tablodan silinmez. Stok ve açık işlem bulunan konum kapatılamaz. İnternet kanalları burada elle kaydedilir; sitelerden otomatik sipariş çekilmez.'));note.setWordWrap(True);self.body.addWidget(note)
        self.mode.currentIndexChanged.connect(self.render);hub.updated.connect(lambda _:self.render());self.render()
    def render(self,*args):
        key=self.mode.currentData();self.records=self.hub.data.get(key,[]);rows(self.grid,[(x['name'],x.get('location_type',T('İnternet / Diğer')),T('Etkin') if x['active'] else T('Kapalı')) for x in self.records]);self.kind.setVisible(key=='locations');self.new()
    def new(self):self.selected=None;self.name.clear();self.active.setChecked(True)
    def select(self,row,col):
        self.selected=self.records[row];self.name.setText(self.selected['name']);self.active.setChecked(self.selected['active']);self.kind.setCurrentIndex(max(0,self.kind.findData(self.selected.get('location_type'))))
    def save(self):
        if self.mode.currentData()=='locations':
            payload=dict(name=self.name.text().strip(),location_type=self.kind.currentData(),active=self.active.isChecked())
            if self.selected:payload.update(id=self.selected['id'],expected={k:self.selected[k] for k in ('name','active','location_type')})
            self.mutation('retail_location_save',payload,lambda _:self.refresh())
        else:
            payload=dict(name=self.name.text().strip(),active=self.active.isChecked())
            if self.selected:payload.update(id=self.selected['id'],expected={k:self.selected[k] for k in ('name','active')})
            self.mutation('retail_channel_save',payload,lambda _:self.refresh())
    def refresh(self):self.run(lambda:self.client.read('retail_snapshot'),self.hub.accept)

class GrantsDialog(ServerDialog):
    def __init__(self,hub,parent=None):
        super().__init__(hub.client,T('Yetkili Bilgisayarlar'),parent);self.devices=[];self.device=QComboBox();self.cap=QComboBox();self.enabled=QCheckBox(T('Yetki ver'))
        for label,key in [(T('Kampanya ve Set Yönetimi'),'offers'),(T('Raf Düzeni'),'layout'),(T('Mali Tablo ve İadeler'),'finance'),(T('Müşteri Kartları'),'customers')]:self.cap.addItem(label,key)
        self.body.addWidget(self.device);self.body.addWidget(self.cap);self.body.addWidget(self.enabled);self.button(T('Kaydet'),self.save)
        self.grid=table([T('Bilgisayar'),T('Kullanıcı'),T('Yetki')]);self.body.addWidget(self.grid,1);self.refresh()
    def refresh(self):self.run(lambda:self.client.read('retail_grants'),self.loaded)
    def loaded(self,data):
        self.devices=data['devices'];self.device.clear()
        for d in self.devices:self.device.addItem(d['name']+' · '+d['code'],d)
        names={d['code']:d['name'] for d in self.devices};rows(self.grid,[(names.get(g['device'],g['device']),g['user_id'][:8],self.cap.itemText(self.cap.findData(g['capability']))) for g in data['grants']])
    def save(self):
        d=self.device.currentData()
        if d:self.mutation('retail_grant_save',dict(user_id=d['user_id'],device=d['code'],capability=self.cap.currentData(),enabled=self.enabled.isChecked()),lambda _:self.refresh())

class ReceiptDialog(ServerDialog):
    def __init__(self,hub,rid,parent=None):
        super().__init__(hub.client,T('Satış Fişi / İade'),parent);self.hub=hub;self.rid=rid;self.record=None
        self.summary=QLabel();self.body.addWidget(self.summary);self.grid=table([T('Ürün'),T('Adet'),T('Birim Fiyat')]);self.body.addWidget(self.grid,1);self.button(T('Seçili Ürünü İade Al'),self.return_item);self.refresh()
    def refresh(self):self.run(lambda:self.client.read('retail_receipt',{'id':self.rid}),self.loaded)
    def loaded(self,data):
        self.record=data;self.summary.setText(data['id']+' · '+money(data['total']));rows(self.grid,[(x.get('name',x['product_id']),x['quantity'],money(x['price'])) for x in data['items']])
    def return_item(self):
        row=self.grid.currentRow()
        if row<0:return
        line=self.record['items'][row];qty,ok=QInputDialog.getInt(self,T('İade'),T('Teslim alınan adet:'),1,1,int(line['quantity']))
        if not ok:return
        if QMessageBox.question(self,T('İade Kontrolü'),T('Ürün fiziksel olarak teslim alındı mı? İade stok ve mali tabloya işlenecek.'))!=QMessageBox.StandardButton.Yes:return
        self.mutation('retail_return',dict(sale_id=line['sale_id'],quantity=qty,inspected=True),lambda result:self.returned(result))
    def returned(self,result):
        self.status_label.setText(T('İade kaydedildi. Müşteriye ödenecek tutar: {amount}',amount=money(result['refund'])));self.hub.refresh()
