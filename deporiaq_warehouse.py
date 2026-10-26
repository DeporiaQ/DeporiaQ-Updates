"""Native, addressable 3D warehouse views and optimistic server-backed layout editor."""
import copy,sys
from pathlib import Path
from PySide6.QtCore import Qt,QUrl,Signal,QTimer
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QSpinBox,QDoubleSpinBox,
 QSplitter,QListWidget,QAbstractItemView,QTableWidget,QTableWidgetItem,QHeaderView,QApplication,QSizePolicy)
from deporiaq_i18n import T,render,QLabel,QPushButton,QLineEdit,QComboBox,QCheckBox,QMessageBox,QInputDialog
from deporiaq_commerce_ui import ServerDialog,table,rows
from deporiaq_retail_model import warehouse_scene,find_products,free_shelves

class WarehouseView(QWidget):
    shelfClicked=Signal(str,int)
    expanded=Signal()
    def __init__(self,parent=None,miniature=False):
        super().__init__(parent);self.miniature=miniature;self.view=None;self.data=None;self.selected=''
        self.layout_=QVBoxLayout(self);self.layout_.setContentsMargins(0,0,0,0);self.setMinimumSize(180,160)
        self.placeholder=QLabel(T('3D raf görünümü yükleniyor…'));self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter);self.placeholder.setWordWrap(True);self.layout_.addWidget(self.placeholder)
    def ensure_view(self):
        if self.view:return True
        if QApplication.platformName()=='offscreen':self.placeholder.setText(T('3D görünüm için masaüstü grafik oturumu gerekli.'));return False
        try:
            from PySide6.QtQuickWidgets import QQuickWidget
            import PySide6.QtQuick3D
            self.view=QQuickWidget(self);self.view.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
            self.view.setSource(QUrl.fromLocalFile(str(Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'warehouse/Warehouse.qml')))
            if self.view.status()==QQuickWidget.Status.Error:
                errors='; '.join(x.toString() for x in self.view.errors());self.placeholder.setText(T('3D görünüm başlatılamadı: ')+errors);self.view.deleteLater();self.view=None;return False
            self.placeholder.hide();self.view.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding);self.layout_.addWidget(self.view,1);self.layout_.activate();root=self.view.rootObject();root.setProperty('miniature',self.miniature)
            root.shelfClicked.connect(self.shelfClicked.emit);root.expanded.connect(self.expanded.emit);return True
        except (ImportError,RuntimeError) as error:self.placeholder.setText(T('3D görünüm başlatılamadı: ')+str(error));return False
    def showEvent(self,event):
        super().showEvent(event)
        if self.data:self.display(*self.data)
    def display(self,layout,shelves,products,selected='',empty_only=False):
        self.data=(layout,shelves,products,selected,empty_only)
        if not self.isVisible():return
        scene=warehouse_scene(layout,shelves,products,selected,empty_only);self.scene=scene
        if not self.ensure_view():return
        root=self.view.rootObject();root.setProperty('parts',scene['parts']);root.setProperty('labels',scene['labels']);root.setProperty('selectedProduct',selected)
        root.setProperty('floorWidth',scene['width']);root.setProperty('floorDepth',scene['depth'])
        if getattr(self,'location_id',None)!=layout.get('location_id'):
            self.location_id=layout.get('location_id');root.setProperty('centerX',scene['centerX']);root.setProperty('centerZ',scene['centerZ']);root.resetView()
    def focus(self,rack,level=0):
        if not self.view:return
        root=self.view.rootObject();root.setProperty('selectedRack',rack);root.setProperty('selectedLevel',level)
        if rack in self.scene['positions']:
            x,z=self.scene['positions'][rack];root.setProperty('centerX',x);root.setProperty('centerZ',z);root.setProperty('distance',620)
    def reset(self):
        if self.view:
            root=self.view.rootObject();root.setProperty('centerX',self.scene['centerX']);root.setProperty('centerZ',self.scene['centerZ']);root.setProperty('selectedRack','');root.resetView()

class WarehouseDialog(ServerDialog):
    def __init__(self,hub,parent=None):
        super().__init__(hub.client,T('3D Raf ve Doluluk'),parent);self.hub=hub;self.data={};self.layout_data=None;self.selected_slot=None;self.resize(1360,850)
        top=QHBoxLayout();self.location=QComboBox();self.location.setMinimumWidth(190);top.addWidget(self.location)
        self.search=QLineEdit();self.search.setPlaceholderText(T('Ürün adı veya barkod ile raftaki yerini bul…'));top.addWidget(self.search,1)
        self.empty=QCheckBox(T('Boş alanları göster'));top.addWidget(self.empty);self.body.addLayout(top)
        self.info=QLabel();self.info.setWordWrap(True);self.body.addWidget(self.info)
        split=QSplitter();self.view=WarehouseView();split.addWidget(self.view)
        side=QWidget();sidebar=QVBoxLayout(side);side.setMaximumWidth(350);self.matches=QListWidget();sidebar.addWidget(self.matches,1)
        self.details=QLabel();self.details.setWordWrap(True);sidebar.addWidget(self.details);split.addWidget(side);split.setSizes([1000,300]);self.body.addWidget(split,1)
        controls=QHBoxLayout();self.button(T('Genel görünüm'),self.view.reset,controls);self.button(T('Yenile'),self.refresh,controls)
        self.edit=self.button(T('Raf Düzenini Değiştir'),self.edit_layout,controls);self.place=self.button(T('Ürün Yerleştir / Taşı'),self.place_product,controls);self.seed=self.button(T('Örnek Yerleşim Hazırla'),self.seed_layouts,controls);self.body.addLayout(controls)
        self.location.currentIndexChanged.connect(self.render_scene);self.search.textChanged.connect(self.render_scene);self.empty.toggled.connect(self.render_scene)
        self.matches.itemClicked.connect(self.focus_match);self.view.shelfClicked.connect(self.slot_selected)
        self.hub.updated.connect(self.loaded);self.loaded(hub.data);self.refresh()
    def refresh(self):self.run(lambda:self.client.read('retail_snapshot'),self.hub.accept)
    def loaded(self,data):
        if not data:return
        self.data=data;previous=self.location.currentData();self.location.blockSignals(True);self.location.clear()
        for loc in data.get('locations',[]):
            if loc['active']:self.location.addItem(loc['name'],loc['id'])
        if previous:self.location.setCurrentIndex(max(0,self.location.findData(previous)))
        self.location.blockSignals(False)
        can=data.get('capabilities',{}).get('layout',False)
        for button in (self.edit,self.place,self.seed):button.setEnabled(can)
        self.render_scene()
    def render_scene(self,*args):
        lid=self.location.currentData();self.layout_data=next((l for l in self.data.get('layouts',[]) if l['location_id']==lid),None);self.matches.clear()
        if not self.layout_data:
            self.info.setText(T('Bu konumun raf planı henüz oluşturulmadı. Raf düzeni tanımlayın veya örnek yerleşim hazırlayın.'));self.view.hide();return
        self.view.show();products=self.data.get('products',[]);shelves=[s for s in self.data.get('shelves',[]) if s['location_id']==lid]
        found=find_products(products,self.search.text());ids={p['id'] for p in found};names={p['id']:p['name'] for p in products}
        selected=found[0]['id'] if len(found)==1 else ''
        self.view.display(self.layout_data,shelves,products,selected,self.empty.isChecked());scene=warehouse_scene(self.layout_data,shelves,products)
        stock=sum(float(i['quantity']) for i in self.data.get('inventory',[]) if i['location_id']==lid)
        self.info.setText(T('Raf doluluğu: %{rate:.1f} · Yerleşen: {placed} · Yeri doğrulanan: {verified} · Yerleştirilmemiş: {unplaced}',rate=scene['occupancy'],placed=scene['placed'],verified=scene['verified'],unplaced=int(stock-scene['placed'])))
        self.details.setText(T('Doluluk, kullanılan raf genişliğine göre hesaplanır. Örnek planda kitap başına 2 cm varsayılır; gerçek ölçüleri ve fiziksel yerleri doğrulayın.'))
        for s in shelves:
            if not self.search.text().strip() or s['product_id'] in ids:
                label=f"{s['rack']} · "+render(T('Kat {n}',n=s['level']))+f" · {s['quantity']}\n{names.get(s['product_id'],'')}"
                if not s.get('verified'):label+=' · '+render(T('Örnek / doğrulanmadı'))
                self.matches.addItem(label);self.matches.item(self.matches.count()-1).setData(Qt.ItemDataRole.UserRole,(s['rack'],s['level'],s['product_id']))
        if found and not self.matches.count():self.details.setText(T('Ürün bu konumda rafa yerleştirilmemiş veya stokta yok.'))
    def focus_match(self,item):
        rack,level,pid=item.data(Qt.ItemDataRole.UserRole);self.selected_slot=(rack,level);self.view.display(self.layout_data,self.data['shelves'],self.data['products'],pid,self.empty.isChecked());self.view.focus(rack,level)
    def slot_selected(self,rack,level):
        self.selected_slot=(rack,level);self.view.focus(rack,level)
        self.details.setText(T('Seçili raf: {rack} · Kat {level}',rack=rack,level=level))
    def seed_layouts(self):self.mutation('retail_seed_layouts',{},lambda _:self.refresh())
    def edit_layout(self):
        if not self.location.currentData():return
        LayoutEditor(self.client,self.location.currentData(),self.layout_data,self).exec();self.refresh()
    def place_product(self):
        if not self.layout_data:self.status_label.setText(T('Önce raf düzenini oluşturun.'));return
        PlacementDialog(self.client,self.layout_data,self.data,self.selected_slot,self).exec();self.refresh()

class LayoutEditor(ServerDialog):
    def __init__(self,client,lid,layout,parent=None):
        super().__init__(client,T('Raf Düzeni'),parent);self.lid=lid;self.record=layout;self.resize(1050,760)
        self.note=QLabel(T('Ölçüler santimetredir. Dolu raf/kat silinemez; önce üzerindeki ürünleri başka rafa veya yerleştirilmemiş alana alın.'));self.note.setWordWrap(True);self.body.addWidget(self.note)
        form=QHBoxLayout();self.row_count=QSpinBox();self.row_count.setRange(1,20);self.row_count.setValue(3);self.bays=QSpinBox();self.bays.setRange(1,20);self.bays.setValue(4);self.levels=QSpinBox();self.levels.setRange(1,10);self.levels.setValue(5);self.aisle=QSpinBox();self.aisle.setRange(60,1000);self.aisle.setValue(int((layout or {}).get('spec',{}).get('aisle',140)))
        for text,widget in [(T('Sıra'),self.row_count),(T('Her sırada raf'),self.bays),(T('Kat'),self.levels),(T('Koridor (cm)'),self.aisle)]:form.addWidget(QLabel(text));form.addWidget(widget)
        self.bay_gap=QSpinBox();self.bay_gap.setRange(0,500);self.bay_gap.setValue(int((layout or {}).get('spec',{}).get('bay_gap',16)));form.addWidget(QLabel(T('Raf arası (cm)')));form.addWidget(self.bay_gap)
        self.body.addLayout(form);self.button(T('Bu Sayılarla Plan Oluştur'),self.generate)
        self.grid=QTableWidget(0,7);self.grid.setHorizontalHeaderLabels([T('Raf kodu'),T('Sıra'),T('Raf no'),T('Kat'),T('Genişlik'),T('Derinlik'),T('Yükseklik')]);self.grid.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);self.body.addWidget(self.grid,1)
        row=QHBoxLayout();self.button(T('Raf Ekle'),self.add,row);self.button(T('Seçili Rafı Kaldır'),lambda:self.grid.removeRow(self.grid.currentRow()) if self.grid.currentRow()>=0 else None,row);self.button(T('Kaydet'),self.save,row);self.body.addLayout(row)
        for rack in (layout or {}).get('spec',{}).get('racks',[]):self.add(rack)
        if not layout:self.generate()
    def add(self,rack=None):
        if not isinstance(rack,dict):rack=dict(id=f'R1-B{self.grid.rowCount()+1}',row=1,bay=self.grid.rowCount()+1,levels=5,width=160,depth=50,height=220)
        row=self.grid.rowCount();self.grid.insertRow(row)
        for col,key in enumerate(['id','row','bay','levels','width','depth','height']):self.grid.setItem(row,col,QTableWidgetItem(str(rack[key])))
    def generate(self):
        if self.row_count.value()*self.bays.value()>200:self.status_label.setText(T('En fazla 200 raf oluşturulabilir.'));return
        if self.grid.rowCount() and QMessageBox.question(self,T('Raf planı'),T('Ekrandaki taslak raf planı yeniden oluşturulsun mu?'))!=QMessageBox.StandardButton.Yes:return
        self.grid.setRowCount(0)
        for r in range(1,self.row_count.value()+1):
            for b in range(1,self.bays.value()+1):self.add(dict(id=f'R{r}-B{b}',row=r,bay=b,levels=self.levels.value(),width=160,depth=50,height=220))
    def save(self):
        try:
            racks=[]
            for row in range(self.grid.rowCount()):
                values=[self.grid.item(row,c).text().strip() for c in range(7)];racks.append(dict(id=values[0],row=int(values[1]),bay=int(values[2]),levels=int(values[3]),width=float(values[4]),depth=float(values[5]),height=float(values[6])))
        except (ValueError,AttributeError):self.status_label.setText(T('Raf numaraları ve ölçüler sayı olmalı.'));return
        self.mutation('retail_layout_save',{'location_id':self.lid,'version':(self.record or {}).get('version',0),'spec':{'aisle':self.aisle.value(),'bay_gap':self.bay_gap.value(),'racks':racks}},lambda _:self.accept())

class PlacementDialog(ServerDialog):
    def __init__(self,client,layout,data,selected,parent=None):
        super().__init__(client,T('Rafa Ürün Yerleştir'),parent);self.record=layout;self.data=data;self.resize(780,620)
        self.product=QComboBox();self.product.setEditable(True);self.product.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        for p in data['products']:
            if p['active']:self.product.addItem(p['barcode']+' · '+p['name'],p['id'])
        self.rack=QComboBox()
        for r in layout['spec']['racks']:
            for level in range(1,int(r['levels'])+1):self.rack.addItem(r['id']+' · '+render(T('Kat {n}',n=level)),(r['id'],level))
        if selected:self.rack.setCurrentIndex(max(0,self.rack.findData(selected)))
        self.qty=QSpinBox();self.qty.setRange(0,1000000);self.width=QDoubleSpinBox();self.width.setRange(.1,1000);self.width.setValue(2);self.width.setSuffix(' cm');self.verified=QCheckBox(T('Ürünün fiziksel yerini ve ölçüsünü doğruladım'))
        form=QFormLayout();form.addRow(T('Ürün'),self.product);form.addRow(T('Raf / kat'),self.rack);form.addRow(T('Bu raftaki toplam adet'),self.qty);form.addRow(T('Bir ürünün rafta kapladığı genişlik'),self.width);form.addRow(self.verified);self.body.addLayout(form)
        self.note=QLabel(T('0 adet bu raftan kaldırır; toplam stok değişmez. Başka rafa taşımadan önce kaynak raftaki adedi azaltın.'));self.note.setWordWrap(True);self.body.addWidget(self.note)
        self.suggestions=QListWidget();self.body.addWidget(self.suggestions,1);self.button(T('Uygun Boş Rafları Bul'),self.suggest);self.button(T('Kaydet'),self.save)
        self.product.currentIndexChanged.connect(self.load_slot);self.rack.currentIndexChanged.connect(self.load_slot);self.suggestions.itemClicked.connect(self.choose_slot);self.load_slot()
    def load_slot(self):
        rid,level=self.rack.currentData();s=next((s for s in self.data['shelves'] if s['location_id']==self.record['location_id'] and s['rack']==rid and s['level']==level and s['product_id']==self.product.currentData()),{})
        self.qty.setValue(s.get('quantity',0));self.width.setValue(float(s.get('unit_width',2)));self.verified.setChecked(s.get('verified',False))
    def suggest(self):
        self.suggestions.clear()
        for rack,level,free in free_shelves(self.record,self.data['shelves'],max(1,self.qty.value()),self.width.value()):
            self.suggestions.addItem(f'{rack} · '+render(T('Kat {n}',n=level))+f' · {free:.1f} cm');self.suggestions.item(self.suggestions.count()-1).setData(Qt.ItemDataRole.UserRole,(rack,level))
        if not self.suggestions.count():self.status_label.setText(T('Bu miktarın tamamı için yeterli boş raf yok. Miktarı bölerek yerleştirebilirsiniz.'))
    def choose_slot(self,item):
        qty=self.qty.value();width=self.width.value();self.rack.setCurrentIndex(self.rack.findData(item.data(Qt.ItemDataRole.UserRole)));self.qty.setValue(qty);self.width.setValue(width)
    def save(self):
        rack,level=self.rack.currentData();self.mutation('retail_shelf_place',dict(location_id=self.record['location_id'],version=self.record['version'],rack=rack,level=level,product_id=self.product.currentData(),quantity=self.qty.value(),unit_width=str(self.width.value()),verified=self.verified.isChecked()),lambda _:self.accept())
