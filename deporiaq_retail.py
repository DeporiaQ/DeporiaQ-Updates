"""Optional retail dashboard panels with shared, server-authoritative state."""
import copy,json
from decimal import Decimal
from PySide6.QtCore import QObject,QTimer,Signal,Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QSpinBox,QDoubleSpinBox,QCompleter,QAbstractItemView
from deporiaq_i18n import T,render,QLabel,QPushButton,QLineEdit,QComboBox,QMessageBox,QInputDialog
from deporiaq_commerce_ui import Job,table,rows,quantity_control
from deporiaq_retail_model import find_products,money,warehouse_scene

class RetailHub(QObject):
    updated=Signal(dict)
    def __init__(self,window):
        super().__init__(window);self.window=window;self.client=window.commerce;self.data={};self.job=None;self.error='';self.panels={}
        self.timer=QTimer(self);self.timer.timeout.connect(self.refresh);self.timer.start(10000)
    def refresh(self):
        if self.job is not None or not self.client.cloud.bagli:return
        self.job=Job(lambda:self.client.read('retail_snapshot'),self);self.job.finished.connect(self.finished);self.job.start()
    def finished(self):
        job=self.job;self.job=None
        if job.error:self.error=job.error
        else:self.error='';self.accept(job.result)
        job.deleteLater()
    def accept(self,data):self.data=data;self.updated.emit(data)
    def open(self,key):
        from deporiaq_warehouse import WarehouseDialog
        from deporiaq_retail_ui import OffersDialog,FinanceDialog,CustomersDialog
        if key=='pos':return self.window.panel_canvas.open_panel('retail_pos')
        cls={'warehouse':WarehouseDialog,'campaigns':OffersDialog,'bundles':OffersDialog,'accounts':FinanceDialog,'customers':CustomersDialog}[key]
        dialog=cls(self,key=='bundles',self.window) if key in ('campaigns','bundles') else cls(self,self.window)
        try:dialog.exec()
        finally:dialog.deleteLater();self.refresh()
    def install(self,canvas):
        for key,title in [('warehouse',T('3D Raf ve Doluluk')),('pos',T('Satış Kasası')),('campaigns',T('Kampanyalar')),('bundles',T('Set ve Paketler')),('accounts',T('Mali Tablo')),('customers',T('Müşteriler ve Üyelik'))]:
            widget=SalePanel(self) if key=='pos' else RetailTile(self,key,title)
            opener=None if key=='pos' else lambda k=key:self.open(k)
            canvas.add('retail_'+key,title,widget,(0,920,800,460),(420,330),visible=False,opener=opener);self.panels[key]=widget

class RetailTile(QWidget):
    def __init__(self,hub,key,title):
        super().__init__();self.hub=hub;self.key=key;self.layout_=QVBoxLayout(self);self.summary=QLabel();self.summary.setWordWrap(True);self.layout_.addWidget(self.summary)
        if key=='warehouse':
            from deporiaq_warehouse import WarehouseView
            self.location=QComboBox();self.layout_.addWidget(self.location);self.view=WarehouseView(miniature=True);self.layout_.addWidget(self.view,1)
            self.location.currentIndexChanged.connect(self.render);self.view.expanded.connect(lambda:hub.open(key))
        else:self.layout_.addStretch()
        button=QPushButton(T('Aç'));button.clicked.connect(lambda:hub.open(key));self.layout_.addWidget(button)
        hub.updated.connect(self.loaded);self.loaded(hub.data)
    def loaded(self,data):
        if self.key=='warehouse':
            previous=self.location.currentData();self.location.blockSignals(True);self.location.clear()
            for l in data.get('locations',[]):
                if l['active']:self.location.addItem(l['name'],l['id'])
            if previous:self.location.setCurrentIndex(max(0,self.location.findData(previous)))
            self.location.blockSignals(False)
        self.render()
    def render(self,*args):
        data=self.hub.data
        if self.key=='warehouse':
            layout=next((x for x in data.get('layouts',[]) if x['location_id']==self.location.currentData()),None)
            if layout:
                scene=warehouse_scene(layout,data.get('shelves',[]),data.get('products',[]));self.summary.setText(T('Raf doluluğu %{rate:.1f} · {count} adet yerleşmiş',rate=scene['occupancy'],count=scene['placed']));self.view.display(layout,data.get('shelves',[]),data.get('products',[]))
            else:self.summary.setText(T('Raf planınızı oluşturun; boş alanları ve ürün yerlerini 3D görün.'))
        elif self.key in ('campaigns','bundles'):
            kind='campaign' if self.key=='campaigns' else 'bundle';count=sum(x['kind']==kind and x['active'] for x in data.get('offers',[]));self.summary.setText(T('{count} etkin tanım · Fiyat ve maliyet satış anında yeniden kontrol edilir.',count=count))
        elif self.key=='accounts':self.summary.setText(T('Bugün, bu hafta, bu ay ve bu yıl: satış, iade, maliyet ve giderler. Şube ve satış kanalı kırılımları.'))
        else:self.summary.setText(T('Müşteri kartları, gönüllü üyelik ve ayrı e-posta / SMS izinleri.'))

class SalePanel(QWidget):
    """Scanner input stays responsive while a quote is in flight; stale quotes cannot sell."""
    def __init__(self,hub):
        super().__init__();self.hub=hub;self.job=None;self.lines=[];self.revision=0;self.quote=None;self.customer=None;self.last_receipt=None;self.draft_loaded=False;self.draft_key=None
        self.setStyleSheet("QPushButton{padding:6px 8px;font-size:12px;} QLabel#retailTotal{font-size:22px;font-weight:700;}")
        layout=QVBoxLayout(self);self.location=QComboBox();self.channel=QComboBox();row=QHBoxLayout();row.addWidget(self.location,1);row.addWidget(self.channel,1);layout.addLayout(row)
        self.barcode=QLineEdit();self.barcode.setPlaceholderText(T('Barkod okutun, ürün adı veya barkod yazın…'));self.barcode.returnPressed.connect(self.add)
        self.qty=QSpinBox();self.qty.setRange(1,1000000);row=QHBoxLayout();row.addWidget(self.barcode,1);row.addWidget(self.qty);layout.addLayout(row)
        row=QHBoxLayout()
        for label,fn in [(T('Ekle'),self.add),(T('Adet'),self.quantity),(T('Kaldır'),self.remove),(T('Set Ekle'),self.add_bundle),(T('Müşteri'),self.choose_customer)]:
            button=QPushButton(label);button.clicked.connect(fn);row.addWidget(button)
        layout.addLayout(row)
        self.grid=table([T('Ürün'),T('Adet'),T('Tutar')]);self.grid.setMinimumHeight(90);layout.addWidget(self.grid,1)
        self.total=QLabel(T('Sepet boş'));self.total.setObjectName('retailTotal');layout.addWidget(self.total)
        self.message=QLabel();self.message.setWordWrap(True);layout.addWidget(self.message)
        row=QHBoxLayout();self.cash=QDoubleSpinBox();self.card=QDoubleSpinBox()
        for label,control in [(T('Nakit'),self.cash),(T('Kart'),self.card)]:control.setRange(0,1000000000);control.setDecimals(2);row.addWidget(QLabel(label));row.addWidget(control)
        layout.addLayout(row);row=QHBoxLayout()
        for label,fn in [(T('Nakit'),lambda:self.fill('cash')),(T('Kart'),lambda:self.fill('card')),(T('Hesapla'),self.changed),(T('Fiş / İade'),self.receipt)]:
            button=QPushButton(label);button.clicked.connect(fn);row.addWidget(button)
        self.sell_button=QPushButton(T('Satışı Tamamla'));self.sell_button.setObjectName('basari');self.sell_button.clicked.connect(self.sell);row.addWidget(self.sell_button);layout.addLayout(row)
        self.debounce=QTimer(self);self.debounce.setSingleShot(True);self.debounce.setInterval(150);self.debounce.timeout.connect(self.request_quote)
        self.location.currentIndexChanged.connect(self.changed);self.channel.currentIndexChanged.connect(self.changed);hub.updated.connect(self.loaded);self.loaded(hub.data)
    def loaded(self,data):
        for combo,items in [(self.location,[x for x in data.get('locations',[]) if x['active'] and x['id'] in data.get('sale_locations',[])]),(self.channel,[x for x in data.get('channels',[]) if x['active']])]:
            previous=combo.currentData();combo.blockSignals(True);combo.clear()
            if combo is self.channel:combo.addItem(T('Mağaza / Doğrudan'),None)
            for item in items:combo.addItem(item['name'],item['id'])
            if previous:combo.setCurrentIndex(combo.findData(previous))
            combo.blockSignals(False)
        if data and not self.draft_loaded:
            self.draft_loaded=True
            self.draft_key='retail_cart_'+str(self.hub.client.cloud.company_id)+'_'+str(self.hub.window.kullanici['id'])
            try:
                draft=json.loads(self.hub.window.vt.ayar_getir(self.draft_key,'{}'))
                self.lines=[x for x in draft.get('items',[]) if isinstance(x,dict) and type(x.get('quantity')) is int and 1<=x['quantity']<=1000000 and bool(x.get('product_id') or x.get('bundle_id'))][:200]
                if draft.get('location_id'):self.location.setCurrentIndex(self.location.findData(draft['location_id']))
                if draft.get('channel_id'):self.channel.setCurrentIndex(self.channel.findData(draft['channel_id']))
                if self.lines:self.changed()
            except (ValueError,TypeError,AttributeError):self.lines=[]
        self.render()
    def persist(self):
        if self.draft_key:
            payload=self.payload();payload.pop('customer_id',None)
            self.hub.window.vt.ayar_kaydet(self.draft_key,json.dumps(payload));self.hub.window.vt.baglanti.commit()
    def add(self):
        found=find_products(self.hub.data.get('products',[]),self.barcode.text())
        if not found:self.message.setText(T('Ürün bulunamadı. Ürün adı veya barkodunu kontrol edin.'));return
        if len(found)>1:
            names=[p['barcode']+' · '+p['name'] for p in found];name,ok=QInputDialog.getItem(self,T('Ürün Seç'),T('Birden fazla ürün bulundu:'),names,0,False)
            if not ok:return
            product=found[names.index(name)]
        else:product=found[0]
        key=product['id'];line=next((x for x in self.lines if x.get('product_id')==key),None)
        if line:line['quantity']+=self.qty.value()
        else:self.lines.append(dict(product_id=key,quantity=self.qty.value()))
        self.qty.setValue(1);self.barcode.clear();self.barcode.setFocus();self.changed()
    def quantity(self):
        row=self.grid.currentRow()
        if row<0:return
        value,ok=QInputDialog.getInt(self,T('Adet'),T('Yeni adet:'),self.lines[row]['quantity'],1,1000000)
        if ok:self.lines[row]['quantity']=value;self.changed()
    def remove(self):
        row=self.grid.currentRow()
        if row>=0:self.lines.pop(row);self.changed()
    def add_bundle(self):
        bundles=[b for b in self.hub.data.get('offers',[]) if b['kind']=='bundle' and b['active']]
        if not bundles:self.message.setText(T('Etkin set bulunamadı. Set ve Paketler panelinden oluşturun.'));return
        names=[b['name']+' · '+b['id'][:8] for b in bundles];name,ok=QInputDialog.getItem(self,T('Set Ekle'),T('Set / Paket'),names,0,False)
        if ok:
            bid=bundles[names.index(name)]['id'];line=next((x for x in self.lines if x.get('bundle_id')==bid),None)
            if line:line['quantity']+=self.qty.value()
            else:self.lines.append(dict(bundle_id=bid,quantity=self.qty.value()))
            self.qty.setValue(1);self.changed()
    def choose_customer(self):
        from deporiaq_retail_ui import CustomerPicker
        dialog=CustomerPicker(self.hub.client,self);dialog.exec()
        if dialog.chosen is not None:self.customer=dialog.chosen or None;self.changed()
        dialog.deleteLater()
    def payload(self):
        return dict(location_id=self.location.currentData(),channel_id=self.channel.currentData(),customer_id=self.customer['id'] if self.customer else None,items=copy.deepcopy(self.lines))
    def changed(self,*args):
        self.revision+=1;self.quote=None;self.persist();self.render();self.debounce.start()
    def render(self):
        products={p['id']:p for p in self.hub.data.get('products',[])};offers={o['id']:o for o in self.hub.data.get('offers',[])};display=[]
        for line in self.lines:
            name=(products.get(line.get('product_id')) or offers.get(line.get('bundle_id')) or {}).get('name',T('Ürün bulunamadı'))
            total=None
            if self.quote:
                matching=[x for x in self.quote['lines'] if (line.get('bundle_id') and x.get('bundle_id')==line['bundle_id']) or (not line.get('bundle_id') and not x.get('bundle_id') and x['product_id']==line.get('product_id'))]
                total=sum((Decimal(str(x['price']))*x['quantity'] for x in matching),Decimal(0))
            display.append((name,line['quantity'],money(total) if total is not None else '…'))
        selected=self.grid.currentRow();rows(self.grid,display)
        if 0<=selected<len(display):self.grid.selectRow(selected)
        self.total.setText(T('Toplam: {amount}',amount=money(self.quote['total'])) if self.quote else T('Tutar hesaplanıyor…') if self.lines else T('Sepet boş'))
        self.sell_button.setEnabled(bool(self.quote) and self.job is None)
    def request_quote(self):
        if self.job is not None:return
        if not self.lines:self.quote=None;self.render();return
        payload=self.payload();revision=self.revision
        self.job=Job(lambda:self.hub.client.read('retail_quote',payload),self);self.job.finished.connect(lambda:self.quoted(revision));self.job.start()
    def quoted(self,revision):
        job=self.job;self.job=None
        if revision==self.revision:
            if job.error:self.message.setText(job.error);self.quote=None
            else:self.quote=job.result;self.message.setText((self.customer['name']+' · '+render(T('Üyelik uygulanır')) if self.customer else render(T('Ödeme alındığında satışı tamamlayın.'))))
            self.render()
        else:self.debounce.start()
        job.deleteLater()
    def fill(self,kind):
        if self.quote:
            self.cash.setValue(float(self.quote['total']) if kind=='cash' else 0);self.card.setValue(float(self.quote['total']) if kind=='card' else 0)
    def sell(self):
        if self.job is not None or not self.quote:return
        payload=self.payload();payload.update(fingerprint=self.quote['fingerprint'],payments=[{'type':'cash','amount':str(self.cash.value())},{'type':'card','amount':str(self.card.value())}])
        if Decimal(str(self.cash.value()))+Decimal(str(self.card.value()))!=Decimal(str(self.quote['total'])):self.message.setText(T('Nakit ve kart toplamı sepet tutarıyla eşleşmeli.'));return
        if QMessageBox.question(self,T('Satışı Tamamla'),T('{amount} ödeme alındı mı? Satış ve stok hareketi kaydedilecek.',amount=money(self.quote['total'])))!=QMessageBox.StandardButton.Yes:return
        self.setEnabled(False);self.job=Job(lambda:self.hub.client.mutate('retail_sale',payload),self);self.job.finished.connect(self.sold);self.job.start()
    def sold(self):
        job=self.job;self.job=None;self.setEnabled(True)
        if job.error:self.message.setText(job.error)
        else:
            self.last_receipt=job.result['id'];self.lines=[];self.quote=None;self.customer=None;self.cash.setValue(0);self.card.setValue(0)
            self.persist();self.message.setText(T('Satış kaydedildi · İşlem: ')+self.last_receipt);self.hub.refresh()
        self.render();self.barcode.setFocus();job.deleteLater()
    def receipt(self):
        from deporiaq_retail_ui import ReceiptDialog
        rid=self.last_receipt
        if not rid:
            rid,ok=QInputDialog.getText(self,T('Satış Fişi'),T('İşlem kimliği:'))
            if not ok or not rid.strip():return
        dialog=ReceiptDialog(self.hub,rid,self);dialog.exec();dialog.deleteLater()
