"""Painted UI assets: scalable bell and unread notification orbit."""
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QPainterPath, QConicalGradient
from PySide6.QtWidgets import QPushButton
from deporiaq_i18n import T, render, Text ,QPushButton,QWidget

class NotificationButton(QPushButton):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.unread=0;self.angle=0
        self.setMinimumSize(86,40)
        self.setAccessibleName(T('Bildirimler'))
        self.timer=QTimer(self);self.timer.setInterval(40);self.timer.timeout.connect(self.advance)
        self.setCount(0)
    def advance(self):
        self.angle=(self.angle+5)%360;self.update()
    def setCount(self,count):
        self.unread=max(0,int(count));self.setAccessibleDescription(T('{v0} okunmamış bildirim', v0=self.unread))
        self.setToolTip(T('Bildirimler · {v0} okunmamış', v0=self.unread))
        if self.unread:self.timer.start()
        else:self.timer.stop()
        self.update()
    def paintEvent(self,event):
        super().paintEvent(event)
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor('#E2E8F0'),1.8));p.setBrush(Qt.BrushStyle.NoBrush)
        y=self.height()/2
        path=QPainterPath(QPointF(18,y+5));path.lineTo(20,y+2);path.lineTo(20,y-3)
        path.cubicTo(20,y-11,32,y-11,32,y-3);path.lineTo(32,y+2);path.lineTo(34,y+5);path.closeSubpath()
        p.drawPath(path);p.drawArc(QRectF(23,y+4,6,6),180*16,180*16)
        p.drawText(QRectF(42,0,self.width()-48,self.height()),Qt.AlignmentFlag.AlignCenter,render(str(self.unread)))
        if self.unread:
            gradient=QConicalGradient(self.rect().center(),self.angle)
            gradient.setColorAt(0,QColor('#FBBF24'));gradient.setColorAt(.2,QColor('#FBBF24'));gradient.setColorAt(.65,QColor(251,191,36,10));gradient.setColorAt(1,QColor('#FBBF24'))
            p.setPen(QPen(gradient,2.5));p.drawRoundedRect(QRectF(self.rect()).adjusted(2,2,-2,-2),7,7)

from PySide6.QtCore import QEventLoop
from deporiaq_i18n import QDialog

class WorkspaceDialog(QDialog):
    """Keep main-window controls available while a business panel is open."""
    def exec(self):
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setWindowFlag(Qt.WindowType.WindowMinMaxButtonsHint,True)
        loop=QEventLoop(self)
        self.finished.connect(loop.quit)
        self.show()
        loop.exec()
        self.finished.disconnect(loop.quit)
        return self.result()

from PySide6.QtCore import QElapsedTimer
from PySide6.QtGui import QPixmap,QFont
from PySide6.QtWidgets import QWidget,QApplication

class BrandAnimation(QWidget):
    def __init__(self,icon_path,closing=False):
        super().__init__(None,Qt.WindowType.FramelessWindowHint|Qt.WindowType.Tool)
        self.setFixedSize(500,280);self.closing=closing;self.logo=QPixmap(icon_path)
        self.duration=650 if closing else 1100;self.clock=QElapsedTimer();self.clock.start()
        self.timer=QTimer(self);self.timer.timeout.connect(self.update);self.timer.start(16)
        screen=QApplication.primaryScreen().availableGeometry();self.move(screen.center()-self.rect().center())
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.fillRect(self.rect(),QColor('#0B1424'))
        progress=min(1,self.clock.elapsed()/self.duration);opacity=1-progress if self.closing else min(1,progress*2)
        p.setOpacity(opacity);size=int(80+20*(1-(1-progress)**3));p.drawPixmap((self.width()-size)//2,38,size,size,self.logo)
        p.setFont(QFont('Segoe UI',30,QFont.Weight.Bold));p.setPen(QColor('#F1F5F9'));p.drawText(QRectF(0,150,500,55),Qt.AlignmentFlag.AlignCenter,render('DeporiaQ'))
        p.setFont(QFont('Segoe UI',11));p.setPen(QColor('#38BDF8'));p.drawText(QRectF(0,208,500,25),Qt.AlignmentFlag.AlignCenter,render(T('Güvenli · Hızlı · Bulut')))
        p.setOpacity(1);p.fillRect(QRectF(80,258,340*progress,2),QColor('#38BDF8'))

def play_brand(icon_path,closing=False):
    panel=BrandAnimation(icon_path,closing);loop=QEventLoop()
    panel.show();QTimer.singleShot(panel.duration,loop.quit);loop.exec()
    panel.timer.stop();panel.close();panel.deleteLater()
