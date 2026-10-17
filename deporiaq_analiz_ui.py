"""Operational reports and keyboard command palette for the Qt application."""
from datetime import datetime
from html import escape
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QTextDocument
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QSpinBox, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMessageBox, QListWidget, QAbstractItemView)
from PySide6.QtPrintSupport import QPrinter
from deporiaq_analiz import Analysis, REPORTS, matches, export_csv


from deporiaq_visuals import WorkspaceDialog as QDialog
from deporiaq_i18n import T, render, Text ,QComboBox,QFileDialog,QLabel,QLineEdit,QMessageBox,QPushButton,QTableWidget,QTableWidgetItem

class NumericItem(QTableWidgetItem):
    def __init__(self, value):
        super().__init__(value if isinstance(value,Text) else str(value))
        self.setData(Qt.ItemDataRole.UserRole, value)

    def __lt__(self, other):
        a, b = self.data(Qt.ItemDataRole.UserRole), other.data(Qt.ItemDataRole.UserRole)
        if isinstance(a, (int,float)) and isinstance(b, (int,float)):
            return a < b
        try:
            return datetime.strptime(str(a),'%d.%m.%Y') < datetime.strptime(str(b),'%d.%m.%Y')
        except ValueError:
            pass
        return str(a) < str(b)


class AnalysisWindow(QDialog):
    def __init__(self, db, parent=None, initial='search'):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle(T('DeporiaQ · Operasyon Merkezi'))
        self.resize(1120, 760)
        self.setMinimumSize(760, 560)
        layout = QVBoxLayout(self)
        heading = QLabel(T('OPERASYON MERKEZİ'))
        heading.setStyleSheet('font-size:25px;font-weight:700;color:#38BDF8;padding:10px 0;')
        layout.addWidget(heading)
        self.snapshot_label = QLabel()
        self.snapshot_label.setWordWrap(True)
        layout.addWidget(self.snapshot_label)
        metrics = QHBoxLayout()
        self.metrics = []
        for title in (T('Toplam stok'), T('Stok alış değeri'), T('Sıfır stok satırı'), T('Son 30 gün ciro')):
            card = QLabel(title)
            card.setWordWrap(True)
            card.setStyleSheet('background:#18334B;border:1px solid #285475;border-radius:8px;padding:9px;color:#DDEFFF;')
            metrics.addWidget(card,1)
            self.metrics.append((title,card))
        layout.addLayout(metrics)
        controls = QHBoxLayout()
        self.report_type = QComboBox()
        for key, title in REPORTS:
            self.report_type.addItem(title, key)
        self.location = QComboBox()
        self.location.addItem(T('Tüm konumlar'), None)
        for r in db.konumlari_getir():
            self.location.addItem(r['ad'], r['id'])
        controls.addWidget(self.report_type, 2)
        controls.addWidget(self.location, 1)
        layout.addLayout(controls)
        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(T('Ürün, barkod, konum veya sonuç içinde ara…'))
        self.search.setClearButtonEnabled(True)
        self.days = QSpinBox(); self.days.setRange(1,365); self.days.setValue(30)
        self.cover = QSpinBox(); self.cover.setRange(1,365); self.cover.setValue(14)
        filters.addWidget(self.search, 1)
        self.days_label=QLabel(T('Geçmiş gün:')); filters.addWidget(self.days_label); filters.addWidget(self.days)
        self.cover_label = QLabel(T('Hedef gün:'))
        filters.addWidget(self.cover_label); filters.addWidget(self.cover)
        layout.addLayout(filters)
        self.note = QLabel(); self.note.setWordWrap(True)
        self.note.setStyleSheet('color:#CBD5E1;padding:8px;background:#1E3045;border-radius:6px;')
        layout.addWidget(self.note)
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
        bottom = QHBoxLayout(); self.total = QLabel(); bottom.addWidget(self.total); bottom.addStretch()
        for label, action in [(T('Verileri Yenile'),self.reload),('CSV / Excel',self.csv),('PDF Kaydet',self.pdf),(T('Kapat'),self.accept)]:
            button = QPushButton(label); button.clicked.connect(action); bottom.addWidget(button)
        layout.addLayout(bottom)
        self.debounce = QTimer(self); self.debounce.setSingleShot(True); self.debounce.timeout.connect(self.fill)
        self.search.textChanged.connect(lambda: self.debounce.start(180))
        self.report_type.currentIndexChanged.connect(self.calculate)
        self.location.currentIndexChanged.connect(self.calculate)
        self.days.valueChanged.connect(self.calculate)
        self.cover.valueChanged.connect(self.calculate)
        self.report_type.setCurrentIndex(self.report_type.findData(initial))
        self.reload()
        self.access_timer = QTimer(self)
        self.access_timer.timeout.connect(self.check_access)
        self.access_timer.start(500)

    def check_access(self):
        if not self.allowed():
            self.table.clear(); self.rows=[]; self.filtered=[]
            self.reject()

    def allowed(self):
        parent = self.parent()
        return parent is not None and parent.kullanici['rol'] == 'ANA_YONETICI' and not getattr(parent,'lisans_kilitli',False)

    def reload(self):
        if not self.allowed():
            self.reject(); return
        try:
            self.analysis = Analysis(self.db.baglanti)
            self.snapshot_label.setText(T('Yerel veri görünümü · {v0:%d.%m.%Y %H:%M:%S} · Cloud eşitlemesi tamamlandıktan sonra yenileyin.', v0=self.analysis.now))
            entries = list(self.analysis.entries())
            values = [sum(q for _,_,q in entries),
                      sum(p['alis_fiyati']*q for _,p,q in entries),
                      sum(q == 0 for _,_,q in entries),
                      sum(float(h['toplam_tutar'] or 0) for h in self.analysis.sales(30))]
            for i,((title,card),value) in enumerate(zip(self.metrics,values)):
                display = f'{value:,.2f}' if i in (1,3) else f'{value:,}'
                display = display.translate(str.maketrans(',.','.,'))
                card.setText(T('{title}\n{value}',title=title,value=display))
            self.calculate()
        except Exception as error:
            QMessageBox.warning(self,T('Analiz alınamadı'),str(error))

    def calculate(self):
        if not hasattr(self,'analysis'):
            return
        if not self.allowed():
            self.reject(); return
        kind = self.report_type.currentData()
        self.days.setVisible(kind not in ('search','transfer','count')); self.days_label.setVisible(kind not in ('search','transfer','count'))
        self.cover.setVisible(kind == 'purchase'); self.cover_label.setVisible(kind == 'purchase')
        self.headers, self.rows, note = self.analysis.report(kind,self.location.currentData(),self.days.value(),self.cover.value())
        self.note.setText(note)
        self.fill()

    def fill(self):
        if not self.allowed():
            self.reject(); return
        self.filtered = [r for r in self.rows if matches(r,self.search.text())]
        self.table.setSortingEnabled(False)
        self.table.clear(); self.table.setColumnCount(len(self.headers))
        self.table.setHorizontalHeaderLabels(self.headers)
        self.table.setRowCount(len(self.filtered))
        for y,row in enumerate(self.filtered):
            for x,value in enumerate(row):
                item = NumericItem(value)
                if isinstance(value,(int,float)):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if str(value) in (T('Stok yok'),T('7 gün içinde')):
                    item.setForeground(QColor('#FBBF24'))
                self.table.setItem(y,x,item)
        self.table.setSortingEnabled(True)
        self.table.resizeColumnsToContents()
        for col in range(self.table.columnCount()):
            self.table.setColumnWidth(col,min(290,max(95,self.table.columnWidth(col))))
        self.total.setText(T('{v0} / {v1} sonuç', v0=len(self.filtered), v1=len(self.rows)))

    def visible_rows(self):
        return [[self.table.item(y,x).data(Qt.ItemDataRole.UserRole) for x in range(self.table.columnCount())]
                for y in range(self.table.rowCount())]

    def csv(self):
        if not self.allowed():
            self.reject(); return
        path,_ = QFileDialog.getSaveFileName(self,T('CSV kaydet'),f'DeporiaQ_{self.report_type.currentData()}_{datetime.now():%Y%m%d}.csv','CSV (*.csv)')
        if path:
            try:
                export_csv(path,self.headers,self.visible_rows())
                QMessageBox.information(self,T('Kaydedildi'),T('Filtrelenmiş rapor kaydedildi. Barkod sütununu Excel’de metin olarak açın.'))
            except OSError as error:
                QMessageBox.warning(self,T('Kaydedilemedi'),str(error))

    def pdf(self):
        if not self.allowed():
            self.reject(); return
        path,_ = QFileDialog.getSaveFileName(self,T('PDF kaydet'),f'DeporiaQ_{self.report_type.currentData()}.pdf','PDF (*.pdf)')
        if not path:
            return
        try:
            from PySide6.QtGui import QPageLayout
            title = escape(render(T(self.report_type.currentText())))
            html = f'<h1>{title}</h1><p>{escape(self.snapshot_label.text())}</p><p>{escape(self.note.text())}</p>'
            html += '<table border="1" cellspacing="0" cellpadding="4"><thead><tr>' + ''.join(f'<th>{escape(render(h))}</th>' for h in self.headers) + '</tr></thead>'
            html += ''.join('<tr>'+''.join(f'<td>{escape(str(v))}</td>' for v in row)+'</tr>' for row in self.visible_rows())+'</table>'
            document = QTextDocument(); document.setHtml(html)
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setPageOrientation(QPageLayout.Orientation.Landscape)
            printer.setOutputFileName(path)
            document.print_(printer)
            from pathlib import Path
            if not Path(path).exists() or Path(path).stat().st_size == 0:
                raise OSError(T('PDF yazılamadı; konumu kontrol edin.'))
            QMessageBox.information(self,T('Kaydedildi'),T('PDF raporu kaydedildi.'))
        except Exception as error:
            QMessageBox.warning(self,T('PDF kaydedilemedi'),str(error))


class CommandPalette(QDialog):
    def __init__(self, commands, parent=None):
        super().__init__(parent)
        self.commands = commands
        self.setWindowTitle(T('Hızlı Komutlar · Ctrl+K')); self.resize(600,440)
        layout=QVBoxLayout(self)
        layout.addWidget(QLabel(T('Ne yapmak istiyorsunuz?')))
        self.search=QLineEdit(); self.search.setPlaceholderText(T('Satış, transfer, yedek, analiz…'))
        layout.addWidget(self.search)
        self.results=QListWidget(); layout.addWidget(self.results)
        layout.addWidget(QLabel(T('Enter: aç  •  Esc: kapat')))
        self.search.textChanged.connect(self.filter)
        self.search.returnPressed.connect(self.run)
        self.results.itemActivated.connect(self.run)
        self.filter('')

    def filter(self, text):
        self.selected=[(name,action) for name,action in self.commands if matches([name],text)]
        self.results.clear(); self.results.addItems([name for name,_ in self.selected])
        if self.selected:
            self.results.setCurrentRow(0)

    def run(self, *_):
        index=self.results.currentRow()
        if index >= 0:
            action=self.selected[index][1]
            self.accept()
            QTimer.singleShot(0,action)
