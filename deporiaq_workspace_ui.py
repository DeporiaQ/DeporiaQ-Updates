"""Server-backed basket and workspace screens; no local stock mutation."""
from decimal import Decimal,ROUND_HALF_UP
import uuid
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QPushButton,QComboBox,QLineEdit,
 QSpinBox,QDoubleSpinBox,QTableWidgetItem,QMessageBox,QInputDialog)
from deporiaq_commerce_ui import ServerDialog,table,quantity_control,quantity_text
from deporiaq_i18n import T, render, Text ,QCheckBox,QComboBox,QFileDialog,QFormLayout,QInputDialog,QLabel,QLineEdit,QMessageBox,QPushButton,QTableWidgetItem,QWidget

class BasketDialog(ServerDialog):
    def __init__(self,client,parent=None):
        super().__init__(client,T('Çok Ürünlü Satış'),parent);self.lines=[];self.data={};self.saved_id=None;self.saved_version=None;self.approval_id=None
        self.location=QComboBox();self.body.addWidget(self.location)
        row=QHBoxLayout();self.barcode=QLineEdit();self.barcode.setPlaceholderText(T('Barkod okutun veya ürün barkodunu girin'))
        self.quantity=QSpinBox();self.quantity.setRange(1,1000000);row.addWidget(self.barcode,1);row.addWidget(quantity_control(self.quantity)[0]);self.body.addLayout(row)
        self.button(T('Set / Paket Ekle'),self.add_bundle);self.button(T('Sepete Ekle'),self.add);self.barcode.returnPressed.connect(self.add)
        self.grid=table([T('Barkod'),T('Ürün'),T('Adet'),T('Birim fiyat'),T('İndirim %'),T('Tutar')]);self.body.addWidget(self.grid,1)
        row=QHBoxLayout();self.button(T('Seçili Satırı Sil'),self.remove,row);self.button(T('Satır İndirimi'),self.discount,row);self.button(T('Yönetici Onayı'),self.discount_approval,row);self.button(T('Sepeti Beklet'),self.hold,row);self.button(T('Bekleyen Sepeti Aç'),self.restore,row);self.body.addLayout(row)
        self.total_label=QLabel();self.body.addWidget(self.total_label)
        form=QFormLayout();self.cash=QDoubleSpinBox();self.card=QDoubleSpinBox()
        for widget in (self.cash,self.card):widget.setRange(0,999999999);widget.setDecimals(2)
        form.addRow(T('Nakit:'),self.cash);form.addRow(T('Kart:'),self.card);self.body.addLayout(form)
        row=QHBoxLayout();self.button(T('Tamamı Nakit'),lambda:self.fill_payment('cash'),row);self.button(T('Tamamı Kart'),lambda:self.fill_payment('card'),row);self.sale_button=self.button(T('Satışı Tamamla'),self.sell,row);self.body.addLayout(row)
        self.refresh()
    def refresh(self):self.run(self.client.snapshot,self.loaded)
    def loaded(self,data):
        previous=self.location.currentData();self.data=data;self.location.clear()
        for loc in data['locations']:
            if loc['active'] and loc['id'] in data.get('sale_locations',[]):self.location.addItem(loc['name'],loc['id'])
        if previous:self.location.setCurrentIndex(self.location.findData(previous))
        self.render();self.barcode.setFocus()
    def add(self):
        code=self.barcode.text().strip();product=next((p for p in self.data.get('products',[]) if p['barcode']==code and p['active']),None)
        if not product:self.status_label.setText(T('Barkod bulunamadı. Ürünler ve Stoklar ekranından kontrol edin.'));return
        found=next((x for x in self.lines if x['product_id']==product['id']),None)
        if found:found['quantity']+=self.quantity.value()
        else:self.lines.append({'product_id':product['id'],'quantity':self.quantity.value(),'discount':0,'expected_price':str(product['sale_price'])})
        self.barcode.clear();self.quantity.setValue(1);self.render()
    def line_total(self,line):
        unit=(Decimal(str(line['expected_price']))*(1-Decimal(str(line['discount']))/100)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
        return unit*line['quantity']
    def total(self):return sum((self.line_total(x) for x in self.lines),Decimal(0))
    def render(self):
        self.grid.setRowCount(len(self.lines));products={p['id']:p for p in self.data.get('products',[])}
        for i,line in enumerate(self.lines):
            p=products.get(line['product_id'],{})
            for j,value in enumerate([p.get('barcode',''),p.get('name',T('Ürün bulunamadı')),line['quantity'],line['expected_price'],line['discount'],str(self.line_total(line))]):self.grid.setItem(i,j,QTableWidgetItem(str(value)))
        self.total_label.setText(T('{v0} ürün çeşidi · Toplam: {v1:.2f} TL', v0=len(self.lines), v1=self.total()));self.sale_button.setEnabled(bool(self.lines))
        self.setWindowTitle(T('Çok Ürünlü Satış')+(T(' • Kaydedilmemiş sepet') if self.lines else ''))
    def remove(self):
        row=self.grid.currentRow()
        if row>=0:self.lines.pop(row);self.render()
    def discount(self):
        row=self.grid.currentRow()
        if row<0:return
        value,ok=QInputDialog.getDouble(self,T('Satır İndirimi'),T('İndirim oranı (%):'),float(self.lines[row]['discount']),0,100,2)
        if ok:self.lines[row]['discount']=value;self.render()
    def fill_payment(self,kind):self.cash.setValue(float(self.total()) if kind=='cash' else 0);self.card.setValue(float(self.total()) if kind=='card' else 0)
    def sell(self):
        if not self.lines:return
        if Decimal(str(self.cash.value()))+Decimal(str(self.card.value()))!=self.total():self.status_label.setText(T('Nakit ve kart toplamı sepet tutarıyla eşleşmeli.'));return
        payload={'location_id':self.location.currentData(),'items':self.lines,'payments':[{'type':'cash','amount':str(self.cash.value())},{'type':'card','amount':str(self.card.value())}]}
        if self.approval_id:payload['approval_id']=self.approval_id
        if self.saved_id:payload.update(basket_id=self.saved_id,basket_version=self.saved_version)
        self.mutation('workspace_cart_sale',payload,self.sold)
    def sold(self,result):
        self.saved_id=None;self.saved_version=None;self.lines=[];self.cash.setValue(0);self.card.setValue(0);self.render();self.status_label.setText(T('Satış kaydedildi · İşlem: ')+result['id']);self.refresh()
    def hold(self):
        if not self.lines:return
        name,ok=QInputDialog.getText(self,T('Sepeti Beklet'),T('Sepet adı (ör. müşteri sıra numarası):'))
        if ok and name.strip():self.mutation('workspace_save',{'kind':'basket','data':{'name':name.strip(),'items':self.lines,'location_id':self.location.currentData()}},self.held)
    def held(self,result):self.saved_id=None;self.saved_version=None;self.lines=[];self.render();self.status_label.setText(T('Sepet kaydedildi. Stok ayrılmadı; satış sırasında tekrar kontrol edilir.'))
    def restore(self):
        if self.lines:self.status_label.setText(T('Önce mevcut sepeti bekletin veya boşaltın.'));return
        self.run(lambda:self.client.read('workspace_list'),self.choose_basket)
    def choose_basket(self,data):
        records=[r for r in data['records'] if r['kind']=='basket' and not r['data'].get('closed')]
        if not records:self.status_label.setText(T('Bekleyen sepet yok.'));return
        names=[r['data']['name']+' · '+r['id'][:8] for r in records];name,ok=QInputDialog.getItem(self,T('Bekleyen Sepetler'),T('Sepet:'),names,0,False)
        if ok:
            record=records[names.index(name)];self.saved_id=record['id'];self.saved_version=record['version'];self.lines=[dict(x) for x in record['data']['items']];self.location.setCurrentIndex(self.location.findData(record['data'].get('location_id')));self.render()
    def discount_approval(self):
        if self.lines:self.run(lambda:self.client.read('workspace_list'),self.find_approval)
    def find_approval(self,data):
        match=next((r for r in data['records'] if r['kind']=='approval' and r['data'].get('items')==self.lines and r['data'].get('location_id')==self.location.currentData() and r['data'].get('status')=='approved'),None)
        if match:self.approval_id=match['id'];self.status_label.setText(T('Yönetici onayı bulundu. Satışı tamamlayabilirsiniz.'));return
        self.mutation('workspace_discount_request',{'items':self.lines,'location_id':self.location.currentData()},lambda r:self.status_label.setText(T('Onay istendi. Yönetici onayladıktan sonra bu düğmeye tekrar basın.')))
    def add_bundle(self):self.run(lambda:self.client.read('workspace_list'),self.choose_bundle)
    def choose_bundle(self,data):
        records=[r for r in data['records'] if r['kind']=='bundle']
        if not records:self.status_label.setText(T('Tanımlı set yok. Yönetimden set tanımlayın.'));return
        names=[r['data']['name']+' · '+r['id'][:8] for r in records];name,ok=QInputDialog.getItem(self,T('Set / Paket'),T('Set:'),names,0,False)
        if not ok:return
        products={p['id']:p for p in self.data['products'] if p['active']}
        bundle=records[names.index(name)]['data']['items']
        if any(x['product_id'] not in products for x in bundle):self.status_label.setText(T('Set içinde pasif ürün var; seti güncelleyin.'));return
        for item in bundle:
            product=products[item['product_id']];self.lines.append({'product_id':product['id'],'quantity':item['quantity'],'discount':0,'expected_price':str(product['sale_price'])})
        self.render()
    def reject(self):
        if self.job is not None:return
        if self.lines and QMessageBox.question(self,T('Kaydedilmemiş Sepet'),T('Sepeti kaydetmeden çıkılsın mı?'))!=QMessageBox.StandardButton.Yes:return
        super().reject()
    def closeEvent(self,event):
        if self.job is not None:event.ignore();return
        if self.lines and QMessageBox.question(self,T('Kaydedilmemiş Sepet'),T('Sepeti kaydetmeden çıkılsın mı?'))!=QMessageBox.StandardButton.Yes:event.ignore();return
        event.accept()

class EditableDialog(ServerDialog):
    def remember_saved(self):
        self._baseline=self.form_state();self._base_title=getattr(self,'_base_title',self.title_text);self.setWindowTitle(self._base_title)
    def form_state(self):return None
    def mark_edited(self,*args):
        if hasattr(self,'_baseline'):self.setWindowTitle(self._base_title+(T(' • Kaydedilmemiş değişiklik') if self.form_state()!=self._baseline else ''))
    def may_switch(self):
        if not hasattr(self,'_baseline') or self.form_state()==self._baseline:return True
        return QMessageBox.question(self,T('Kaydedilmemiş Değişiklik'),T('Kaydedilmemiş değişikliklerden vazgeçilsin mi?'),QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel)==QMessageBox.StandardButton.Discard
    def may_close(self):
        if self.job is not None:return False
        if not hasattr(self,'_baseline') or self.form_state()==self._baseline:return True
        answer=QMessageBox.question(self,T('Kaydedilmemiş Değişiklik'),T('Değişiklikler kaydedilsin mi?'),QMessageBox.StandardButton.Save|QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel)
        if answer==QMessageBox.StandardButton.Discard:return True
        if answer==QMessageBox.StandardButton.Save:self._close_after_save=True;self.save()
        return False
    def reject(self):
        if self.may_close():super().reject()
    def closeEvent(self,event):
        if self.may_close():event.accept()
        else:event.ignore()
    def saved_ok(self):
        self.remember_saved()
        if getattr(self,'_close_after_save',False):self._close_after_save=False;self.accept()

class RecordsDialog(EditableDialog):
    FIELDS={
      'supplier':[('name',T('Tedarikçi adı')),('contact',T('Yetkili')),('phone',T('Telefon')),('email',T('E-posta')),('address',T('Adres')),('notes',T('Not'))],
      'task':[('name',T('Görev')),('assignee',T('Sorumlu')),('due',T('Son tarih (YYYY-AA-GG)')),('status',T('Durum')),('notes',T('Açıklama'))],
      'batch':[('lot',T('Parti numarası')),('expires',T('Son kullanma tarihi (YYYY-AA-GG)')),('notes',T('Not'))],
      'product':[('category',T('Kategori')),('tags',T('Etiketler')),('author',T('Yazar / marka')),('publisher',T('Yayınevi / üretici')),('variant',T('Varyant grubu')),('variant_value',T('Renk / beden / baskı')),('shelf',T('Raf / koridor'))]
    }
    def __init__(self,client,kind,parent=None):
        super().__init__(client,{'supplier':T('Tedarikçi Kartları'),'task':T('İşletme Görevleri'),'product':T('Ürün Ayrıntıları'),'batch':T('Parti ve Son Kullanma Tarihleri')}[kind],parent)
        self.kind=kind;self.record=None;self.records=[];self.fields={};self.product=QComboBox();form=QFormLayout()
        if kind in ('product','batch'):form.addRow(T('Ürün:'),self.product)
        for key,label in self.FIELDS[kind]:
            if key=='assignee':widget=QComboBox()
            elif key=='status':widget=QComboBox();widget.addItems([T('Yapılacak'),T('Devam ediyor'),T('Tamamlandı')])
            else:widget=QLineEdit()
            self.fields[key]=widget;form.addRow(label+':',widget)
            (widget.textEdited if isinstance(widget,QLineEdit) else widget.activated).connect(self.mark_edited)
        self.body.addLayout(form);row=QHBoxLayout();self.button(T('Yeni Kayıt'),self.new,row);self.button(T('Kaydet'),self.save,row);self.body.addLayout(row)
        self.search=QLineEdit();self.search.setPlaceholderText(T('Ad, kategori, etiket, varyant veya raf ara…'));self.search.textChanged.connect(self.filter_records);self.body.addWidget(self.search)
        self.grid=table([T('Kayıt'),T('Son değişiklik'),T('Sürüm')]);self.body.addWidget(self.grid,1);self.grid.cellClicked.connect(self.select)
        self.product.activated.connect(self.mark_edited)
        self.run(lambda:(self.client.snapshot(),self.client.read('workspace_list')),self.loaded)
    def form_state(self):return (self.product.currentData(),tuple((k,w.text() if isinstance(w,QLineEdit) else w.currentText()) for k,w in self.fields.items()),getattr(self,'image_data',''))
    def loaded(self,value):
        snapshot,data=value;self.product.clear()
        if self.kind=='task':
            self.fields['assignee'].clear()
            for member in data.get('members',[]):self.fields['assignee'].addItem(member['name'],member['id'])
        for product in snapshot['products']:
            if product['active']:self.product.addItem(product['name'],product['id'])
        self.update_records(data);self.remember_saved()
    def update_records(self,data):
        self.all_records=[r for r in data['records'] if r['kind']==self.kind];self.filter_records()
    def filter_records(self,*args):
        import json
        needle=self.search.text().casefold()
        self.records=[r for r in getattr(self,'all_records',[]) if needle in json.dumps(r['data'],ensure_ascii=False).casefold() or needle in self.product.itemText(self.product.findData(r['data'].get('product_id'))).casefold()];self.grid.setRowCount(len(self.records))
        for i,r in enumerate(self.records):
            name=r['data'].get('name') or (r['data'].get('lot','')+' · '+r['data'].get('expires','') if self.kind=='batch' else '') or self.product.itemText(self.product.findData(r['data'].get('product_id')))
            for j,value in enumerate([name,r['updated_at'],r['version']]):self.grid.setItem(i,j,QTableWidgetItem(str(value)))
    def new(self):
        if not self.may_switch():return False
        self.record=None
        for w in self.fields.values():
            if isinstance(w,QLineEdit):w.clear()
            else:w.setCurrentIndex(0)
        self.remember_saved();return True
    def select(self,row,column):
        if not self.may_switch():return False
        self.record=self.records[row]
        for key,w in self.fields.items():
            value=str(self.record['data'].get(key,''))
            if isinstance(w,QLineEdit):w.setText(value)
            elif key=='assignee':w.setCurrentIndex(w.findData(value))
            else:w.setCurrentText(value)
        self.product.setCurrentIndex(self.product.findData(self.record['data'].get('product_id')));self.remember_saved();return True
    def save(self):
        data={key:(w.text().strip() if isinstance(w,QLineEdit) else w.currentData() if key=='assignee' else w.currentText()) for key,w in self.fields.items()}
        if self.kind in ('product','batch'):data['product_id']=self.product.currentData()
        payload={'kind':self.kind,'data':data}
        if self.record:payload.update(id=self.record['id'],version=self.record['version'])
        self.mutation('workspace_save',payload,self.saved)
    def saved(self,result):
        closing=getattr(self,'_close_after_save',False);self.record=result;self.saved_ok()
        if not closing:self.run(lambda:self.client.read('workspace_list'),self.update_records)

from deporiaq_i18n import QFileDialog,QCheckBox,QWidget
from PySide6.QtGui import QPixmap
import base64,io

class ProductDetailsDialog(RecordsDialog):
    def __init__(self,client,parent=None):
        super().__init__(client,'product',parent);self.image_data='';self.preview=QLabel();self.preview.setMaximumHeight(150);self.body.insertWidget(0,self.preview)
        self.button(T('Ürün Görseli Seç'),self.choose_image)
        self.button(T('Barkod / Raf Etiketi PDF'),self.label_pdf)
    def choose_image(self):
        from PIL import Image
        path,_=QFileDialog.getOpenFileName(self,T('Ürün görseli'),'',T('Görseller (*.png *.jpg *.jpeg)'))
        if not path:return
        try:
            image=Image.open(path);image.thumbnail((640,640));image=image.convert('RGB');buffer=io.BytesIO();image.save(buffer,format='JPEG',quality=85)
            self.image_data=base64.b64encode(buffer.getvalue()).decode();self.show_image();self.mark_edited()
        except Exception:self.status_label.setText(T('Görsel açılamadı. PNG veya JPEG seçin.'))
    def show_image(self):
        image=QPixmap();image.loadFromData(base64.b64decode(self.image_data) if self.image_data else b'');self.preview.setPixmap(image.scaled(160,140,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
    def select(self,row,column):
        if not super().select(row,column):return
        self.run(lambda:self.client.read('workspace_record',{'id':self.record['id']}),self.image_loaded)
    def image_loaded(self,record):
        self.record=record;self.image_data=record['data'].get('image_jpeg','');self.show_image();self.remember_saved()
    def new(self):
        if super().new():self.image_data='';self.show_image();self.remember_saved()
    def save(self):
        data={key:w.text().strip() for key,w in self.fields.items()};data.update(product_id=self.product.currentData(),image_jpeg=self.image_data)
        payload={'kind':'product','data':data}
        if self.record:payload.update(id=self.record['id'],version=self.record['version'])
        self.mutation('workspace_save',payload,self.saved)
    def label_pdf(self):
        pid=self.product.currentData()
        if not pid:return
        self.run(self.client.snapshot,lambda data:self.write_label(next((p for p in data['products'] if p['id']==pid),None)))
    def write_label(self,product):
        if not product:return
        from reportlab.pdfgen import canvas
        from reportlab.graphics.barcode import code128
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from pathlib import Path
        import os
        font=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'/'arial.ttf'
        if not font.exists():font=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
        if not font.exists():self.status_label.setText(T('Etiket için Türkçe yazı tipi bulunamadı.'));return
        pdfmetrics.registerFont(TTFont('DeporiaQLabel',str(font)))
        path,_=QFileDialog.getSaveFileName(self,T('Raf etiketi'),'DeporiaQ_Etiket.pdf','PDF (*.pdf)')
        if not path:return
        c=canvas.Canvas(path,pagesize=(90*mm,55*mm));c.setFont('DeporiaQLabel',10)
        name=product['name']
        while pdfmetrics.stringWidth(name,'DeporiaQLabel',10)>80*mm:name=name[:-2]+'…'
        c.drawString(5*mm,47*mm,name);c.setFont('DeporiaQLabel',15);c.drawString(5*mm,38*mm,f"{Decimal(str(product['sale_price'])):.2f} TL")
        code=code128.Code128(product['barcode'],barHeight=16*mm,barWidth=.28*mm,humanReadable=True)
        c.saveState();c.translate(5*mm,12*mm);scale=min(1,80*mm/code.width);c.scale(scale,1);code.drawOn(c,0,0);c.restoreState()
        c.setFont('DeporiaQLabel',8);c.drawString(5*mm,4*mm,self.fields['shelf'].text()[:60]);c.save();self.status_label.setText(T('Barkodlu raf etiketi kaydedildi.'))

class CollectionDialog(EditableDialog):
    def __init__(self,client,kind,parent=None):
        super().__init__(client,T('Satın Alma Siparişleri') if kind=='purchase' else T('Set ve Paket Tanımları'),parent)
        self.kind=kind;self.lines=[];self.records=[];self.record=None;self.snapshot={};self.name=QLineEdit();self.name.textEdited.connect(self.mark_edited);self.name.setPlaceholderText(T('Sipariş / set adı'));self.body.addWidget(self.name)
        row=QHBoxLayout();self.product=QComboBox();self.quantity=QSpinBox();self.quantity.setRange(1,1000000);row.addWidget(self.product,1);row.addWidget(quantity_control(self.quantity)[0]);self.button(T('Ekle'),self.add,row);self.body.addLayout(row)
        self.grid=table([T('Ürün'),T('Adet')]);self.body.addWidget(self.grid)
        self.button(T('Seçili Satırı Sil'),self.remove)
        self.supplier=QComboBox()
        if kind=='purchase':self.body.addWidget(QLabel(T('Tedarikçi')));self.body.addWidget(self.supplier)
        self.button(T('Yeni Tanım'),self.new);self.button(T('Kaydet'),self.save)
        self.saved=QComboBox();self.body.addWidget(self.saved);self.button(T('Kayıtlı Tanımı Aç'),self.select)
        if kind=='purchase':self.button(T('Mal Kabul ve Fark Tutanağı'),self.receive)
        self.run(lambda:(client.snapshot(),client.read('workspace_list')),self.loaded)
    def form_state(self):return (self.name.text(),self.supplier.currentData(),tuple((x['product_id'],x['quantity']) for x in self.lines))
    def loaded(self,value):
        self.snapshot,data=value;self.product.clear()
        for p in self.snapshot['products']:
            if p['active']:self.product.addItem(p['name'],p['id'])
        self.records=data['records'];self.saved.clear();self.supplier.clear()
        if self.record:self.record=next((r for r in self.records if r['id']==self.record['id']),self.record)
        for r in self.records:
            if r['kind']==self.kind:self.saved.addItem(r['data']['name'],r['id'])
            if r['kind']=='supplier':self.supplier.addItem(r['data']['name'],r['id'])
        self.remember_saved()
    def new(self):
        if not self.may_switch():return
        self.record=None;self.lines=[];self.name.clear();self.render();self.remember_saved()
    def add(self):
        pid=self.product.currentData()
        if not pid:return
        line=next((x for x in self.lines if x['product_id']==pid),None)
        if line:line['quantity']+=self.quantity.value()
        else:self.lines.append({'product_id':pid,'quantity':self.quantity.value()})
        self.render()
    def remove(self):
        row=self.grid.currentRow()
        if row>=0:self.lines.pop(row);self.render()
    def render(self):
        self.grid.setRowCount(len(self.lines))
        for i,line in enumerate(self.lines):
            self.grid.setItem(i,0,QTableWidgetItem(self.product.itemText(self.product.findData(line['product_id']))));self.grid.setItem(i,1,QTableWidgetItem(str(line['quantity'])))
        self.mark_edited()
    def select(self):
        if not self.may_switch():return
        self.record=next((r for r in self.records if r['id']==self.saved.currentData()),None)
        if not self.record:return
        self.lines=[dict(x) for x in self.record['data']['items']];self.name.setText(self.record['data']['name']);self.supplier.setCurrentIndex(self.supplier.findData(self.record['data'].get('supplier_id')));self.render();self.remember_saved()
    def save(self):
        payload={'kind':self.kind,'data':{'name':self.name.text().strip(),'items':self.lines,'supplier_id':self.supplier.currentData()}}
        if self.record:payload.update(id=self.record['id'],version=self.record['version'])
        self.mutation('workspace_save',payload,self.completed)
    def completed(self,result):
        closing=getattr(self,'_close_after_save',False);self.record=result;self.saved_ok()
        if not closing:self.run(lambda:(self.client.snapshot(),self.client.read('workspace_list')),self.loaded)
    def receive(self):
        if not self.record:self.status_label.setText(T('Önce kayıtlı satın alma siparişini açın.'));return
        ReceiptDialog(self.client,self.record,self.snapshot,self.records,self).exec();self.run(lambda:(self.client.snapshot(),self.client.read('workspace_list')),self.loaded)

class ReceiptDialog(ServerDialog):
    def __init__(self,client,purchase,snapshot,records,parent=None):
        super().__init__(client,T('Mal Kabul · Eksik / Fazla / Hasarlı'),parent);self.purchase=purchase;self.rows=[];self.location=QComboBox()
        for loc in snapshot['locations']:
            if loc['active']:self.location.addItem(loc['name'],loc['id'])
        self.body.addWidget(self.location);self.grid=table([T('Ürün'),T('Sipariş'),T('Önceki kabul'),T('Kalan'),T('Sağlam teslim'),T('Hasarlı teslim')]);self.body.addWidget(self.grid)
        self.grid.setRowCount(len(purchase['data']['items']));products={p['id']:p['name'] for p in snapshot['products']}
        for i,item in enumerate(purchase['data']['items']):
            prior=sum(Decimal(str(x.get('accepted',0)))+Decimal(str(x.get('damaged',0))) for r in records if r['kind']=='receipt' and r['data'].get('purchase_id')==purchase['id'] for x in r['data']['items'] if x['product_id']==item['product_id'])
            for col,value in enumerate([products.get(item['product_id'],''),item['quantity'],quantity_text(prior),quantity_text(Decimal(str(item['quantity']))-prior)]):self.grid.setItem(i,col,QTableWidgetItem(str(value)))
            accepted=QSpinBox();damaged=QSpinBox()
            for widget in (accepted,damaged):widget.setRange(0,1000000)
            self.grid.setCellWidget(i,4,accepted);self.grid.setCellWidget(i,5,damaged);self.rows.append((item['product_id'],accepted,damaged))
        self.body.addWidget(QLabel(T('Sağlam adet satılabilir stoğa eklenir. Hasarlı adet ayrı kaydedilir. Fazla teslim, kalan sütununda eksi olarak görünür.')))
        self.button(T('Teslimatı Kaydet'),self.receive)
    def receive(self):
        items=[{'product_id':pid,'accepted':a.value(),'damaged':d.value()} for pid,a,d in self.rows if a.value()+d.value()>0]
        self.mutation('workspace_purchase_receive',{'purchase_id':self.purchase['id'],'version':self.purchase['version'],'location_id':self.location.currentData(),'items':items},lambda result:self.accept())

class DamageDialog(ServerDialog):
    def __init__(self,client,parent=None):
        super().__init__(client,T('Hasarlı Ürün Ayır'),parent);self.product=QComboBox();self.location=QComboBox();self.quantity=QSpinBox();self.quantity.setRange(1,1000000);self.reason=QLineEdit();form=QFormLayout()
        for title,w in [(T('Ürün:'),self.product),(T('Konum:'),self.location),(T('Adet:'),quantity_control(self.quantity)[0]),(T('Hasar nedeni:'),self.reason)]:form.addRow(title,w)
        self.body.addLayout(form);self.body.addWidget(QLabel(T('Bu işlem hasarlı adedi satılabilir stoktan düşürür ve ayrı hasar kaydı oluşturur.')));self.button(T('Hasarlı Stok Alanına Ayır'),self.save)
        self.history=table([T('Ürün'),T('Konum'),T('Adet'),T('Neden')]);self.body.addWidget(self.history)
        self.run(lambda:(client.snapshot(),client.read('workspace_list')),self.loaded)
    def loaded(self,value):
        data,workspace=value;self.product.clear();self.location.clear()
        products={p['id']:p['name'] for p in data['products']};locations={l['id']:l['name'] for l in data['locations']}
        records=[r['data'] for r in workspace['records'] if r['kind']=='damage'];self.history.setRowCount(len(records))
        for i,r in enumerate(records):
            for j,text in enumerate([products.get(r['product_id'],''),locations.get(r['location_id'],''),r['quantity'],r.get('reason','')]):self.history.setItem(i,j,QTableWidgetItem(str(text)))
        for p in data['products']:
            if p['active']:self.product.addItem(p['name'],p['id'])
        for l in data['locations']:
            if l['active']:self.location.addItem(l['name'],l['id'])
    def save(self):self.mutation('workspace_damage',{'product_id':self.product.currentData(),'location_id':self.location.currentData(),'quantity':self.quantity.value(),'reason':self.reason.text().strip()},lambda r:self.run(lambda:(self.client.snapshot(),self.client.read('workspace_list')),self.loaded))

class BulkPricesDialog(ServerDialog):
    def __init__(self,client,parent=None):
        super().__init__(client,T('Toplu Fiyat Değişikliği Önizlemesi'),parent);self.products=[];self.preview=[]
        self.filter=QLineEdit();self.filter.setPlaceholderText(T('Ürün adı veya barkod filtresi'));self.body.addWidget(self.filter)
        self.percent=QDoubleSpinBox();self.percent.setRange(-100,1000);self.percent.setSuffix(' %');self.body.addWidget(self.percent)
        self.button(T('Önizle'),self.calculate);self.grid=table([T('Barkod'),T('Ürün'),T('Eski fiyat'),T('Yeni fiyat')]);self.body.addWidget(self.grid,1)
        self.apply_button=self.button(T('Önizlemedeki Fiyatları Uygula'),self.apply);self.apply_button.setEnabled(False)
        self.filter.textChanged.connect(self.invalidate);self.percent.valueChanged.connect(self.invalidate);self.run(client.snapshot,self.loaded)
    def loaded(self,data):self.products=data['products']
    def invalidate(self,*args):self.preview=[];self.apply_button.setEnabled(False)
    def calculate(self):
        products=[p for p in self.products if p['active'] and self.filter.text().casefold() in (p['name']+' '+p['barcode']).casefold()];self.preview=[];self.grid.setRowCount(len(products))
        for i,p in enumerate(products):
            price=(Decimal(str(p['sale_price']))*(1+Decimal(str(self.percent.value()))/100)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
            self.preview.append({'product_id':p['id'],'expected_price':str(p['sale_price']),'price':str(price)})
            for j,value in enumerate([p['barcode'],p['name'],p['sale_price'],price]):self.grid.setItem(i,j,QTableWidgetItem(str(value)))
        self.apply_button.setEnabled(bool(self.preview))
    def apply(self):
        if not self.preview:return
        if QMessageBox.question(self,T('Fiyatları Güncelle'),T('{v0} ürünün fiyatı değiştirilsin mi?', v0=len(self.preview)))!=QMessageBox.StandardButton.Yes:return
        self.mutation('workspace_prices',{'items':self.preview},self.applied)
    def applied(self,r):self.invalidate();self.status_label.setText(T('{v0} ürün güncellendi.', v0=r['updated']));self.run(self.client.snapshot,self.loaded)

class ImportDialog(ServerDialog):
    HEADERS=[('barcode',T('Barkod')),('name',T('Ürün adı')),('sale_price',T('Satış fiyatı')),('purchase_price',T('Alış fiyatı')),('critical_stock',T('Kritik stok'))]
    def __init__(self,client,parent=None):
        super().__init__(client,T('Önizlemeli Excel / CSV İçe Aktarma'),parent);self.source=[];self.columns={};self.items=[];self.existing=set()
        self.button(T('Excel / CSV Dosyası Seç'),self.choose);self.form=QFormLayout();self.body.addLayout(self.form)
        self.button(T('Eşleştirmeyi Kontrol Et ve Önizle'),self.preview)
        self.grid=table([T('Satır'),T('Barkod'),T('Ürün'),T('Satış'),T('Alış'),T('Kritik'),T('Kontrol')]);self.body.addWidget(self.grid,1)
        self.apply_button=self.button(T('Doğrulanan Ürünleri Ekle'),self.commit);self.apply_button.setEnabled(False)
        self.run(client.snapshot,lambda data:setattr(self,'existing',{p['barcode'] for p in data['products']}))
    def invalidate(self,*args):self.items=[];self.apply_button.setEnabled(False)
    def choose(self):
        path,_=QFileDialog.getOpenFileName(self,T('Ürün dosyası'),'','Excel / CSV (*.xlsx *.csv)')
        if not path:return
        try:
            if path.lower().endswith('.xlsx'):
                import openpyxl
                book=openpyxl.load_workbook(path,read_only=True,data_only=False)
                try:
                    cells=list(book.active.iter_rows(max_row=502))
                    if any(c.data_type=='f' for row in cells for c in row):raise ValueError(T('Formül içeren dosya kabul edilmez. Değerleri ayrı dosyaya yapıştırın.'))
                    rows=[[c.value for c in row] for row in cells]
                finally:book.close()
            else:
                import csv
                with open(path,encoding='utf-8-sig',newline='') as f:
                    sample=f.read(4096);f.seek(0)
                    try:dialect=csv.Sniffer().sniff(sample,delimiters=',;\t')
                    except csv.Error:dialect=csv.excel
                    reader=csv.reader(f,dialect);rows=[]
                    for row in reader:
                        rows.append(row)
                        if len(rows)>501:break
            if len(rows)<2 or len(rows)>501:raise ValueError(T('Başlık ve en fazla 500 ürün satırı gerekli.'))
            self.source=rows[1:];self.columns={}
            while self.form.rowCount():self.form.removeRow(0)
            for key,label in self.HEADERS:
                combo=QComboBox()
                for i,header in enumerate(rows[0]):combo.addItem(str(header or T('Sütun {v0}', v0=i + 1)),i)
                match=next((i for i,x in enumerate(rows[0]) if str(x).casefold() in (key,label.casefold())),0);combo.setCurrentIndex(match)
                combo.currentIndexChanged.connect(self.invalidate);self.form.addRow(label+':',combo);self.columns[key]=combo
            self.invalidate();self.status_label.setText(T('Barkod sütunu metin biçiminde olmalı; baştaki sıfırlar korunur.'))
        except Exception as e:self.status_label.setText(str(e));self.invalidate()
    def preview(self):
        self.invalidate();self.grid.setRowCount(len(self.source));seen=set();valid=True
        if len({w.currentData() for w in self.columns.values()})!=5:self.status_label.setText(T('Her alan için farklı bir sütun seçin.'));return
        for i,row in enumerate(self.source):
            item={};error=T('Uygun')
            try:
                raw={key:row[w.currentData()] for key,w in self.columns.items()}
                if not isinstance(raw['barcode'],str):raise ValueError(T('Barkod metin biçiminde olmalı'))
                item={'barcode':raw['barcode'].strip(),'name':str(raw['name'] or '').strip()}
                if not item['barcode'] or not item['name']:raise ValueError(T('Barkod ve ad gerekli'))
                if item['barcode'] in seen or item['barcode'] in self.existing:raise ValueError(T('Tekrarlanan barkod'))
                seen.add(item['barcode'])
                for key in ('sale_price','purchase_price','critical_stock'):
                    number=Decimal(str(raw[key]).strip().replace(',','.'))
                    if not number.is_finite() or not 0<=number<=10000000:raise ValueError(T('Geçersiz sayı'))
                    if key=='critical_stock' and number!=number.to_integral_value():raise ValueError(T('Kritik stok tam sayı olmalı'))
                    if key!='critical_stock' and number!=number.quantize(Decimal('.01')):raise ValueError(T('Fiyat en fazla iki ondalık içermeli'))
                    item[key]=str(number)
                self.items.append(item)
            except Exception as e:error=str(e);valid=False
            values=[i+2,item.get('barcode',''),item.get('name',''),item.get('sale_price',''),item.get('purchase_price',''),item.get('critical_stock',''),error]
            for j,value in enumerate(values):self.grid.setItem(i,j,QTableWidgetItem(str(value)))
        self.apply_button.setEnabled(valid and bool(self.items))
        if not valid:self.items=[]
    def commit(self):
        if self.items:self.mutation('workspace_import',{'items':self.items},self.imported)
    def imported(self,result):self.invalidate();self.status_label.setText(T('{v0} ürün eklendi. Stok girişi ayrıca yapılır.', v0=result['imported']))


class ApprovalDialog(ServerDialog):
    def __init__(self,client,parent=None):
        super().__init__(client,T('İndirim Onayları'),parent);self.records=[];self.grid=table([T('Talep'),T('Konum'),T('Ürün satırları / indirimler')]);self.body.addWidget(self.grid)
        self.button(T('Yenile'),self.refresh);self.button(T('Seçili İndirimi 15 Dakika İçin Onayla'),self.approve);self.refresh()
    def refresh(self):self.run(lambda:(self.client.snapshot(),self.client.read('workspace_list')),self.loaded)
    def loaded(self,value):
        data,records=value;products={p['id']:p['name'] for p in data['products']};locations={l['id']:l['name'] for l in data['locations']}
        self.records=[r for r in records['records'] if r['kind']=='approval' and r['data'].get('status')=='pending'];self.grid.setRowCount(len(self.records))
        for i,r in enumerate(self.records):
            summary='; '.join(f"{products.get(x['product_id'],'?')} × {x['quantity']} · %{x.get('discount',0)}" for x in r['data']['items'])
            for j,value in enumerate([r['id'][:8],locations.get(r['data']['location_id'],'?'),summary]):self.grid.setItem(i,j,QTableWidgetItem(value))
    def approve(self):
        i=self.grid.currentRow()
        if i<0:return
        if QMessageBox.question(self,T('İndirim Onayı'),T('Seçili sepet indirimi onaylansın mı?'))!=QMessageBox.StandardButton.Yes:return
        self.mutation('workspace_discount_approve',{'id':self.records[i]['id']},lambda r:self.refresh())
