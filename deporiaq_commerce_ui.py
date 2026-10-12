"""0.24 commerce dialogs. All mutations go through checked server RPCs."""
from PySide6.QtCore import QThread, Signal, Qt, QUrl, QTimer
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import time
import csv
from PySide6.QtGui import QDesktopServices,QShortcut,QKeySequence
from urllib.parse import urlencode
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QPushButton,QComboBox,
 QLineEdit,QSpinBox,QDoubleSpinBox,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,
 QMessageBox,QInputDialog,QTabWidget,QWidget,QCheckBox,QPlainTextEdit,QSizePolicy,QApplication,QFileDialog)
from deporiaq_commerce import PLANS,CommerceError

def quantity_text(value):
    number=Decimal(str(value))
    return format(number,'f').rstrip('0').rstrip('.') if '.' in format(number,'f') else format(number,'f')

def csv_cell(value):
    text=str(value)
    return "'"+text if text.startswith(('=','+','-','@','\t','\r')) else text

class SubscriptionClock:
    def __init__(self,status,clock=time.monotonic):
        self.status=status;self.clock=clock;self.started=clock()
        parse=lambda value:datetime.fromisoformat(str(value).replace('Z','+00:00'))
        self.end=parse(status['valid_until']) if status.get('valid_until') else None
        self.server=parse(status['server_time']) if status.get('server_time') else None
    def seconds(self):
        if self.end is None or self.server is None:return None
        return max(0,int((self.end-self.server).total_seconds()-(self.clock()-self.started)))
    def text(self):
        seconds=self.seconds()
        if seconds is None:return 'Geri sayım için sunucu saati bekleniyor.'
        if seconds==0:return 'Paket süresi doldu.'
        days,seconds=divmod(seconds,86400);hours,seconds=divmod(seconds,3600);minutes,_=divmod(seconds,60)
        return f'Kalan süre: {days} gün {hours} saat {minutes} dakika'

class Job(QThread):
    def __init__(self,fn,parent):
        super().__init__(parent); self.fn=fn; self.result=None; self.error=None
    def run(self):
        try:self.result=self.fn()
        except Exception as e:self.error=str(e)

class ServerDialog(QDialog):
    def __init__(self,client,title,parent=None):
        super().__init__(parent);self.client=client;self.job=None;self.setWindowTitle(title);self.resize(960,650)
        self.refresh_shortcut=QShortcut(QKeySequence('F5'),self);self.refresh_shortcut.activated.connect(lambda:getattr(self,'refresh',lambda:None)())
        self.layout_=QVBoxLayout(self);self.heading=QLabel(title);self.heading.setObjectName('sayfaBaslik');self.heading.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Maximum);self.layout_.addWidget(self.heading)
        self.content=QWidget();self.body=QVBoxLayout(self.content);self.layout_.addWidget(self.content,1)
        self.status_label=QLabel('');self.status_label.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Maximum);self.status_label.setWordWrap(True);self.layout_.addWidget(self.status_label)
    def run(self,fn,done=None):
        if self.job is not None:return
        self.content.setEnabled(False);self.status_label.setText('Sunucudan yanıt bekleniyor…')
        self.job=Job(fn,self);self.job.finished.connect(lambda:self.finish(done));self.job.start()
    def finish(self,done):
        job=self.job;self.job=None;self.content.setEnabled(True)
        if job.error:self.status_label.setText(job.error)
        else:
            self.status_label.clear()
            if done:done(job.result)
        job.deleteLater()
    def closeEvent(self,event):
        if self.job is not None:event.ignore()
        else:super().closeEvent(event)
    def reject(self):
        if self.job is None:super().reject()
    def button(self,text,fn,layout=None):
        b=QPushButton(text);b.clicked.connect(fn);(layout or self.body).addWidget(b);return b
    def mutation(self,action,payload,done=None):
        self.run(lambda:self.client.mutate(action,payload),done)

def quantity_control(quantity):
    quantity.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
    quantity.setAlignment(Qt.AlignmentFlag.AlignCenter);quantity.setFixedWidth(130)
    quantity.setAccessibleName('Miktar')
    quantity_row=QWidget();quantity_layout=QHBoxLayout(quantity_row);quantity_layout.setContentsMargins(0,0,0,0)
    decrease=QPushButton('−');increase=QPushButton('+')
    for button,label in ((decrease,'Adedi azalt'),(increase,'Adedi artır')):
        button.setFixedSize(48,44);button.setAccessibleName(label);button.setToolTip(label)
        button.setAutoDefault(False);button.setStyleSheet('QPushButton {font-size:24px; border-radius:8px; padding:0px;}')
    decrease.clicked.connect(quantity.stepDown);increase.clicked.connect(quantity.stepUp)
    quantity_layout.addWidget(decrease);quantity_layout.addWidget(quantity);quantity_layout.addWidget(increase);quantity_layout.addStretch()
    return quantity_row,decrease,increase

def table(headers):
    t=QTableWidget(0,len(headers));t.setHorizontalHeaderLabels(headers)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    t.verticalHeader().hide();t.setAlternatingRowColors(True);t.setWordWrap(False)
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);return t

def rows(t,data):
    t.setRowCount(len(data))
    for r,values in enumerate(data):
        for c,value in enumerate(values):t.setItem(r,c,QTableWidgetItem(str(value)));t.item(r,c).setToolTip(str(value))

class PlansDialog(ServerDialog):
    def __init__(self,client=None,parent=None):
        super().__init__(client,'Paketim ve Abonelik',parent);self.resize(820,760)
        info=QLabel('İşletmenize uygun bilgisayar sayısını seçin. Demo: 30 gün, 1 bilgisayar.');info.setWordWrap(True);self.body.addWidget(info)
        t=table(['Paket','Bilgisayar','Kullanım']);t.setMinimumHeight(205);rows(t,[(name,n,desc) for code,name,n,desc in PLANS]);self.body.addWidget(t)
        self.summary=QLabel('Fiyatlar ve ödeme sağlayıcısı henüz yapılandırılmadı. Satın alma kapalı.');self.summary.setWordWrap(True);self.body.addWidget(self.summary)
        self.purchase=self.button('Paket Satın Al / Yükselt',lambda:None);self.purchase.setEnabled(False)
        self.cancel=self.button('Otomatik Yenilemeyi Sonlandır',self.cancel_renewal);self.cancel.setEnabled(False)
        self.device_table=table(['Cihaz','Durum','Kod']);self.body.addWidget(self.device_table)
        self.remove=self.button('Seçili Cihazın Erişimini Kapat',self.disable_device);self.remove.setEnabled(False)
        self.countdown=QLabel('');self.body.insertWidget(2,self.countdown)
        self.clock_timer=QTimer(self);self.clock_timer.timeout.connect(self.tick);self.clock_timer.start(1000)
        self.status_timer=QTimer(self);self.status_timer.timeout.connect(lambda:self.refresh() if self.client else None);self.status_timer.start(60000)
        if client:
            self.button('Destek Talebi',lambda:SupportDialog(client,self).exec())
            self.button('Bilgileri Yenile',self.refresh);self.refresh()
        else:self.status_label.setText('Paket bilgileri bilgilendirme amaçlıdır. Hesabınızla giriş yapın.')
    def refresh(self):self.run(self.client.status,self.show_status)
    def show_status(self,s):
        self.subscription_clock=SubscriptionClock(s)
        end=self.subscription_clock.end
        date=end.astimezone(timezone(timedelta(hours=3))).strftime('%d.%m.%Y %H:%M')+' (Türkiye)' if end else '—'
        plan=next((name for code,name,*_ in PLANS if code==s.get('plan')),s.get('plan') or 'Atanmamış')
        self.summary.setText(f"Paket: {plan}  •  Cihaz: {s.get('devices_used',0)}/{s.get('device_limit') or '—'}\n"
            f"Bitiş: {date}\n"+('Kullanım etkin.' if s.get('allowed') else 'İşletme işlemleri kapalı. Verileriniz korunur.'))
        self.tick()
        admin=s.get('role') in ('owner','admin');self.cancel.setEnabled(admin and bool(s.get('enabled')));self.remove.setEnabled(admin and bool(s.get('enabled')))
        if admin and s.get('enabled'):self.run(lambda:self.client.read('devices'),lambda ds:rows(self.device_table,[(d['name'],'Etkin' if d['active'] else 'Kapalı',d['code']) for d in ds]))
    def tick(self):
        clock=getattr(self,'subscription_clock',None)
        if clock is None:return
        self.countdown.setText(clock.text())
        seconds=clock.seconds();parent=self.parentWidget()
        if seconds is not None and parent and hasattr(parent,'notify') and seconds<=int(parent.vt.ayar_getir('notify_expiry_days','7'))*86400:
            parent.notify('Paket süresi','Paket bitişi yaklaşıyor. Kalan süreyi Paketim ve Abonelik ekranından kontrol edin.','notify_expiry')
    def cancel_renewal(self):
        if QMessageBox.question(self,'Yenilemeyi sonlandır','Ödenmiş sürenin sonuna kadar kullanım sürer. Veriler silinmez. Yenileme tercihini kapatalım mı?')!=QMessageBox.StandardButton.Yes:return
        self.mutation('renewal',{'renew':False},lambda _:self.refresh())
    def disable_device(self):
        r=self.device_table.currentRow()
        if r<0:return
        code=self.device_table.item(r,2).text()
        if QMessageBox.question(self,'Cihaz erişimi','Bu bilgisayarın sunucu işlemleri kapatılsın mı?')==QMessageBox.StandardButton.Yes:
            self.mutation('device_disable',{'code':code},lambda _:self.refresh())

class StockDialog(ServerDialog):
    def __init__(self,client,mode='sale',parent=None):
        titles={'sale':'Şube Satış','receive':'Stok Girişi','transfer':'Stok Transferi','count':'Stok Sayımı','catalog':'Stok ve Ürünler'}
        super().__init__(client,titles[mode],parent);self.mode=mode;self.data={}
        filters=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText('Ürün adı veya barkod ara…');self.search.setClearButtonEnabled(True)
        self.filter_location=QComboBox();self.filter_location.addItem('Tüm konumlar',None)
        self.filter_state=QComboBox();self.filter_state.addItems(['Tüm stoklar','Satılabilir stok var','Satılabilir stok yok','Rezervasyon var'])
        filters.addWidget(self.search,2);filters.addWidget(self.filter_location);filters.addWidget(self.filter_state);self.body.addLayout(filters)
        self.grid=table(['Konum','Barkod','Ürün','Fiziksel','Ayrılan','Satılabilir']);self.body.addWidget(self.grid,1)
        self.stock_summary=QLabel('');self.body.addWidget(self.stock_summary)
        actions=QHBoxLayout();self.button('Barkodu Kopyala',self.copy_barcode,actions);self.button('Görünen Stokları CSV Aktar',self.export_stock,actions);self.body.addLayout(actions)
        self.search.textChanged.connect(self.filter_stock);self.filter_location.currentIndexChanged.connect(self.filter_stock);self.filter_state.currentIndexChanged.connect(self.filter_stock)
        self.grid.itemSelectionChanged.connect(self.select_stock)
        f=QFormLayout();self.product=QComboBox();self.location=QComboBox();self.target=QComboBox();self.quantity=QSpinBox();self.quantity.setRange(0 if mode=='count' else 1,1000000)
        f.addRow('Ürün:',self.product);f.addRow('Kaynak / satış konumu:',self.location)
        if mode=='transfer':f.addRow('Hedef:',self.target)
        if mode!='catalog':
            quantity_row,self.decrease,self.increase=quantity_control(self.quantity)
            f.addRow('Miktar:',quantity_row)
        self.body.addLayout(f)
        if mode!='catalog':self.submit=self.button({'sale':'Satışı Tamamla','receive':'Stok Girişini Kaydet','transfer':'Transferi Tamamla','count':'Sayımı Kaydet'}[mode],self.commit)
        else:
            self.button('Ürün Ekle / Fiyat Güncelle',self.product_edit)
            self.button('Depo / Şube Ekle',self.location_edit)
        self.button('Stokları Yenile',self.refresh);self.refresh()
    def refresh(self):self.run(self.client.snapshot,self.populate)
    def populate(self,s):
        self.data=s;ps={p['id']:p for p in s['products']};ls={l['id']:l for l in s['locations']}
        self.stock_rows=[(i['product_id'],i['location_id'],ls[i['location_id']]['name'],ps[i['product_id']]['barcode'],ps[i['product_id']]['name'],i['quantity'],Decimal(str(i['quantity']))-Decimal(str(i['available'])),i['available']) for i in s['inventory']]
        previous=self.filter_location.currentData();self.filter_location.blockSignals(True);self.filter_location.clear();self.filter_location.addItem('Tüm konumlar',None)
        for location in s['locations']:self.filter_location.addItem(location['name'],location['id'])
        self.filter_location.setCurrentIndex(max(0,self.filter_location.findData(previous)));self.filter_location.blockSignals(False)
        old=[self.product.currentData(),self.location.currentData(),self.target.currentData()]
        self.product.clear();self.location.clear();self.target.clear()
        for p in s['products']:
            if p['active']:self.product.addItem(p['barcode']+' · '+p['name'],p['id'])
        for l in s['locations']:
            if l['active']:self.location.addItem(l['name'],l['id']);self.target.addItem(l['name'],l['id'])
        for combo,value in zip([self.product,self.location,self.target],old):
            if combo.findData(value)>=0:combo.setCurrentIndex(combo.findData(value))
        self.filter_stock()
        self.status_label.setText('Fiziksel: toplam stok · Ayrılan: rezervasyonlar · Satılabilir: satışa uygun stok.')
    def filter_stock(self,*_):
        query=self.search.text().strip().casefold();loc=self.filter_location.currentData();mode=self.filter_state.currentIndex()
        self.visible_stock=[]
        for row in getattr(self,'stock_rows',[]):
            if query and query not in (row[3]+' '+row[4]).casefold():continue
            if loc is not None and row[1]!=loc:continue
            available=Decimal(str(row[7]));reserved=Decimal(str(row[6]))
            if (mode==1 and available<=0) or (mode==2 and available>0) or (mode==3 and reserved<=0):continue
            self.visible_stock.append(row)
        rows(self.grid,[(r[2],r[3],r[4],quantity_text(r[5]),quantity_text(r[6]),quantity_text(r[7])) for r in self.visible_stock])
        total=sum((Decimal(str(r[7])) for r in self.visible_stock),Decimal(0))
        self.stock_summary.setText(f'{len(self.visible_stock)} kayıt · Satılabilir toplam: {quantity_text(total)} adet')
    def select_stock(self):
        r=self.grid.currentRow()
        if r<0 or r>=len(getattr(self,'visible_stock',[])):return
        row=self.visible_stock[r]
        for combo,value in ((self.product,row[0]),(self.location,row[1])):
            combo.setCurrentIndex(combo.findData(value))
    def copy_barcode(self):
        r=self.grid.currentRow()
        if r<0:self.status_label.setText('Önce stok tablosundan bir satır seçin.');return
        QApplication.clipboard().setText(self.grid.item(r,1).text());self.status_label.setText('Barkod kopyalandı.')
    def export_stock(self):
        path,_=QFileDialog.getSaveFileName(self,'Görünen stokları kaydet','DeporiaQ_Stok.csv','CSV (*.csv)')
        if not path:return
        try:
            with open(path,'w',newline='',encoding='utf-8-sig') as stream:
                writer=csv.writer(stream,delimiter=';');writer.writerow(['Konum','Barkod','Ürün','Fiziksel','Ayrılan','Satılabilir'])
                for r in range(self.grid.rowCount()):writer.writerow([csv_cell(self.grid.item(r,c).text()) for c in range(6)])
        except OSError as e:self.status_label.setText('Dosya kaydedilemedi: '+str(e));return
        self.status_label.setText('Görünen stoklar CSV dosyasına kaydedildi.')
    def commit(self):
        payload={'product_id':self.product.currentData(),'location_id':self.location.currentData(),'quantity':self.quantity.value()}
        if self.mode=='transfer':payload['target_id']=self.target.currentData()
        if self.mode=='count' and QMessageBox.question(self,'Sayım','Girilen miktar fiziksel toplamdır. Sayım sonucunu uygulayalım mı?')!=QMessageBox.StandardButton.Yes:return
        def completed(result):
            QMessageBox.information(self,'İşlem sunucuda tamamlandı',f"İşlem kaydedildi. Toplam: {result.get('total','—')}")
            self.refresh()
        self.mutation(self.mode,payload,completed)
    def product_edit(self):
        d=QDialog(self);d.setWindowTitle('Ürün Ekle / Güncelle');f=QFormLayout(d)
        barcode=QLineEdit();name=QLineEdit();sale=QDoubleSpinBox();cost=QDoubleSpinBox();critical=QSpinBox()
        for x in (sale,cost):x.setRange(0,10000000);x.setDecimals(2)
        critical.setRange(0,1000000)
        for label,x in [('Barkod',barcode),('Ad',name),('Satış fiyatı',sale),('Alış fiyatı',cost),('Kritik stok',critical)]:f.addRow(label,x)
        b=QPushButton('Kaydet');b.clicked.connect(d.accept);f.addRow(b)
        if d.exec()==QDialog.DialogCode.Accepted:self.mutation('catalog_product',{'barcode':barcode.text(),'name':name.text(),'sale_price':sale.value(),'purchase_price':cost.value(),'critical_stock':critical.value()},lambda _:self.refresh())
    def location_edit(self):
        name,ok=QInputDialog.getText(self,'Konum','Depo / şube adı:')
        if not ok:return
        typ,ok=QInputDialog.getItem(self,'Konum','Tür:',['Şube','Depo'],0,False)
        if ok:self.mutation('catalog_location',{'name':name,'type':'branch' if typ=='Şube' else 'warehouse'},lambda _:self.refresh())

class OrdersDialog(ServerDialog):
    def __init__(self,client,parent=None):
        super().__init__(client,'İnternet Satışları',parent);self.data={};self.order_ids=[];self.alloc_ids=[]
        self.note=QLabel('Elle girilen kanal siparişleri • Otomatik pazaryeri bağlantısı henüz yok.\nÖdeme bekleyen rezervasyon 30 dakika tutulur.');self.note.setWordWrap(True);self.body.addWidget(self.note)
        self.tabs=QTabWidget();self.body.addWidget(self.tabs)
        order_page=QWidget();o=QVBoxLayout(order_page)
        self.orders=table(['Sipariş','Müşteri','Durum','Gönderim']);o.addWidget(self.orders);self.orders.itemSelectionChanged.connect(self.select_order)
        self.allocations=table(['Ürün','Konum','Adet','Durum']);o.addWidget(self.allocations)
        bar=QHBoxLayout();o.addLayout(bar)
        for text,action in [('Yeni Sipariş',self.new_order),('Ödemeyi Doğruladım / Hazırla',lambda:self.order_action('order_prepare')),('İptal',lambda:self.order_action('order_cancel')),('Teslim Edildi',lambda:self.order_action('order_complete'))]:self.button(text,action,bar)
        bar=QHBoxLayout();o.addLayout(bar)
        for text,action in [('Merkeze Sevk',lambda:self.allocation_action('allocation_dispatch')),('Merkez Teslim Aldı',lambda:self.allocation_action('allocation_receive')),('Kargoya Ver',lambda:self.allocation_action('allocation_ship')),('İadeyi Teslim Aldım',lambda:self.allocation_action('allocation_return'))]:self.button(text,action,bar)
        self.tabs.addTab(order_page,'Siparişler')
        channels_page=QWidget();c=QVBoxLayout(channels_page);self.channels=table(['Kanal','Durum','Bağlantı']);c.addWidget(self.channels)
        self.button('Kanal Ekle / Konumları Düzenle',self.channel_edit,c);self.button('Seçili Kanalı Arşivle',self.channel_archive,c);self.tabs.addTab(channels_page,'Satış Kanalları')
        self.button('Bilgileri Yenile',self.refresh);self.button('Bekleyen İşlemi Kontrol Et',lambda:self.run(self.client.reconcile,lambda _:self.refresh()));self.refresh()
    def refresh(self):self.run(self.client.snapshot,self.populate)
    def populate(self,s):
        self.data=s;self.order_ids=[x['id'] for x in s['orders']]
        self.orders.blockSignals(True);rows(self.orders,[(x['reference'],x['customer'],{'reserved':'Ödeme bekliyor','preparing':'Hazırlanıyor','expired':'Rezervasyon doldu','cancelled':'İptal','shipped':'Gönderildi','completed':'Tamamlandı'}[x['status']],'Merkezde birleştir' if x['shipping']=='consolidate' else 'Ayrı gönder') for x in s['orders']]);self.orders.blockSignals(False)
        rows(self.channels,[(x['name'],'Etkin' if x['active'] else 'Arşiv','Elle giriş') for x in s['channels']]);rows(self.allocations,[])
    def selected(self):
        r=self.orders.currentRow()
        return next((x for x in self.data.get('orders',[]) if r>=0 and x['id']==self.order_ids[r]),None)
    def select_order(self):
        order=self.selected()
        if not order:return
        self.alloc_ids=[x['id'] for x in order['allocations']];ps={p['id']:p['name'] for p in self.data['products']};ls={l['id']:l['name'] for l in self.data['locations']}
        names={'reserved':'Ayrıldı','transit':'Yolda','shipped':'Kargoda','released':'Serbest','returned':'İade alındı'}
        rows(self.allocations,[(ps[x['product_id']],ls[x['location_id']],x['quantity'],names[x['state']]) for x in order['allocations']])
    def order_action(self,action):
        order=self.selected()
        if not order:return
        if QMessageBox.question(self,'Sipariş işlemi','Seçili siparişte bu işlemi onaylıyor musunuz?'+('\nBu onay, ödemeyi dış kanalda gerçekten kontrol ettiğiniz anlamına gelir.' if action=='order_prepare' else ''))!=QMessageBox.StandardButton.Yes:return
        self.mutation(action,{'order_id':order['id']},lambda _:self.refresh())
    def allocation_action(self,action):
        order=self.selected();r=self.allocations.currentRow()
        if not order or r<0:return
        payload={'order_id':order['id'],'allocation_id':self.alloc_ids[r]}
        if action=='allocation_ship':
            carrier,ok=QInputDialog.getText(self,'Kargo','Firma:')
            if not ok:return
            tracking,ok=QInputDialog.getText(self,'Kargo','Takip numarası:')
            if not ok:return
            payload.update(carrier=carrier,tracking=tracking)
        if action=='allocation_return':
            if QMessageBox.question(self,'İade kontrolü','Bu satırdaki ürünlerin TAMAMINI fiziksel olarak teslim alıp satışa uygunluğunu kontrol ettiniz mi?')!=QMessageBox.StandardButton.Yes:return
            payload['inspected']=True
        if action in ('allocation_dispatch','allocation_receive') and QMessageBox.question(self,'Fiziksel hareket','Seçili satırın tamamı için fiziksel sevk / teslim işlemi gerçekleşti mi?')!=QMessageBox.StandardButton.Yes:return
        self.mutation(action,payload,lambda _:self.refresh())
    def channel_edit(self):
        d=QDialog(self);d.setWindowTitle('Kanal ve Satışa Açık Konumlar');v=QVBoxLayout(d);name=QLineEdit();name.setPlaceholderText('Örn. Instagram');v.addWidget(name)
        boxes=[]
        for l in self.data['locations']:
            if l['active']:
                b=QCheckBox(l['name']);v.addWidget(b);boxes.append((b,l['id']))
        buffer=QSpinBox();buffer.setRange(0,1000000);v.addWidget(QLabel('Her konumda satışa açılmayacak güvenlik stoğu:'));v.addWidget(buffer)
        channel_id=None;r=self.channels.currentRow()
        if r>=0:
            channel=self.data['channels'][r];channel_id=channel['id'];name.setText(channel['name'])
        v.addWidget(QLabel('Konumları yeniden seçin. Seçilmemiş konum internet satışına açılmaz.'))
        b=QPushButton('Kaydet');b.clicked.connect(d.accept);v.addWidget(b)
        if d.exec()==QDialog.DialogCode.Accepted:
            payload={'name':name.text(),'locations':[{'id':i,'buffer':buffer.value()} for box,i in boxes if box.isChecked()]}
            if channel_id:payload['channel_id']=channel_id
            self.mutation('channel_save',payload,lambda _:self.refresh())
    def channel_archive(self):
        r=self.channels.currentRow()
        if r<0:return
        if QMessageBox.question(self,'Kanalı arşivle','Yeni sipariş girişi kapanır. Geçmiş ve açık siparişler korunur. Devam edilsin mi?')==QMessageBox.StandardButton.Yes:
            self.mutation('channel_archive',{'channel_id':self.data['channels'][r]['id']},lambda _:self.refresh())
    def new_order(self):
        d=QDialog(self);d.setWindowTitle('İnternet Siparişi');d.resize(650,500);v=QVBoxLayout(d);f=QFormLayout();v.addLayout(f)
        channel=QComboBox();reference=QLineEdit();customer=QLineEdit();address=QLineEdit();shipping=QComboBox()
        for c in self.data['channels']:
            if c['active']:channel.addItem(c['name'],c['id'])
        shipping.addItem('Merkezde birleştir','consolidate');shipping.addItem('Ayrı gönder','split')
        for label,w in [('Kanal',channel),('Kanal sipariş numarası',reference),('Müşteri',customer),('Teslimat adresi',address),('Gönderim',shipping)]:f.addRow(label,w)
        product=QComboBox();quantity=QSpinBox();quantity.setRange(1,1000000)
        for p in self.data['products']:
            if p['active']:product.addItem(p['barcode']+' · '+p['name'],p['id'])
        f.addRow('Ürün',product);f.addRow('Adet',quantity);items=[];t=table(['Ürün','Adet']);v.addWidget(t)
        def add():
            if product.currentData():items.append({'product_id':product.currentData(),'quantity':quantity.value()});rows(t,[(next(p['name'] for p in self.data['products'] if p['id']==x['product_id']),x['quantity']) for x in items])
        b=QPushButton('Satır Ekle');b.clicked.connect(add);v.addWidget(b)
        b=QPushButton('Stokları Rezerve Et');b.clicked.connect(d.accept);v.addWidget(b)
        if d.exec()==QDialog.DialogCode.Accepted:self.mutation('reserve',{'channel_id':channel.currentData(),'reference':reference.text(),'customer':customer.text(),'address':address.text(),'shipping':shipping.currentData(),'items':items},lambda _:self.refresh())

class SupportDialog(ServerDialog):
    def __init__(self,client,parent=None):
        super().__init__(client,'Destek Talebi',parent);self.resize(650,500)
        self.body.addWidget(QLabel('Müşteri desteği: deporiaq@gmail.com'))
        f=QFormLayout();self.subject=QLineEdit();self.message=QPlainTextEdit();self.contact=QLineEdit()
        f.addRow('Konu',self.subject);f.addRow('Açıklama',self.message);f.addRow('İletişim',self.contact);self.body.addLayout(f)
        self.subject.setPlaceholderText('En az 3 karakter: ör. Satış ekranı sorunu')
        self.message.setPlaceholderText('En az 5 karakter: ne yaptığınızı ve gördüğünüz hatayı yazın')
        self.body.addWidget(QLabel('Destek adresi: deporiaq@gmail.com · Gönderim durumu aşağıda gösterilir.'))
        self.send_button=self.button('Gönder',self.send);self.send_button.setObjectName('birincil')
    def valid(self):
        for value,minimum,maximum,label in [(self.subject.text().strip(),3,200,'Konu'),(self.message.toPlainText().strip(),5,10000,'Açıklama'),(self.contact.text().strip(),3,300,'İletişim')]:
            if not minimum<=len(value)<=maximum:
                self.status_label.setText(f'{label} {minimum}–{maximum} karakter olmalı.');return False
        return True
    def email_draft(self):
        if not self.valid():return
        query=urlencode({'subject':self.subject.text().strip(),'body':self.message.toPlainText().strip()+'\n\nİletişim: '+self.contact.text().strip()})
        opened=QDesktopServices.openUrl(QUrl('mailto:deporiaq@gmail.com?'+query.replace('+','%20')))
        self.status_label.setText('E-posta uygulamasında taslak açıldı; göndermek için uygulamanızdaki Gönder düğmesini kullanın.' if opened else 'E-posta uygulaması açılamadı. deporiaq@gmail.com adresine kendiniz yazabilirsiniz.')
    def send(self):
        if not self.valid():return
        self.mutation('support',{'subject':self.subject.text().strip(),'message':self.message.toPlainText().strip(),'contact':self.contact.text().strip()},self.sent)
    def sent(self,result):self.status_label.setText(f"Talep kaydedildi: {result['id']}\nE-posta bildirimi: gönderim bekliyor. Bu durum e-postanın teslim edildiği anlamına gelmez.")

class SaleDialog(ServerDialog):
    """Cashier starts with an exact barcode. Other stores are an explicit lookup."""
    def __init__(self,client,location_name='',parent=None):
        super().__init__(client,'Kasa · Barkodlu Satış',parent);self.resize(900,360)
        self.body.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.data={};self.selected_product=None;self.location_name=location_name;self.other_ids=[]
        f=QFormLayout();self.location=QComboBox();self.barcode=QLineEdit();self.barcode.setPlaceholderText('Ürün barkodunu okutun veya barkod girip Enter’a basın')
        self.quantity=QSpinBox();self.quantity.setRange(1,1000000)
        quantity_row,self.decrease,self.increase=quantity_control(self.quantity)
        f.addRow('Satış yapılan mağaza / depo',self.location);f.addRow('Ürün barkodu',self.barcode);f.addRow('Adet',quantity_row);self.body.addLayout(f)
        self.info=QLabel('Satışa başlamak için barkod okutun.');self.info.setWordWrap(True);self.info.setMinimumHeight(70);self.body.addWidget(self.info)
        bar=QHBoxLayout();self.body.addLayout(bar)
        self.button('Ürünü Bul',self.lookup,bar);self.sell=self.button('Satışı Tamamla',self.commit,bar);self.sell.setObjectName('basari');self.sell.setEnabled(False)
        self.button('Satışı İptal / Temizle',self.clear_sale,bar)
        bar=QHBoxLayout();self.body.addLayout(bar)
        self.button('Ürün Adıyla Bul',self.find_by_name,bar);self.button('Şube / Depo Stoklarını Sorgula',self.other_stock,bar)
        self.button('Rezervasyonlar ve Teslimatlar',lambda:CounterOrdersDialog(client,self).exec(),bar)
        self.other=QWidget();v=QVBoxLayout(self.other);v.setContentsMargins(0,0,0,0)
        v.addWidget(QLabel('Seçili ürünün diğer konumlardaki güncel stoğu'))
        self.grid=table(['Şube / Depo','Satılabilir adet','Ayrılan adet']);v.addWidget(self.grid)
        bar=QHBoxLayout();v.addLayout(bar)
        self.pickup=self.button('Seçili Şubeden Teslim · Rezerve Et',lambda:self.reserve('pickup'),bar)
        self.cargo=self.button('Seçili Konumdan Kargo · Rezerve Et',lambda:self.reserve('cargo'),bar)
        self.body.addWidget(self.other);self.other.hide()
        self.cash_shortcuts=[]
        for key,action in [('F2',lambda:self.barcode.setFocus()),('F8',lambda:self.sell.click())]:
            shortcut=QShortcut(QKeySequence(key),self);shortcut.activated.connect(action);self.cash_shortcuts.append(shortcut)
        self.barcode.setToolTip('F2: barkod alanına dön · Enter: ürünü bul · F8: satışı tamamla')
        self.barcode.returnPressed.connect(self.lookup);self.barcode.textEdited.connect(self.invalidate)
        self.location.currentIndexChanged.connect(self.render_product);self.quantity.valueChanged.connect(self.render_product)
        self.refresh()
    def refresh(self):self.run(self.client.snapshot,self.populate)
    def populate(self,data):
        self.data=data;old=self.location.currentData();self.location.blockSignals(True);self.location.clear()
        allowed=data.get('sale_locations')
        for l in data['locations']:
            if l['active'] and (allowed is None or l['id'] in allowed):self.location.addItem(l['name'],l['id'])
        idx=self.location.findData(old) if old else self.location.findText(self.location_name)
        if idx>=0:self.location.setCurrentIndex(idx)
        self.location.blockSignals(False)
        self.resolve_product();self.barcode.setFocus()
    def invalidate(self,*_):
        self.selected_product=None;self.sell.setEnabled(False);self.other.hide();self.info.setText('Barkodu doğrulamak için Enter’a basın.')
    def lookup(self):
        if not self.barcode.text().strip():self.info.setText('Önce ürün barkodu girin.');self.barcode.setFocus();return
        self.refresh()
    def resolve_product(self):
        code=self.barcode.text().strip()
        self.selected_product=next((p for p in self.data.get('products',[]) if p['active'] and p['barcode']==code),None)
        self.render_product()
    def stock(self,location):
        pid=(self.selected_product or {}).get('id')
        return next((i for i in self.data.get('inventory',[]) if i['product_id']==pid and i['location_id']==location),{'quantity':0,'available':0})
    def render_product(self,*_):
        p=self.selected_product;self.sell.setEnabled(False)
        if not p:
            self.info.setText('Barkod kayıtlı ürünlerde bulunamadı. Barkodu kontrol edin veya ürün adıyla bulun.' if self.barcode.text().strip() else 'Satışa başlamak için barkod okutun.')
            return
        stock=self.stock(self.location.currentData());available=float(stock['available']);qty=self.quantity.value();price=float(p.get('sale_price',0))
        text=f"{p['name']}  ·  Barkod: {p['barcode']}\nBirim fiyat: {price:,.2f} TL  ·  {qty} adet toplam: {price*qty:,.2f} TL\n"
        if self.location.currentData() is None:text+='Bu hesap için satış konumu atanmamış. Yöneticinizle görüşün.'
        elif available<=0:text+='Ürün seçili mağaza / depo stoklarında satılabilir durumda bulunmamaktadır. Şube / Depo Stoklarını Sorgula seçeneğini kullanın.'
        elif qty>available:text+=f'Satılabilir stok: {available:g} adet. İstenen adet yetersiz stok nedeniyle satılamaz.'
        else:text+=f'Satılabilir stok: {available:g} adet.';self.sell.setEnabled(True)
        self.info.setText(text)
        if self.other.isVisible():self.show_other()
    def clear_sale(self):
        self.barcode.clear();self.quantity.setValue(1);self.selected_product=None;self.other.hide();self.render_product();self.barcode.setFocus()
    def find_by_name(self):
        products=[p for p in self.data.get('products',[]) if p['active']]
        names=[p['name']+' · '+p['barcode'] for p in products]
        name,ok=QInputDialog.getItem(self,'Ürün Adıyla Bul','Ürün adı yazın veya listeden seçin:',names,0,True)
        if not ok:return
        matches=[p for p in products if name in (p['name'],p['name']+' · '+p['barcode']) or name.casefold() in p['name'].casefold()]
        if len(matches)!=1:self.status_label.setText('Tek bir ürün seçin; aramayı daraltın.');return
        self.barcode.setText(matches[0]['barcode']);self.lookup()
    def other_stock(self):
        if not self.barcode.text().strip():self.info.setText('Barkod girin veya ürün adıyla bulun.');return
        def ready(data):self.populate(data);self.other.show();self.show_other()
        self.run(self.client.snapshot,ready)
    def show_other(self):
        values=[];self.other_ids=[]
        if self.selected_product:
            for loc in self.data.get('locations',[]):
                if not loc['active'] or loc['id']==self.location.currentData():continue
                row=self.stock(loc['id']);available=float(row['available'])
                if available<=0:continue
                self.other_ids.append(loc['id']);values.append((loc['name'],f'{available:g}',f"{float(row['quantity'])-available:g}"))
        rows(self.grid,values);self.pickup.setEnabled(bool(values));self.cargo.setEnabled(bool(values))
        if not values:self.status_label.setText('Ürün diğer mağaza ve depo stoklarında da satılabilir durumda bulunmamaktadır.')
    def commit(self):
        if not self.selected_product or not self.sell.isEnabled():return
        payload={'product_id':self.selected_product['id'],'location_id':self.location.currentData(),'quantity':self.quantity.value()}
        if QMessageBox.question(self,'Satışı Tamamla',self.info.text()+'\n\nÖdemeyi aldınız mı? Satışı kaydedelim mi?')!=QMessageBox.StandardButton.Yes:return
        def done(result):
            QMessageBox.information(self,'Satış Tamamlandı',f"Satış kaydedildi. Toplam: {result.get('total',0)} TL")
            self.clear_sale();self.refresh()
        self.mutation('sale',payload,done)
    def reserve(self,kind):
        r=self.grid.currentRow()
        if r<0 or not self.selected_product:self.status_label.setText('Önce stok bulunan şube / depo satırını seçin.');return
        loc=self.other_ids[r]
        if float(self.stock(loc)['available'])<self.quantity.value():self.status_label.setText('Seçili konumda bu adet için yeterli stok yok.');return
        d=QDialog(self);d.setWindowTitle('Şubeden Teslim Rezervasyonu' if kind=='pickup' else 'Kargo Rezervasyonu');f=QFormLayout(d)
        customer=QLineEdit();contact=QLineEdit();address=QPlainTextEdit()
        f.addRow('Müşteri adı',customer);f.addRow('Telefon / e-posta',contact)
        if kind=='cargo':f.addRow('Teslimat adresi',address)
        note=QLabel('Ürün 24 saat ayrılır. Bu adım ödeme veya teslimat kaydı oluşturmaz.');note.setWordWrap(True);f.addRow(note)
        b=QPushButton('Rezervasyonu Kaydet');f.addRow(b)
        def accept():
            if len(customer.text().strip())<2 or len(contact.text().strip())<3 or (kind=='cargo' and len(address.toPlainText().strip())<5):
                note.setText('Müşteri adı, iletişim ve kargo için açık adres girin.');return
            d.accept()
        b.clicked.connect(accept)
        if d.exec()!=QDialog.DialogCode.Accepted:return
        payload={'product_id':self.selected_product['id'],'location_id':self.location.currentData(),'target_id':loc,'quantity':self.quantity.value(),'delivery':kind,'customer':customer.text().strip(),'contact':contact.text().strip(),'address':address.toPlainText().strip()}
        def done(result):
            QMessageBox.information(self,'Rezervasyon Hazır',f"Rezervasyon numarası: {result['id']}\nSon teslim / kargolama zamanı: {result['expires_at']}\nRezervasyonlar ve Teslimatlar ekranından takip edebilirsiniz.")
            self.refresh()
        self.mutation('counter_reserve',payload,done)

class CounterOrdersDialog(ServerDialog):
    def __init__(self,client,parent=None):
        super().__init__(client,'Rezervasyonlar ve Teslimatlar',parent);self.entries=[]
        self.grid=table(['Numara','Müşteri','Teslim Konumu','Ürün / Adet','Teslimat','Durum']);self.body.addWidget(self.grid)
        self.details=QLabel('Bir rezervasyon seçin.');self.details.setWordWrap(True);self.body.addWidget(self.details);self.grid.itemSelectionChanged.connect(self.selected_details)
        bar=QHBoxLayout();self.body.addLayout(bar)
        for label,act in [('Şubeden Teslim Et','counter_collect'),('Kargoya Ver','counter_ship'),('Kargo Teslim Edildi','counter_complete'),('Rezervasyonu İptal Et','counter_cancel')]:
            self.button(label,lambda checked=False,a=act:self.action(a),bar)
        self.button('Yenile',self.refresh);self.button('Bekleyen İşlem Sonucunu Kontrol Et',lambda:self.run(self.client.reconcile,lambda _:self.refresh()));self.refresh()
    def refresh(self):self.run(self.client.snapshot,self.populate)
    def populate(self,data):
        self.entries=data.get('counter_orders',[]);ps={p['id']:p['name'] for p in data['products']};ls={l['id']:l['name'] for l in data['locations']}
        labels={'reserved':'Ayrıldı','shipped':'Kargoda','completed':'Teslim edildi','cancelled':'İptal','expired':'Süresi doldu'}
        rows(self.grid,[(o['id'][:8],o['customer'],ls.get(o['location_id'],''),f"{ps.get(o['product_id'],'')} / {o['quantity']}",'Şubeden teslim' if o['delivery']=='pickup' else 'Kargo',labels[o['status']]) for o in self.entries])
    def selected_details(self):
        r=self.grid.currentRow()
        if r<0:return
        o=self.entries[r];self.details.setText(f"Numara: {o['id']}\nİletişim: {o['contact']}  •  Son zaman: {o['expires_at']}\nAdres: {o.get('address','')}\nKargo: {o.get('carrier','')} {o.get('tracking','')}")
    def action(self,action):
        r=self.grid.currentRow()
        if r<0:return
        payload={'order_id':self.entries[r]['id']}
        if action=='counter_ship':
            carrier,ok=QInputDialog.getText(self,'Kargo','Kargo firması:')
            if not ok:return
            tracking,ok=QInputDialog.getText(self,'Kargo','Takip numarası:')
            if not ok:return
            if not carrier.strip() or not tracking.strip():self.status_label.setText('Kargo firması ve takip numarası gerekli.');return
            payload.update(carrier=carrier.strip(),tracking=tracking.strip())
        message='Seçili rezervasyona işlemi uygulayalım mı?'
        if action in ('counter_collect','counter_ship'):message='Ödemeyi aldınız ve ürünleri fiziksel olarak müşteriye / kargoya teslim ettiniz mi? Bu işlem stoğu düşürüp satış kaydeder.';payload['paid']=True
        if QMessageBox.question(self,'Teslimat işlemi',message)!=QMessageBox.StandardButton.Yes:return
        self.mutation(action,payload,lambda _:self.refresh())
