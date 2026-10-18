"""Customer enrollment and hosted billing. No merchant secret on the desktop."""
import re
import uuid
from urllib.parse import urlparse
from PySide6.QtCore import QUrl,QTimer
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFormLayout,QHBoxLayout
from deporiaq_commerce_ui import ServerDialog
from stok_programi_v2 import parola_guclu_mu
from deporiaq_i18n import T,language,QLabel,QLineEdit,QPushButton,QCheckBox,QComboBox

def validated_payment_url(url,environment):
    parsed=urlparse(url)
    hosts=('payment.iyzipay.com','checkout.iyzipay.com') if environment=='live' else ('sandbox-payment.iyzipay.com','sandbox-checkout.iyzipay.com')
    if parsed.scheme!='https' or parsed.hostname not in hosts or parsed.username or parsed.password or parsed.port is not None:
        raise ValueError('DPQ_PAYMENT_URL')
    return url

class RegistrationClient:
    def __init__(self,cloud):self.cloud=cloud
    def signup(self,email,password):
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) or len(password)>128 or not parola_guclu_mu(password)[0]:raise ValueError('DPQ_REGISTRATION_INPUT')
        return self.cloud._istek('/auth/v1/signup','POST',{'email':email,'password':password},auth=False)
    def resend(self,email):return self.cloud._istek('/auth/v1/resend','POST',{'type':'signup','email':email},auth=False)
    def verify(self,email,code):
        if not re.fullmatch(r'\d{6,10}',code):raise ValueError('DPQ_EMAIL_CODE')
        result=self.cloud._istek('/auth/v1/verify','POST',{'email':email,'token':code,'type':'email'},auth=False)
        if not result.get('access_token') or not result.get('user',{}).get('id'):raise ValueError('DPQ_AUTH')
        self.cloud.access_token=result['access_token'];self.cloud.refresh_token=result.get('refresh_token','');self.cloud.user_id=result['user']['id']
        return True
    def enroll(self,name):return self.cloud._istek('/rest/v1/rpc/dpq_enroll','POST',{'p_name':name})

class RegistrationDialog(ServerDialog):
    def __init__(self,cloud,parent):
        super().__init__(None,T('Yeni İşletme Oluştur'),parent);self.registration=RegistrationClient(cloud);self.resize(540,640);self.verified=False
        note=QLabel(T('E-postanızı doğrulayın; işletmeniz ve 30 günlük denemeniz otomatik hazırlansın. Kredi kartı gerekmez.'));note.setWordWrap(True);self.body.addWidget(note)
        form=QFormLayout();self.name=QLineEdit();self.name.setMaxLength(120);self.email=QLineEdit();self.email.setMaxLength(254)
        self.password=QLineEdit();self.password.setEchoMode(QLineEdit.EchoMode.Password);self.password.setMaxLength(128)
        self.confirm=QLineEdit();self.confirm.setEchoMode(QLineEdit.EchoMode.Password);self.confirm.setMaxLength(128)
        for label,w in [(T('İşletme adı'),self.name),(T('E-posta'),self.email),(T('Parola (en az 14 karakter)'),self.password),(T('Parolayı tekrar yazın'),self.confirm)]:form.addRow(label,w)
        self.body.addLayout(form)
        rule=QLabel(T('Büyük harf, küçük harf, rakam ve özel sembol kullanın. Parolanızda boşluk bulunmasın.'));rule.setWordWrap(True);self.body.addWidget(rule)
        self.send_code=self.button(T('Doğrulama Kodu Gönder'),self.signup)
        self.code=QLineEdit();self.code.setPlaceholderText(T('E-postadaki doğrulama kodu'));self.code.setMaxLength(10);self.body.addWidget(self.code)
        self.verify_button=self.button(T('E-postayı Doğrula ve İşletmeyi Aç'),self.verify);self.verify_button.setEnabled(False)
        self.resend_button=self.button(T('Kodu Yeniden Gönder'),self.resend);self.resend_button.setEnabled(False)
        self.cooldown=QTimer(self);self.cooldown.setSingleShot(True);self.cooldown.timeout.connect(lambda:self.resend_button.setEnabled(True))
    def signup(self):
        if not 2<=len(self.name.text().strip())<=120 or self.password.text()!=self.confirm.text():self.status_label.setText(T('İşletme adını ve eşleşen parolaları kontrol edin.'));return
        email=self.email.text().strip();password=self.password.text()
        self.run(lambda:self.registration.signup(email,password),self.sent)
    def sent(self,result):
        for field in (self.email,self.password,self.confirm):field.setReadOnly(True)
        self.send_code.setEnabled(False);self.verify_button.setEnabled(True);self.resend_button.setEnabled(False);self.cooldown.start(60000)
        self.status_label.setText(T('E-postadaki kodu yazın. Spam klasörünü de kontrol edin. Hesabınız zaten varsa giriş ekranını kullanın.'))
    def resend(self):
        email=self.email.text().strip();self.run(lambda:self.registration.resend(email),self.sent)
    def verify(self):
        email=self.email.text().strip();code=self.code.text().strip();name=self.name.text().strip()
        def operation():
            if not self.verified:self.registration.verify(email,code);self.verified=True
            return self.registration.enroll(name)
        self.run(operation,lambda _:self.accept())

class BillingClient:
    def __init__(self,cloud):self.cloud=cloud
    def catalog(self):return self.cloud._istek('/rest/v1/rpc/dpq_checkout_catalog','POST',{})
    def create(self,offer,request,buyer):
        return self.cloud._istek('/functions/v1/payment-checkout','POST',{'action':'create','offer':offer,'request_id':request,'buyer':buyer,'accepted_terms':True,'locale':language()})
    def status(self,order):return self.cloud._istek('/functions/v1/payment-checkout','POST',{'action':'status','order_id':order})

class CheckoutDialog(ServerDialog):
    def __init__(self,cloud,parent):
        super().__init__(None,T('Abonelik Satın Al'),parent);self.billing=BillingClient(cloud);self.cloud=cloud;self.resize(590,760)
        self.request_id=str(uuid.uuid4());self.order_id=None;self.offers={};self.environment='sandbox';self.catalogue={}
        self.offer=QComboBox();self.body.addWidget(self.offer);self.fields={};form=QFormLayout()
        for key,label in [('name',T('Ad')),('surname',T('Soyad')),('gsmNumber',T('Telefon (+90…)')),('identityNumber',T('Fatura için kimlik / vergi numarası')),('address',T('Fatura adresi')),('city',T('Şehir')),('country',T('Ülke'))]:
            edit=QLineEdit();edit.setMaxLength(300 if key=='address' else 80);form.addRow(label,edit);self.fields[key]=edit
        self.fields['country'].setText('Turkey');self.body.addLayout(form)
        self.note=QLabel(T('Kart bilgileri ödeme sağlayıcısının güvenli sayfasında girilir. DeporiaQ kart bilgilerini kaydetmez.'));self.note.setWordWrap(True);self.body.addWidget(self.note)
        links=QHBoxLayout();self.button(T('Satış Koşulları'),lambda:self.open_policy('terms_url'),links);self.button(T('Gizlilik'),lambda:self.open_policy('privacy_url'),links);self.body.addLayout(links)
        self.accepted=QCheckBox(T('Satış koşullarını ve gizlilik bilgisini okudum.'));self.body.addWidget(self.accepted)
        self.pay=self.button(T('Güvenli Ödemeye Geç'),self.create);self.pay.setEnabled(False)
        self.check=self.button(T('Ödeme Durumunu Denetle'),self.poll);self.check.setEnabled(False)
        self.timer=QTimer(self);self.timer.setInterval(10000);self.timer.timeout.connect(self.poll)
        self.run(self.billing.catalog,self.loaded)
    def loaded(self,data):
        self.catalogue=data;self.environment=data.get('environment','sandbox')
        for offer in data.get('offers',[]):
            self.offers[offer['code']]=offer
            self.offer.addItem(T('{plan} · {months} ay · {devices} bilgisayar · {amount:.2f} TL',plan=offer['plan'].title(),months=offer['months'],devices=offer['devices'],amount=offer['amount_minor']/100),offer['code'])
        enabled=bool(data.get('enabled') and data.get('can_buy') and self.offers)
        self.pay.setEnabled(enabled)
        if not data.get('can_buy'):self.status_label.setText(T('Abonelik satın alma yetkisi yalnızca işletme sahibindedir.'))
        elif not enabled:self.status_label.setText(T('Çevrimiçi ödeme henüz açılmadı. Paketiniz ve mevcut süreniz korunur.'))
        elif self.environment=='sandbox':self.status_label.setText(T('Test ortamı: Gerçek tahsilat ve abonelik etkinleştirme yapılmaz.'))
        else:self.status_label.setText(T('Tek seferlik ödeme yapılır. Kalan abonelik sürenize seçtiğiniz süre eklenir; otomatik kart çekimi yapılmaz.'))
        saved=self.cloud.vt.ayar_getir('billing_order_'+self.cloud.company_id,'')
        if saved:self.order_id=saved;self.check.setEnabled(True)
    def open_policy(self,key):
        url=self.catalogue.get(key,'');p=urlparse(url)
        if p.scheme=='https' and p.hostname and not p.username and not p.password:QDesktopServices.openUrl(QUrl(url))
    def create(self):
        if not self.accepted.isChecked():self.status_label.setText(T('Devam etmek için satış koşullarını okuyup onaylayın.'));return
        buyer={key:w.text().strip() for key,w in self.fields.items()}
        if any(len(v)<2 for v in buyer.values()):self.status_label.setText(T('Fatura ve iletişim alanlarını doldurun.'));return
        offer=self.offer.currentData()
        if offer not in self.offers:return
        self.run(lambda:self.billing.create(offer,self.request_id,buyer),self.created)
    def created(self,result):
        self.order_id=result['order_id'];self.cloud.vt.ayar_kaydet('billing_order_'+self.cloud.company_id,self.order_id);self.cloud.vt.baglanti.commit()
        self.pay.setEnabled(False);self.offer.setEnabled(False);self.check.setEnabled(True)
        for field in self.fields.values():field.clear()
        if result.get('paid'):self.show_payment(result);return
        try:url=validated_payment_url(result['url'],result['environment'])
        except (ValueError,KeyError):self.status_label.setText(T('Ödeme adresi doğrulanamadı. Destek talebi oluşturun.'));return
        QDesktopServices.openUrl(QUrl(url));self.timer.start();self.status_label.setText(T('Ödeme sayfası açıldı. Ödeme sonucunu burada otomatik kontrol ediyoruz.'))
    def poll(self):
        if self.order_id and self.job is None and self.isVisible():self.run(lambda:self.billing.status(self.order_id),self.show_payment)
    def show_payment(self,result):
        if result.get('paid'):
            self.timer.stop();self.check.setEnabled(False);self.status_label.setText(T('Ödemeniz doğrulandı, aboneliğiniz etkinleştirildi. Paket ekranını yenileyebilirsiniz.'))
        elif result.get('sandbox'):
            self.timer.stop();self.status_label.setText(T('Test ödemesi tamamlandı. Gerçek abonelik değiştirilmedi.'))
        elif result.get('rejected'):
            self.timer.stop();self.status_label.setText(T('Ödeme onaylanmadı. Aboneliğiniz değiştirilmedi.'))
        else:self.status_label.setText(T('Ödeme henüz doğrulanmadı. Banka kontrolü sürüyorsa biraz sonra tekrar denetleyin.'))
    def closeEvent(self,event):
        super().closeEvent(event)
        if event.isAccepted():self.timer.stop()
