"""Explicit, live UI translations. Business/customer strings stay untouched.

Text keeps its Turkish source value for existing enum/storage contracts; render()
is used only at presentation boundaries. No global Qt monkey-patching.
"""
import weakref
from PySide6 import QtWidgets as W
from PySide6.QtCore import QSignalBlocker, Qt, QTranslator, QLibraryInfo, QLocale
from shiboken6 import isValid
from deporiaq_translations import EN

_language='tr'
_qt_translator=None
_qt_language=None
_bindings={}

def bindings_for(obj):
    key=id(obj)
    if key not in _bindings:
        _bindings[key]=(weakref.ref(obj,lambda ref,k=key:_bindings.pop(k,None)),{})
    return _bindings[key][1]

def language():return _language

class Text(str):
    def __new__(cls,source,**values):
        stable=source.format(**{k:source_text(v) if isinstance(v,Text) else v for k,v in values.items()}) if values else source
        obj=super().__new__(cls,stable);obj.source=source;obj.values=values;obj.parts=None;return obj
    def __str__(self):
        if self.parts is not None:return ''.join(render(x) for x in self.parts)
        template=EN.get(self.source,self.source) if _language=='en' else self.source
        return template.format(**{k:render(v) if isinstance(v,Text) else v for k,v in self.values.items()}) if self.values else template
    def __format__(self,spec):return format(str(self),spec)
    def __add__(self,other):
        result=Text(super().__add__(other));result.parts=(self,other);return result
    def __radd__(self,other):
        result=Text(str.__add__(other,self));result.parts=(other,self);return result

def source_text(value):
    if not isinstance(value,Text):return str(value)
    if value.parts is not None:return ''.join(source_text(x) for x in value.parts)
    return value.source.format(**{k:source_text(v) if isinstance(v,Text) else v for k,v in value.values.items()}) if value.values else value.source

def T(source,**values):return Text(source,**values)
def render(value):return str(value)
def join_text(separator,parts):
    result=T('')
    for i,part in enumerate(parts):result=result+(separator if i else '')+part
    return result

def bind(obj,key,value,apply):
    values=bindings_for(obj)
    if isinstance(value,Text):values[key]=(value,apply)
    else:values.pop(key,None)
    apply(obj,render(value))

def set_language(value):
    global _language,_qt_translator,_qt_language
    if value not in ('tr','en'):raise ValueError('Unsupported language')
    app=W.QApplication.instance()
    if app and _qt_language!=value:
        if _qt_translator:app.removeTranslator(_qt_translator)
        _qt_translator=QTranslator(app)
        if value=='tr' and _qt_translator.load('qtbase_tr',QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
            app.installTranslator(_qt_translator)
        _qt_language=value
        QLocale.setDefault(QLocale('tr_TR' if value=='tr' else 'en_GB'))
    if _language==value:return
    _language=value
    for reference,bindings in list(_bindings.values()):
        obj=reference()
        if obj is None or not isValid(obj):continue
        blocker=QSignalBlocker(obj) if hasattr(obj,'blockSignals') else None
        for value,apply in list(bindings.values()):apply(obj,render(value))
        del blocker
    app=W.QApplication.instance()
    if app:
        import gc
        gc.collect()
        widgets=app.allWidgets()
        for widget in widgets:
            if isValid(widget):widget.update()

class Localized:
    def setWindowTitle(self,text):bind(self,'title',text,lambda o,v:super(Localized,o).setWindowTitle(v))
    def setToolTip(self,text):bind(self,'tooltip',text,lambda o,v:super(Localized,o).setToolTip(v))
    def setAccessibleName(self,text):bind(self,'accessible',text,lambda o,v:super(Localized,o).setAccessibleName(v))

class QLabel(Localized,W.QLabel):
    def __init__(self,*args,**kwargs):
        text=args[0] if args and isinstance(args[0],str) else None
        super().__init__(*(('',)+args[1:] if text is not None else args),**kwargs)
        if text is not None:self.setText(text)
    def setText(self,text):bind(self,'text',text,lambda o,v:W.QLabel.setText(o,v))
    def clear(self):self.setText('')

class QPushButton(Localized,W.QPushButton):
    def __init__(self,*args,**kwargs):
        texts=[(i,x) for i,x in enumerate(args) if isinstance(x,str)]
        super().__init__(*[render(x) if isinstance(x,Text) else x for x in args],**kwargs)
        if texts:self.setText(texts[0][1])
    def setText(self,text):bind(self,'text',text,lambda o,v:W.QPushButton.setText(o,v.replace('&','&&')))

class QCheckBox(Localized,W.QCheckBox):
    def __init__(self,*args,**kwargs):
        super().__init__(*[render(x) if isinstance(x,Text) else x for x in args],**kwargs)
        if args and isinstance(args[0],str):self.setText(args[0])
    def setText(self,text):bind(self,'text',text,lambda o,v:W.QCheckBox.setText(o,v))

class QLineEdit(Localized,W.QLineEdit):
    # Editable contents are never translated, even if they equal a UI label.
    def setPlaceholderText(self,text):bind(self,'placeholder',text,lambda o,v:W.QLineEdit.setPlaceholderText(o,v))

class QPlainTextEdit(Localized,W.QPlainTextEdit):
    def __init__(self,*args,**kwargs):
        text=args[0] if args and isinstance(args[0],Text) else None
        super().__init__(*(('',)+args[1:] if text is not None else args),**kwargs)
        if text is not None:self.setPlainText(text)
    def setPlaceholderText(self,text):bind(self,'placeholder',text,lambda o,v:W.QPlainTextEdit.setPlaceholderText(o,v))
    def setPlainText(self,text):bind(self,'plain',text,lambda o,v:W.QPlainTextEdit.setPlainText(o,v))

class QComboBox(Localized,W.QComboBox):
    SOURCE=Qt.ItemDataRole.UserRole+260
    def addItem(self,*args):
        i=0 if isinstance(args[0],str) else 1;text=args[i];idx=self.count()
        super().addItem(*[render(x) if isinstance(x,Text) else x for x in args])
        if isinstance(text,Text):
            self.setItemData(idx,source_text(text),self.SOURCE)
            bind(self,('item',idx),text,lambda o,v,i=idx:W.QComboBox.setItemText(o,i,v))
    def addItems(self,texts):
        for text in texts:self.addItem(text)
    def clear(self):
        for key in list(bindings_for(self)):
            if isinstance(key,tuple):bindings_for(self).pop(key)
        super().clear()
    def currentText(self):
        source=self.itemData(self.currentIndex(),self.SOURCE)
        return source if source is not None else super().currentText()
    def findText(self,text,*args):
        for i in range(self.count()):
            if self.itemData(i,self.SOURCE)==text:return i
        return super().findText(render(text),*args)
    def setCurrentText(self,text):
        index=self.findText(text)
        if index>=0:self.setCurrentIndex(index)
        else:super().setCurrentText(render(text))

class QTableWidgetItem(W.QTableWidgetItem):
    def __init__(self,*args):
        super().__init__(*[render(x) if isinstance(x,Text) else x for x in args])
        if args and isinstance(args[0],Text):self.setText(args[0])
    def setText(self,text):bind(self,'text',text,lambda o,v:W.QTableWidgetItem.setText(o,v))

class QTableWidget(Localized,W.QTableWidget):
    def setHorizontalHeaderLabels(self,labels):
        for i,label in enumerate(labels):self.setHorizontalHeaderItem(i,QTableWidgetItem(label))

class QTabWidget(Localized,W.QTabWidget):
    def addTab(self,*args):
        text=args[-1];idx=super().addTab(*[render(x) if isinstance(x,Text) else x for x in args])
        bind(self,('tab',idx),text,lambda o,v,i=idx:W.QTabWidget.setTabText(o,i,v));return idx

class QFormLayout(W.QFormLayout):
    def addRow(self,*args):
        if args and isinstance(args[0],Text):args=(QLabel(args[0]),)+args[1:]
        return super().addRow(*args)

class QDialog(Localized,W.QDialog):pass
class QMainWindow(Localized,W.QMainWindow):pass
class QWidget(Localized,W.QWidget):pass

class QMessageBox(W.QMessageBox):
    @staticmethod
    def _call(method,*args,**kwargs):
        from deporiaq_errors import error_text
        if len(args)>2 and isinstance(args[2],str) and not isinstance(args[2],Text):args=args[:2]+(error_text(args[2]),)+args[3:]
        return method(*[render(x) if isinstance(x,Text) else x for x in args],**kwargs)
    @staticmethod
    def information(*a,**kw):return QMessageBox._call(W.QMessageBox.information,*a,**kw)
    @staticmethod
    def warning(*a,**kw):return QMessageBox._call(W.QMessageBox.warning,*a,**kw)
    @staticmethod
    def critical(*a,**kw):return QMessageBox._call(W.QMessageBox.critical,*a,**kw)
    @staticmethod
    def question(*a,**kw):return QMessageBox._call(W.QMessageBox.question,*a,**kw)

class QInputDialog(W.QInputDialog):
    @staticmethod
    def getText(*a,**kw):return QMessageBox._call(W.QInputDialog.getText,*a,**kw)
    @staticmethod
    def getInt(*a,**kw):return QMessageBox._call(W.QInputDialog.getInt,*a,**kw)
    @staticmethod
    def getDouble(*a,**kw):return QMessageBox._call(W.QInputDialog.getDouble,*a,**kw)
    @staticmethod
    def getItem(parent,title,label,items,*a,**kw):
        displayed=[render(i) for i in items]
        value,ok=W.QInputDialog.getItem(parent,render(title),render(label),displayed,*a,**kw)
        chosen=items[displayed.index(value)] if value in displayed else value
        return (source_text(chosen) if isinstance(chosen,Text) else chosen),ok

class QFileDialog(W.QFileDialog):
    @staticmethod
    def getOpenFileName(*a,**kw):return QMessageBox._call(W.QFileDialog.getOpenFileName,*a,**kw)
    @staticmethod
    def getSaveFileName(*a,**kw):return QMessageBox._call(W.QFileDialog.getSaveFileName,*a,**kw)
