"""Presentation-only errors. Protocol classification always uses original responses."""
import re
from deporiaq_i18n import T,language
from deporiaq_translations import EN
ERRORS={
 'DPQ_AUTH':('Cloud oturumunuzu doğrulayın.','Verify your Cloud session.'),
 'DPQ_SESSION':('Oturum doğrulanamadı. Yeniden giriş yapın.','The session could not be verified. Sign in again.'),
 'DPQ_COMPANY':('Tek ve etkin işletme üyeliği gereklidir.','One active business membership is required.'),
 'DPQ_TENANT':('Bu kayıt işletmenize ait değil.','This record does not belong to your business.'),
 'DPQ_OWNER':('İşletme adını yalnızca ana hesap sahibi değiştirebilir.','Only the primary account owner can change the business name.'),
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
for tr,en in ERRORS.values():EN[tr]=en

def error_text(message):
    text=str(message)
    if language()=='tr':return text
    match=re.search(r'\bDPQ_[A-Z_]+\b',text)
    if match and match.group() in ERRORS:return match.group()+': '+str(T(ERRORS[match.group()][0]))
    if 'PGRST202' in text:return str(T(ERRORS['DPQ_NOT_READY'][0]))
    return T(text) if text in EN else text
