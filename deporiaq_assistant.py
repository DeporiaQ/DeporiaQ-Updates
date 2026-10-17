"""In-application assistant. The desktop never receives the provider API key."""
import json
import urllib.request
import urllib.error
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import QDockWidget,QScrollArea,QVBoxLayout,QHBoxLayout,QFrame
from deporiaq_i18n import T,language,Localized,QLabel,QPlainTextEdit,QPushButton,QWidget
from deporiaq_commerce_ui import Job

ERRORS={
 'AI_NOT_CONFIGURED':T('DeporiaQ Asistan henüz sunucuda etkinleştirilmedi. Kullanım Rehberi bölümünü açabilirsiniz.'),
 'AI_LIMIT':T('Asistan kullanım sınırına ulaşıldı. Bir süre sonra tekrar deneyin.'),
 'ACCESS':T('Asistan için etkin abonelik, kullanıcı ve cihaz kaydı gerekli.'),
 'AUTH':T('Cloud oturumunuzu doğrulayıp tekrar deneyin.'),
 'INPUT':T('Sorunuzu 1–2000 karakter arasında yazın.'),
 'AI_INCOMPLETE':T('Yanıt tamamlanamadı. Lütfen tekrar deneyin.'),
 'AI_UNAVAILABLE':T('Asistana şu anda ulaşılamıyor. Lütfen tekrar deneyin.'),
}

def ask_server(cloud,action,messages=None,locale=None):
    if not cloud.bagli:raise ValueError(str(ERRORS['AUTH']))
    # Refresh credentials using the shared session before the longer model request.
    cloud._istek('/rest/v1/rpc/dpq_call','POST',{'p_action':'status','p_payload':{},'p_device':cloud.cihaz_kimligi})
    with cloud._session_lock:
        url=cloud.url;key=cloud.anahtar;token=cloud.access_token;device=cloud.cihaz_kimligi
    body={'action':action,'device':device,'language':locale or language()}
    if action=='ask':body['messages']=messages
    request=urllib.request.Request(url+'/functions/v1/deporiaq-assistant',data=json.dumps(body,ensure_ascii=False).encode(),headers={'apikey':key,'Authorization':'Bearer '+token,'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(request,timeout=45) as response:data=json.loads(response.read(64000))
        if action=='ask' and not isinstance(data.get('answer'),str):raise ValueError(str(ERRORS['AI_UNAVAILABLE']))
        return data
    except urllib.error.HTTPError as error:
        try:code=json.loads(error.read(64000)).get('code','AUTH' if error.code==401 else 'AI_UNAVAILABLE')
        except (ValueError,TypeError,AttributeError):code='AI_UNAVAILABLE'
        raise ValueError(str(ERRORS.get(code,ERRORS['AI_UNAVAILABLE']))) from None
    except (urllib.error.URLError,TimeoutError):raise ValueError(str(ERRORS['AI_UNAVAILABLE'])) from None

class AssistantPanel(Localized,QDockWidget):
    def __init__(self,window):
        super().__init__(window);self.setWindowTitle(T('DeporiaQ Asistan'));self.window=window;self.job=None;self.history=[];self.ready=False
        self.setObjectName('assistantDock');self.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable);self.setMinimumWidth(345)
        root=QWidget();layout=QVBoxLayout(root);layout.setContentsMargins(18,18,18,18);layout.setSpacing(12)
        heading=QLabel(T('DeporiaQ Asistan'));heading.setObjectName('sayfaBaslik');layout.addWidget(heading)
        self.status=QLabel(T('Bağlantı kontrol ediliyor…'));self.status.setWordWrap(True);layout.addWidget(self.status)
        note=QLabel(T('DeporiaQ kullanımı hakkında sorun. Yalnızca yazdığınız mesajlar yapay zekâ hizmetine gönderilir. Parola veya özel müşteri bilgisi yazmayın.'));note.setWordWrap(True);note.setObjectName('soluk');layout.addWidget(note)
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);self.messages=QWidget();self.messages_layout=QVBoxLayout(self.messages);self.messages_layout.setAlignment(Qt.AlignmentFlag.AlignTop);self.scroll.setWidget(self.messages);layout.addWidget(self.scroll,1)
        self.input=QPlainTextEdit();self.input.setPlaceholderText(T('Örneğin: Şubeler arası transfer nasıl yapılır?'));self.input.setMaximumHeight(100);layout.addWidget(self.input)
        bar=QHBoxLayout();self.send=QPushButton(T('Gönder'));self.send.setObjectName('birincil');self.send.clicked.connect(self.submit);bar.addWidget(self.send)
        self.clear=QPushButton(T('Yeni sohbet'));self.clear.clicked.connect(self.reset);bar.addWidget(self.clear);layout.addLayout(bar)
        self.retry=QPushButton(T('Bağlantıyı yeniden dene'));self.retry.clicked.connect(self.check);layout.addWidget(self.retry)
        self.setWidget(root);self.resize(390,650)
    def run(self,fn,done):
        if self.job:return
        self.send.setEnabled(False);self.clear.setEnabled(False);self.retry.setEnabled(False)
        self.job=Job(fn,self);self.job.finished.connect(lambda:self.finished(done));self.job.start()
    def finished(self,done):
        job=self.job;self.job=None;self.clear.setEnabled(True);self.retry.setEnabled(True)
        if job.error:self.status.setText(job.error)
        else:done(job.result)
        self.send.setEnabled(self.ready);job.deleteLater()
    def check(self):
        self.status.setText(T('Bağlantı kontrol ediliyor…'))
        self.run(lambda:ask_server(self.window.cloud_client,'status'),self.checked)
    def checked(self,result):
        self.ready=bool(result.get('ready'));self.status.setText(T('Yapay zekâ hazır · Uygulama kullanım desteği'))
    def append(self,name,text):
        frame=QFrame();frame.setObjectName('assistantMessage');box=QVBoxLayout(frame)
        label=QLabel(name);label.setObjectName('soluk');box.addWidget(label)
        content=QLabel(text);content.setTextFormat(Qt.TextFormat.PlainText);content.setWordWrap(True);content.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse);box.addWidget(content)
        self.messages_layout.addWidget(frame)
        QTimer.singleShot(0,self,lambda:self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum()))
    def submit(self):
        text=self.input.toPlainText().strip()
        if self.job or not self.ready:return
        if not 1<=len(text)<=2000:self.status.setText(ERRORS['INPUT']);return
        self.pending={'role':'user','content':text};messages=self.history[-6:]+[self.pending];locale=language()
        self.append(T('Siz'),text);self.input.clear();self.status.setText(T('Yanıt hazırlanıyor…'))
        self.run(lambda:ask_server(self.window.cloud_client,'ask',messages,locale),self.answered)
    def answered(self,result):
        answer=result['answer'];self.history=(self.history+[self.pending,{'role':'assistant','content':answer[:2000]}])[-6:]
        self.append(T('DeporiaQ Asistan'),answer);self.status.setText(T('Yanıtı işlemi uygulamadan önce kontrol edin.'))
    def reset(self):
        if self.job:return
        self.history=[]
        while self.messages_layout.count():
            item=self.messages_layout.takeAt(0);item.widget().deleteLater()
        self.status.setText(T('Yeni sohbet hazır.'))
