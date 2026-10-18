"""Presentation-only errors. Protocol classification always uses original responses."""
import re
from deporiaq_i18n import T,language
from deporiaq_translations import EN
ERRORS={
 'DPQ_AUTH':('Cloud oturumunuzu doğrulayın.','Verify your Cloud session.'),
 'DPQ_SESSION':('Oturum doğrulanamadı. Yeniden giriş yapın.','The session could not be verified. Sign in again.'),
 'DPQ_COMPANY':('Tek ve etkin işletme üyeliği gereklidir.','One active business membership is required.'),
 'DPQ_TENANT':('Bu kayıt işletmenize ait değil.','This record does not belong to your business.'),
 'DPQ_OWNER':('Bu işlem yalnızca işletmenin ana hesap sahibine açıktır.','This action is available only to the primary business owner.'),
 'DPQ_ROLE':('Bu işlem için yetkiniz bulunmuyor.','You do not have permission for this action.'),
 'DPQ_LOCATION_ROLE':('Bu konumda işlem yapma yetkiniz bulunmuyor.','You do not have permission to act at this location.'),
 'DPQ_CONFLICT':('Kayıt başka bir işlemde değişti. Ekranı yenileyip tekrar kontrol edin.','The record changed in another action. Refresh the screen and review it again.'),
 'DPQ_LICENSE':('Etkin bir abonelik gereklidir. Paketim ve Abonelik bölümünü kontrol edin.','An active subscription is required. Check Plan and Subscription.'),
 'DPQ_DEVICE':('Bu bilgisayarın etkin cihaz kaydı gerekli.','An active device registration is required for this computer.'),
 'DPQ_LIMIT':('Paketinizin bilgisayar sınırına ulaşıldı.','Your plan has reached its computer limit.'),
 'DPQ_STOCK':('Satılabilir stok bu işlem için yeterli değil. Stokları yenileyin.','There is not enough available stock. Refresh the stock list.'),
 'DPQ_RESERVED':('Ürünün ayrılmış stoğu bulunuyor. Rezervasyonları kontrol edin.','The product has reserved stock. Review its reservations.'),
 'DPQ_PRICE':('Ürün fiyatı değişmiş. Güncel fiyatı kontrol edin.','The product price changed. Check the current price.'),
 'DPQ_PRODUCT':('Geçerli ve etkin bir ürün seçin.','Select a valid active product.'),
 'DPQ_LOCATION':('Geçerli ve etkin bir konum seçin.','Select a valid active location.'),
 'DPQ_INPUT':('Alanları, adetleri ve zorunlu bilgileri kontrol edin.','Check the fields, quantities and required information.'),
 'DPQ_PAYMENT':('Ödeme toplamı satış toplamıyla eşleşmiyor.','Payment amounts do not match the sale total.'),
 'DPQ_APPROVAL':('Bu indirim için geçerli yönetici onayı gerekli.','Valid administrator approval is required for this discount.'),
 'DPQ_NOT_READY':('Bu işletme için sunucu güncellemesi gerekli. Yöneticinize başvurun.','This business needs a server update. Contact your administrator.'),
 'DPQ_STATE':('Kaydın mevcut durumu bu işleme uygun değil. Ekranı yenileyin.','The current record status does not allow this action. Refresh the screen.'),
 'DPQ_ORDER':('Sipariş bulunamadı veya bu işlem için uygun değil.','The order was not found or does not allow this action.'),
 'DPQ_AI_QUOTA':('Asistanın günlük kullanım sınırına ulaşıldı.','The daily assistant limit has been reached.'),
 'DPQ_AI_RATE':('Yeni soru için birkaç saniye bekleyin.','Wait a few seconds before asking another question.'),
 'DPQ_RATE':('İşlem sınırına ulaşıldı. Bir süre sonra yeniden deneyin.','The request limit has been reached. Try again shortly.')}
ERRORS.update({
 'DPQ_EMAIL_VERIFY':('Önce e-posta adresinizi doğrulayın.','Verify your email address first.'),
 'DPQ_EMAIL_CODE':('E-postadaki doğrulama kodunu kontrol edin.','Check the verification code in your email.'),
 'DPQ_REGISTRATION_INPUT':('Geçerli e-posta ve en az 14 karakterlik parola yazın.','Enter a valid email and a password of at least 14 characters.'),
 'DPQ_ALREADY_MEMBER':('Bu hesap zaten bir işletmeye bağlı. Giriş ekranını kullanın.','This account already belongs to a business. Use the sign-in screen.'),
 'DPQ_MEMBERSHIP':('İşletme üyeliğiniz etkin değil. Destek ekibiyle iletişime geçin.','Your business membership is inactive. Contact support.'),
 'DPQ_SIGNUP_CLOSED':('Yeni işletme kaydı henüz açılmadı. Bir süre sonra tekrar deneyin.','New business registration is not available yet. Try again later.'),
 'DPQ_BILLING_CLOSED':('Çevrimiçi ödeme henüz açılmadı.','Online payment is not available yet.'),
 'DPQ_BILLING_DETAILS':('Fatura bilgilerini ve uluslararası biçimde telefon numaranızı kontrol edin.','Check your billing details and phone number in international format.'),
 'DPQ_CHECKOUT_EXPIRED':('Ödeme bağlantısının süresi doldu. Paket ekranını yeniden açın.','The payment link expired. Reopen the plan screen.'),
 'DPQ_CHECKOUT_REVIEW':('Ödeme bağlantısının sonucu belirsiz. Yeniden ödeme yapmadan destek talebi oluşturun.','The payment-link result is uncertain. Contact support before paying again.'),
 'DPQ_PAYMENT_MISMATCH':('Ödeme bilgileri doğrulanamadı. Yeniden ödeme yapmadan destek talebi oluşturun.','Payment details could not be verified. Contact support before paying again.'),
 'DPQ_PAYMENT_UNAVAILABLE':('Ödeme hizmetine ulaşılamadı. Ödeme durumunu denetleyin.','The payment service is unavailable. Check the payment status.'),
 'DPQ_PROVIDER_UNAVAILABLE':('Ödeme sağlayıcısından yanıt alınamadı. Ödeme durumunu kontrol edin.','No response from the payment provider. Check the payment status.'),
 'DPQ_DOWNGRADE':('Mevcut ödenmiş süre bitmeden daha küçük pakete geçilemez.','A smaller plan cannot replace the current paid plan before it expires.'),
 'DPQ_DOWNGRADE_REVIEW':('Paketiniz bu ödeme sırasında değişmiş. Destek ekibi ödemenizi kontrol etmelidir.','Your plan changed during payment. Support needs to review this payment.'),
 'DPQ_SUBSCRIPTION_REVIEW':('Abonelik durumu için destek ekibinin incelemesi gerekiyor.','Support needs to review the subscription status.'),
 'DPQ_BILLING_RATE':('Çok fazla ödeme bağlantısı açıldı. Bir süre sonra yeniden deneyin.','Too many payment links were created. Try again later.'),
})
for tr,en in ERRORS.values():EN[tr]=en

def error_text(message):
    text=str(message)
    match=re.search(r'\bDPQ_[A-Z_]+\b',text)
    if match and match.group() in ERRORS:return match.group()+': '+str(T(ERRORS[match.group()][0]))
    if language()=='tr':return text
    if 'PGRST202' in text:return str(T(ERRORS['DPQ_NOT_READY'][0]))
    return T(text) if text in EN else text
