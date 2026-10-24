"""Explicit product lifecycle. Every write is authorized and serialized on the server."""
import unicodedata
from decimal import Decimal
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout,QHBoxLayout,QDoubleSpinBox,QSpinBox,QDialog
from deporiaq_i18n import T,QLabel,QLineEdit,QComboBox,QMessageBox,QInputDialog
from deporiaq_commerce_ui import ServerDialog,table,rows,quantity_text

FIELDS=('barcode','name','sale_price','purchase_price','critical_stock','active')

def expected_product(product):
    return {key:product.get(key,True if key=='active' else 0 if key in FIELDS[2:5] else '') for key in FIELDS}

def clean_barcode(value):
    value=value.strip()
    if not 1<=len(value)<=120 or any(c.isspace() or unicodedata.category(c).startswith('C') for c in value):
        raise ValueError(str(T('Barkod boşluk veya görünmeyen karakter içeremez.')))
    return value

class ProductEditor(ServerDialog):
    def __init__(self,client,product=None,parent=None):
        super().__init__(client,T('Seçili Ürünü Düzenle') if product else T('Yeni Ürün'),parent)
        self.product=product;self.saved=None;self.resize(560,430)
        form=QFormLayout();self.body.addLayout(form)
        self.barcode=QLineEdit();self.barcode.setMaxLength(120);self.name=QLineEdit();self.name.setMaxLength(250)
        self.sale=QDoubleSpinBox();self.cost=QDoubleSpinBox();self.critical=QSpinBox()
        for field in (self.sale,self.cost):field.setRange(0,10000000);field.setDecimals(2)
        self.critical.setRange(0,1000000)
        for label,field in ((T('Barkod'),self.barcode),(T('Ad'),self.name),(T('Satış fiyatı'),self.sale),(T('Alış fiyatı'),self.cost),(T('Kritik stok'),self.critical)):
            form.addRow(label,field)
        if product:
            self.barcode.setText(product['barcode']);self.name.setText(product['name'])
            self.sale.setValue(float(product.get('sale_price',0)));self.cost.setValue(float(product.get('purchase_price',0)));self.critical.setValue(int(product.get('critical_stock',0)))
        note=QLabel(T('Ürün bilgileri değişir; stok miktarı ve işlem geçmişi korunur.'));note.setWordWrap(True);self.body.addWidget(note)
        actions=QHBoxLayout();self.button(T('Vazgeç'),self.reject,actions);self.save_button=self.button(T('Kaydet'),self.save,actions);self.body.addLayout(actions)
    def save(self):
        try:barcode=clean_barcode(self.barcode.text())
        except ValueError as error:self.status_label.setText(str(error));return
        name=self.name.text().strip()
        if not name or any(unicodedata.category(c).startswith('C') for c in name):
            self.status_label.setText(T('Geçerli bir ürün adı yazın.'));return
        payload={'operation':'edit' if self.product else 'create','barcode':barcode,'name':name,
                 'sale_price':self.sale.value(),'purchase_price':self.cost.value(),'critical_stock':self.critical.value()}
        if self.product:payload.update(product_id=self.product['id'],expected=expected_product(self.product))
        def completed(result):self.saved=result['id'];self.accept()
        self.mutation('catalog_manage',payload,completed)

class ProductCatalogDialog(ServerDialog):
    def __init__(self,client,parent=None):
        super().__init__(client,T('Ürün Kartları'),parent);self.resize(1050,660);self.data={};self.visible_products=[];self.selected_id=None
        filters=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText(T('Ürün adı veya barkod ara…'));self.search.setClearButtonEnabled(True)
        self.state=QComboBox();self.state.addItems([T('Aktif Ürünler'),T('Arşivlenen Ürünler'),T('Tüm Ürünler')]);filters.addWidget(self.search,2);filters.addWidget(self.state);self.body.addLayout(filters)
        self.grid=table([T('Barkod'),T('Ürün'),T('Satış fiyatı'),T('Alış fiyatı'),T('Toplam stok'),T('Durum')]);self.body.addWidget(self.grid,1)
        self.detail=QLabel('');self.detail.setWordWrap(True);self.body.addWidget(self.detail)
        actions=QHBoxLayout();self.create_button=self.button(T('Yeni Ürün'),self.create,actions);self.edit_button=self.button(T('Düzenle'),self.edit,actions)
        self.archive_button=self.button(T('Arşivle'),lambda:self.lifecycle('archive'),actions);self.restore_button=self.button(T('Yeniden Etkinleştir'),lambda:self.lifecycle('restore'),actions)
        self.delete_button=self.button(T('Kalıcı Sil'),lambda:self.lifecycle('delete'),actions);self.delete_button.setObjectName('tehlike');self.body.addLayout(actions)
        self.button(T('Ürünleri Yenile'),self.refresh)
        note=QLabel(T('Kalıcı silme yalnızca stoksuz ve işlem geçmişi olmayan ürünlerde kullanılabilir. Geçmişi olan ürünleri stokları bittikten sonra arşivleyebilirsiniz.'));note.setWordWrap(True);self.body.addWidget(note)
        self.search.textChanged.connect(self.filter);self.state.currentIndexChanged.connect(self.filter);self.grid.itemSelectionChanged.connect(self.selection_changed)
        self.grid.cellDoubleClicked.connect(lambda *_:self.edit());self.refresh()
    def refresh(self):
        selected=self.selected();self.selected_id=selected['id'] if selected else self.selected_id
        self.run(self.client.snapshot,self.populate)
    def populate(self,data):self.data=data;self.filter()
    def filter(self,*_):
        query=self.search.text().strip().casefold();state=self.state.currentIndex()
        self.visible_products=[p for p in self.data.get('products',[]) if (state==2 or bool(p['active'])==(state==0)) and (not query or query in (p['name']+' '+p['barcode']).casefold())]
        self.visible_products.sort(key=lambda p:(p['name'].casefold(),p['barcode']))
        totals={}
        for item in self.data.get('inventory',[]):totals[item['product_id']]=totals.get(item['product_id'],Decimal(0))+Decimal(str(item['quantity']))
        self.grid.blockSignals(True)
        rows(self.grid,[(p['barcode'].replace('\n',' ↵ ').replace('\r','').replace('\t',' ⇥ '),p['name'],f"{float(p.get('sale_price',0)):.2f}",f"{float(p.get('purchase_price',0)):.2f}",quantity_text(totals.get(p['id'],0)),T('Aktif') if p['active'] else T('Arşivde')) for p in self.visible_products])
        self.grid.clearSelection();self.grid.setCurrentCell(-1,-1)
        for i,p in enumerate(self.visible_products):
            if p['id']==self.selected_id:self.grid.selectRow(i);break
        self.grid.blockSignals(False);self.selection_changed()
    def selected(self):
        index=self.grid.currentRow();return self.visible_products[index] if 0<=index<len(self.visible_products) else None
    def selection_changed(self):
        p=self.selected();role=getattr(getattr(self.client,'cloud',None),'role','viewer');admin=role in ('owner','admin')
        self.create_button.setEnabled(admin);self.edit_button.setEnabled(admin and p is not None)
        self.archive_button.setEnabled(admin and bool(p and p['active']));self.restore_button.setEnabled(admin and bool(p and not p['active']))
        self.delete_button.setEnabled(role=='owner' and p is not None)
        self.detail.setText(T('Seçili ürün: {name}',name=p['name']) if p else T('Düzenlemek veya kaldırmak için bir ürün seçin.'))
    def create(self):
        dialog=ProductEditor(self.client,parent=self)
        if dialog.exec()==QDialog.DialogCode.Accepted:self.selected_id=dialog.saved;self.search.clear();self.state.setCurrentIndex(0);self.refresh()
    def edit(self):
        p=self.selected()
        if not p or not self.edit_button.isEnabled():return
        dialog=ProductEditor(self.client,p,self)
        if dialog.exec()==QDialog.DialogCode.Accepted:self.selected_id=dialog.saved;self.refresh()
    def lifecycle(self,operation):
        p=self.selected()
        if not p:return
        if operation=='delete':
            text,ok=QInputDialog.getText(self,T('Kalıcı Sil'),T('“{name}” kalıcı olarak silinecek. Onaylamak için SİL yazın.',name=p['name']))
            if not ok or text.strip()!='SİL':return
        else:
            message=T('“{name}” satış listesinden kaldırılıp arşivlensin mi? Geçmiş kayıtlar korunur.',name=p['name']) if operation=='archive' else T('“{name}” yeniden satışa açılsın mı?',name=p['name'])
            if QMessageBox.question(self,T('Ürün durumu'),message)!=QMessageBox.StandardButton.Yes:return
        self.mutation('catalog_manage',{'operation':operation,'product_id':p['id'],'expected':expected_product(p)},lambda _:self.refresh())
