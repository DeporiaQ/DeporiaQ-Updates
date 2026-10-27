"""Reviewed offline usage guide and conservative bilingual topic matching.

No model, network, database, credential, billing or filesystem access. This is
retrieval of authored instructions, not generative AI or live business data.
"""
from dataclasses import dataclass
import re
import unicodedata
from difflib import SequenceMatcher

@dataclass(frozen=True)
class Topic:
    key: str
    title: str
    title_en: str
    body: str
    body_en: str
    phrases: tuple[str, ...]
    actions: tuple[str, ...]
    source: str = 'deporiaq_assistant_guide.py'

TOPICS = (
    Topic('product','Ürün kartı oluşturma','Create a product',
          '1. Stok ve Ürünler → Ürünler ve Stoklar ekranını açın.\n2. Ürün ekleme alanında barkod, ad ve fiyat bilgilerini doldurun.\n3. Kaydetmeden önce barkodu kontrol edin.\n\nÜrün kartı oluşturmak stok adedi eklemez. Adet eklemek için Stok Girişi kullanılır.',
          '1. Open Products & Stock → Products & Stock.\n2. Enter the barcode, name and prices in the new-product section.\n3. Check the barcode before saving.\n\nCreating a product does not add stock. Use Stock Receipt to add quantities.',
          ('urun ekle','urun olustur','yeni urun','kitap ekle','add product','create product','new product'),('catalog','receive')),
    Topic('receive','Stok girişi','Stock receipt',
          '1. Stok ve Ürünler → Stok Girişi ekranını açın.\n2. Ürünü ve giriş yapılacak konumu seçin.\n3. Eklenecek pozitif tam adedi girip bilgileri kontrol edin.\n4. İşlemi onaylayın; sunucu sonucu gelmeden tamamlandı kabul etmeyin.\n\nBu alan mevcut stoğa ekleme yapar; fiziksel sayım toplamı için Stok Sayımı kullanın.',
          '1. Open Products & Stock → Stock Receipt.\n2. Select the product and receiving location.\n3. Enter the positive whole quantity to add and check the details.\n4. Confirm and wait for the server result.\n\nThis adds stock. Use Stock Count to enter a physically counted total.',
          ('stok gir','stok ekle','stok artir','mal kabul','adet ekle','stock receipt','add stock','increase stock','receive goods'),('receive','count')),
    Topic('lookup','Ürün ve stok sorgulama','Find products and stock',
          'Üstteki arama alanına ürün adı veya barkod yazın; Ctrl+K ile doğrudan aramaya geçebilirsiniz. Ürün sonucunu seçip konumu ve satılabilir adedi kontrol edin.\n\nAsistan canlı stok okumaz. Bir kitabın kaç adet olduğunu buradan söyleyemem; güncel adet için stok ekranını kullanın. Aramada ürün bulunması, seçtiğiniz şubede stok olduğu anlamına gelmez.',
          'Enter a product name or barcode in the top search. Ctrl+K focuses search. Select the product, then check its location and available quantity.\n\nThe assistant cannot read live stock or provide an exact count. Use the stock screen for quantities. Finding a product does not mean it is available at your branch.',
          ('stok sorgula','stok bul','kac adet','kac tane','stok var','urun ara','barkod ara','stok yok','find product','check stock','how many','available stock','search barcode','out of stock'),('search','catalog','branch_sale')),
    Topic('transfer','Şubeler arası transfer','Transfer between locations',
          '1. Depolar ve Transferler → Stok Transferi ekranını açın.\n2. Kaynak ve hedef konumu seçin.\n3. Ürünü/barkodu ve aktarılacak tam adedi belirleyin.\n4. Kaynak, hedef ve adedi kontrol edip onaylayın.\n\nTransfer satılabilir stokla sınırlıdır; kaynak stok düşer ve hedef stok artar. Asistan transfer yapmaz, yalnızca ekranı açar.',
          '1. Open Warehouses / Transfers → Stock Transfer.\n2. Choose the source and destination.\n3. Select the product/barcode and whole quantity.\n4. Check the locations and quantity, then confirm.\n\nTransfers are limited to available stock. The source decreases and the destination increases. The assistant only opens the screen; it does not transfer stock.',
          ('transfer','stok aktar','sube aktar','depo aktar','move stock','stock transfer'),('transfer',)),
    Topic('count','Fiziksel stok sayımı','Physical stock count',
          'Stok ve Ürünler → Stok Sayımı ekranında konumu ve ürünü seçin. Fiziksel olarak saydığınız toplam adedi girin; eklenecek farkı girmeyin. Açıklamayı yazıp sonucu kontrol edin.\n\nAyrılmış stokla çelişen sayımlar sunucuda reddedilebilir. Önce ilgili rezervasyonları kontrol edin.',
          'In Products & Stock → Stock Count, choose the location and product. Enter the physically counted total, not the difference to add. Enter a note and check the result.\n\nThe server may reject counts that conflict with reserved stock. Review those reservations first.',
          ('stok say','sayim','fiziksel say','stock count','physical count','inventory count'),('count',)),
    Topic('sale','Barkodla satış','Barcode sales',
          'Satışlar bölümünde Çok Ürünlü Satış veya Şube Satış / Rezervasyon ekranını açın. Barkodu okutun, ürünü ve tam adedi kontrol edin. Sepet ve ödeme bilgilerini gözden geçirdikten sonra satış işlemini onaylayın.\n\nStok yoksa Şube / Depo Stoklarını Sorgula seçeneğiyle başka konumları inceleyebilirsiniz. Bu rehber satış kaydetmez.',
          'Open Sales and choose Multi-Item Sale or Branch Sales / Reservations. Scan the barcode and check the product and whole quantity. Review the basket and payment details before confirming.\n\nIf unavailable locally, use Check Branch / Warehouse Stock. This guide does not record a sale.',
          ('satis','urun sat','kitap sat','kitab sat','nasil sat','barkod okut','sale','sell product','sell book','scan barcode'),('sales','branch_sale')),
    Topic('reservation','Rezervasyon ve kargo','Reservations and shipping',
          '1. Satışlar → Şube Satış / Rezervasyon ekranında barkodu arayın.\n2. Şube / Depo Stoklarını Sorgula ile uygun konumu seçin.\n3. Şubeden teslim veya kargo rezervasyonu seçin.\n4. Müşteri ve iletişim bilgilerini; kargo için adresi doldurup kontrol edin.\n\nRezervasyon oluşturmak ödeme alındığı veya teslimat yapıldığı anlamına gelmez.',
          '1. Search the barcode in Sales → Branch Sales / Reservations.\n2. Check Branch / Warehouse Stock and choose a location.\n3. Choose collection or shipping reservation.\n4. Check the customer/contact details and the delivery address for shipping.\n\nA reservation does not mean payment or delivery is complete.',
          ('rezervasyon','kargo','subeden teslim','reservation','reserve','shipping','collect branch','pickup'),('branch_sale',)),
    Topic('basket','Sepet ve bekletilen satış','Basket and held sales',
          'Satışlar → Çok Ürünlü Satış ekranında barkodla ürünleri sepete ekleyin ve adetleri kontrol edin. Satışı daha sonra tamamlayacaksanız sepeti bekletebilirsiniz.\n\nBekletilen sepet stok ayırmaz. Satış tamamlanırken stok yeniden kontrol edilir.',
          'In Sales → Multi-Item Sale, add products by barcode and check quantities. Hold the basket if you want to complete it later.\n\nA held basket does not reserve inventory. Stock is checked again when the sale completes.',
          ('sepet','beklet','basket','hold sale','held sale','cart'),('sales',)),
    Topic('payment','Ödeme kaydı','Record payment',
          'Çok Ürünlü Satış ekranında nakit, kart veya bölünmüş ödeme tutarlarını girin. Girilen ödeme toplamı sepet toplamına eşit olmalıdır.\n\nBu alanlar ödeme yöntemini kaydeder. Banka veya POS cihazından otomatik tahsilat yapmaz.',
          'Enter cash, card or split-payment amounts in Multi-Item Sale. The total entered must equal the basket total.\n\nThese fields record the payment method; they do not charge a bank card or POS terminal.',
          ('odeme','nakit','kredi kart','pos','payment','cash','split payment','charge card'),('sales',)),
    Topic('discount','İndirim ve yönetici onayı','Discounts and approval',
          'Personel indirimi işletmenin sınırını aşıyorsa ilgili satış sepeti için yönetici onayı gerekir. Onay belirli sepete bağlıdır ve 15 dakika geçerlidir. Sepeti değiştirirseniz yeniden onay gerekebilir.\n\nYönetim bölümünde Personel İndirim Sınırı ve İndirim Onayları bulunur. Yetki kontrolü sunucuda yapılır.',
          'Staff discounts above the business limit need administrator approval for that basket. Approval is basket-specific and valid for 15 minutes. Changes may require a new approval.\n\nStaff Discount Limit and Discount Approvals are in Management. The server checks permissions.',
          ('indirim','discount','approval'),('sales','management')),
    Topic('purchase','Tedarikçi ve satın alma','Suppliers and purchasing',
          'Yönetim bölümünde tedarikçi kartını oluşturun ve Satın Alma Siparişleri ekranında siparişi kaydedin. Teslimde sağlam/hasarlı adetleri ayrı girin ve kalan adetleri kontrol edin.\n\nSipariş kaydetmek, malların teslim alındığı anlamına gelmez.',
          'Create a supplier in Management, then record the order in Purchase Orders. On receipt, enter good and damaged quantities separately and check the remaining quantities.\n\nRecording an order does not receive the goods.',
          ('tedarik','satin al','mal teslim','supplier','purchase','receive order'),('management',)),
    Topic('damage','Hasarlı ürün ve parti kaydı','Damaged stock and batches',
          'Stok ve Ürünler bölümündeki Hasarlı Ürün Ayır ekranı satılabilir stoktan ayrı hasar kaydı oluşturur. Parti ve Son Kullanma ekranında ürüne bağlı parti/tarih bilgisi tutulur.\n\nParti kaydı otomatik son kullanma tarihi önceliğiyle satış tahsisi yapmaz.',
          'Use Products & Stock → Damaged Stock to record damaged quantities separately from sellable stock. Batch and Expiry stores product batch/date information.\n\nBatch records do not automatically allocate sales by expiry date.',
          ('hasar','parti','son kullanma','damage','batch','expiry','expiration'),('stock_menu',)),
    Topic('details','Ürün ayrıntıları ve barkod etiketi','Product details and barcode labels',
          'Stok ve Ürünler → Ürün Ayrıntıları bölümünde ürünün kategori, etiket, yazar/marka, yayınevi/üretici, varyant ve raf bilgilerini düzenleyebilirsiniz. Ürün görseli ve PDF barkod etiketi seçenekleri de bu ekrandadır.\n\nMüşteriye ait ürün adları dil değiştirdiğinizde çevrilmez.',
          'In Products & Stock → Product Details, edit category, tags, author/brand, publisher/manufacturer, variant and shelf information. Product images and PDF barcode labels are also available there.\n\nCustomer-entered product names are not translated when the interface language changes.',
          ('raf','etiket','yazar','yayinevi','urun gorsel','varyant','shelf','label','author','publisher','product image','variant'),('stock_menu',)),
    Topic('import','Excel ve CSV ile ürün ekleme','Import products from Excel or CSV',
          'Yönetim → Excel Ürün İçe Aktarma ekranında dosyayı seçin, sütunları eşleştirin ve önizlemeyi kontrol edin. Barkodları metin olarak tutun; baştaki sıfırları silmeyin. Bir işlemde en fazla 500 satır işlenir.\n\nBu işlem ürün kartı aktarır; stok adedi aktarmaz.',
          'In Management → Import Products from Excel, choose the file, map columns and review the preview. Keep barcodes as text to preserve leading zeros. Each operation accepts up to 500 rows.\n\nThis imports products, not stock quantities.',
          ('excel','csv ice','ice aktar','dosyadan urun','import','spreadsheet'),('management',)),
    Topic('price','Toplu fiyat güncelleme','Bulk price update',
          'Yönetim → Toplu Fiyat Güncelle ekranında değişiklikleri hazırlayıp önizlemeyi kontrol edin. İşlemi onaylamadan önce eski ve yeni fiyatları karşılaştırın.\n\nBaşka bir kullanıcı aynı fiyatı değiştirmişse çakışma oluşabilir; verileri yenileyip yeniden kontrol edin. Asistan fiyat okumaz veya değiştirmez.',
          'Prepare changes in Management → Bulk Price Update and review the preview. Compare old and new prices before applying.\n\nA concurrent price edit may cause a conflict. Refresh and review again. The assistant cannot read or change prices.',
          ('fiyat guncelle','fiyat degistir','toplu fiyat','update price','change price','bulk price'),('management','catalog')),
    Topic('tasks','Kullanıcı rolleri ve yetki devri','User roles and delegation',
          'Ana yönetici, Yönetim → Kullanıcı Yetkileri ekranından kişiyi ve rolü seçebilir. Geçici yetkide bitiş tarihini girin; süresiz yetkide geçici seçeneğini kapatın. Yetki Devrini Kaldır önceki role döndürür. Ana yönetici kimliği değişmez.',
          'The owner can select a user and role in Management → User Permissions. Set an end date for temporary authority or disable the temporary option for an indefinite role. Revoke Delegation restores the base role. Owner identity stays unchanged.',
          ('gorev','yetki devri','gecici yetki','task','assign','delegation'),('management',)),
    Topic('reports','Raporlar ve analiz','Reports and analysis',
          'Raporlar bölümünden stok, kritik stok ve hareket geçmişini açabilirsiniz. Yetkili ana yönetici Operasyon Merkezi analizlerini kullanabilir. Rapor ekranlarında uygun dışa aktarma/yazdırma seçeneklerini seçin.\n\nYerel raporlar önbelleğe dayanır. Güncel Cloud eşitlemesinden sonra verileri yenileyin; öneriler kendiliğinden stok değiştirmez.',
          'Open stock, critical-stock and movement reports from Reports. Authorised primary administrators can use the Operations Centre. Use the available export/print options in each report.\n\nLocal reports use cached data. Refresh after Cloud sync. Suggestions do not change stock automatically.',
          ('rapor','analiz','kar rapor','kritik stok','report','analysis','critical stock','profit'),('reports','operations')),
    Topic('backup','Yedek alma','Back up local data',
          'Ana yönetici Yönetim → Veri ve Yedekleme bölümünü açabilir. Yedek için ayrı bir dosya adı ve konum seçin; başarı mesajını bekleyin.\n\nBu işlem bilgisayardaki yerel veritabanını yedekler. Cloud veritabanının tam sunucu yedeği değildir. Asıl veritabanının üzerine kaydetmeyin.',
          'The primary administrator can open Management → Data and Backup. Choose a separate filename/location and wait for confirmation.\n\nThis backs up the local database on this computer, not the entire Cloud database. Do not overwrite the working database.',
          ('yedek','backup','back up'),('backup',)),
    Topic('company','İşletme adını değiştirme','Change the business name',
          'Ayarlar → Genel bölümünde işletme adını düzenleyip İşletme Bilgisini Kaydet seçin. Sunucu onayından sonra üst başlık güncellenir.\n\nBu yetki yalnızca ana hesap sahibindedir. Diğer yöneticiler adı değiştiremez. Ad başka bir cihazdan değiştirilmişse ayarları kapatıp yeniden açın.',
          'Edit the business name in Settings → General and select Save Business Details. The header updates after server confirmation.\n\nOnly the primary account owner may rename the business. Other administrators cannot. Reopen settings if the name changed on another device.',
          ('isletme adi','sirket adi','firma adi','isletme ism','firma ism','company name','business name','rename business'),('settings',)),
    Topic('cloud','Cloud bağlantısı','Cloud connection',
          'Sol alttaki Cloud göstergesini kontrol edin. Geçici bağlantı hatasında uygulama yeniden dener; her hata oturumun kapandığı anlamına gelmez.\n\nİnternet bağlantısını kontrol edin. Giriş isteniyorsa Ayarlar → Cloud ve Senkronizasyon bölümünden kendi hesabınızla giriş yapın. Sorun sürerse destek talebi oluşturun. Asistan hesabınızın bağlantısını ölçmez.',
          'Check the Cloud indicator at the lower left. Temporary network errors are retried; an error does not always mean you have been signed out.\n\nCheck your internet connection. If sign-in is required, use your account in Settings → Cloud and Sync. Contact support if the issue persists. The assistant does not measure your connection.',
          ('cloud','bulut','baglanti','oturum at','oturum kop','connection','disconnect','signed out','sync'),('settings','support')),
    Topic('password','Parola ve hesap erişimi','Password and account access',
          'Cloud parolanızı unuttuysanız hesap yöneticinizle iletişime geçin. Giriş ekranındaki Şifremi Unuttum açıklamasını da okuyabilirsiniz. Yerel ekran kilidi parolası ile Cloud hesabı aynı işlem değildir.\n\nParola, doğrulama kodu veya API anahtarını asistana yazmayın. Asistan parola sıfırlamaz ve hesap yetkisi vermez.',
          'If you forgot your Cloud password, contact your account administrator. You can also read Forgot Password on the sign-in screen. The local screen-lock password and Cloud account are separate.\n\nDo not enter passwords, verification codes or API keys here. The assistant cannot reset passwords or grant access.',
          ('sifre','parola','password','forgot login','reset account'),('support','settings')),
    Topic('subscription','Paket ve abonelik','Plan and subscription',
          'Paketim ve Abonelik ekranında paketi, bitiş tarihini, kalan süreyi ve cihazları inceleyin. Geri sayım sunucu saatini kullanır; uygulama güncellemesi abonelik süresini sıfırlamaz.\n\nDemo 30 gün/1 bilgisayardır. Single 1, Duo yönetici dahil 3, Plus yönetici dahil 6, Ultra yönetici dahil 20 bilgisayardır. Satın alma etkin değilse destek bölümüne başvurun. Asistan aboneliğinizi uzatamaz veya ödeme alamaz.',
          'Review the plan, expiry date, remaining time and devices in Plan and Subscription. The countdown uses server time; app updates do not reset it.\n\nDemo is 30 days/1 computer. Single supports 1, Duo 3 including the administrator, Plus 6 and Ultra 20. Contact support if purchasing is unavailable. The assistant cannot extend subscriptions or take payment.',
          ('abonelik','paket su','paketim','lisans','demo','subscription','plan','licence','license','trial'),('plans',)),
    Topic('appearance','Tema ve arka plan','Theme and background',
          'Ayarlar içindeki görünüm seçeneklerinden standart arka planı veya kendi görselinizi seçin; saydamlık ve yazı ayarlarını düzenleyin. Sağ üstteki güneş/ay simgesi açık ve karanlık görünümü değiştirir.\n\nAçılış/kapanış logo animasyonunu da görünüm ayarlarından kapatabilirsiniz.',
          'Choose a standard background or your own image in Settings appearance options, then adjust opacity and fonts. The sun/moon icon at the top right switches light and dark mode.\n\nYou can also disable the startup/shutdown logo animation in appearance settings.',
          ('tema','arka plan','karanlik','opak','animasyon','theme','background','dark mode','light mode','opacity','animation'),('settings',)),
    Topic('language','Türkçe ve İngilizce','Turkish and English',
          'Sol menünün altındaki Türk bayrağı Türkçeyi, Birleşik Krallık bayrağı İngilizceyi seçer. Dil tercihiniz kaydedilir.\n\nÜrün adları, barkodlar ve açık formdaki kendi girişleriniz değiştirilmez. Asistanın rehber yanıtları da seçtiğiniz arayüz dilinde gösterilir.',
          'Use the Turkish or UK flag near the bottom of the sidebar to switch languages. Your choice is saved.\n\nProduct names, barcodes and your unsaved form entries stay unchanged. Assistant guide answers follow the interface language too.',
          ('dil','ingilizce','turkce','bayrak','language','english','turkish','flag'),('help',)),
    Topic('notifications','Bildirimler','Notifications',
          'Sağ üstteki zil simgesine tıklayarak bildirimleri açın. Yanındaki sayı okunmamış bildirimleri gösterir. Ayarlar içindeki bildirim seçeneklerinden hangi uyarıları almak istediğinizi düzenleyebilirsiniz.',
          'Click the bell at the top right to open notifications. Its number shows unread items. Choose which alerts to receive in Settings notification options.',
          ('bildirim','zil','notification','bell','alert'),('notifications','settings')),
    Topic('shortcuts','Klavye kısayolları','Keyboard shortcuts',
          'Ctrl+1: Ana Sayfa\nCtrl+2: Stok ve Ürünler\nCtrl+3: Şube Satış\nCtrl+4: İnternet Siparişleri\nCtrl+K: Üst arama alanı\nF5: Destekleyen iş ekranında yenileme\n\nAsistanda Enter gönderir; Shift+Enter yeni satır ekler. Açık ve kaydedilmemiş bir form varsa önce ekrandaki uyarıyı yanıtlayın.',
          'Ctrl+1: Home\nCtrl+2: Products & Stock\nCtrl+3: Branch Sales\nCtrl+4: Online Orders\nCtrl+K: Top search\nF5: Refresh a supported business screen\n\nIn the assistant, Enter submits and Shift+Enter adds a new line. Respond to any unsaved-form prompt first.',
          ('kisayol','ctrl','f5','shortcut','keyboard'),('shortcuts','search')),
    Topic('support','Destek talebi','Support request',
          'Yardım ve Destek → Destek Talebi Gönder ekranında konu, açıklama ve iletişim bilgilerini doldurun. Gönder düğmesine basıp talep numarasını ve gönderim durumunu kontrol edin.\n\nTalebin kaydedilmesi ile e-postanın gelen kutusuna ulaşması farklıdır. Gönderim hatası varsa aynı talebin durumunu kontrol edin. Asistan kendi kendine e-posta göndermez.',
          'In Help and Support → Send Support Request, enter the subject, description and contact details. Click Send, then check the ticket number and sending status.\n\nSaving a ticket is different from delivery to an inbox. Check that ticket if delivery fails. The assistant does not send email automatically.',
          ('destek','mail','eposta','e posta','talep','hata','support','email','ticket','error'),('support',)),
    Topic('update','Uygulamayı güncelleme','Update the application',
          'Ana penceredeki Güncellemeleri Denetle düğmesini kullanın. Yeni sürüm varsa güncelleyicide indirip kurmayı seçin ve gerekirse Windows izin ekranını yanıtlayın. Kurulum uygulamayı kapatıp yeni sürümü açar.\n\nÖnce açık işlemlerinizi kaydedin. Güncelleme için AppData içindeki işletme verilerini silmeyin. Asistan kurulum başlatmaz; düğme yalnızca güncelleme denetimini açar.',
          'Use Check for Updates in the main window. If a version is available, choose download/install in the updater and respond to any Windows permission prompt. Setup closes and reopens the app.\n\nSave ongoing work first. Do not delete business data from AppData. The assistant button only checks for updates; it does not install them.',
          ('guncelle','yeni surum','update','upgrade','new version'),('updates',)),
    Topic('users','Kullanıcılar ve yetkiler','Users and permissions',
          'Kullanıcı yetkileri Cloud işletme üyeliğiyle belirlenir. Yerel bir kullanıcı adını veya rolü değiştirmek sunucu yetkisi vermez. İşletme adını değiştirme yetkisi yalnızca hesap sahibindedir.\n\nAktif kullanıcı listesi 10 saniyede bir denetlenir; bağlantısı kesilen oturumlar son yoklamadan yaklaşık 30 saniye sonra kaybolur. Yetki sorunu için ana yöneticinizle görüşün.',
          'Permissions come from Cloud business membership. Changing a local name or role does not grant server permissions. Only the account owner can rename the business.\n\nPresence is checked every 10 seconds; disconnected sessions disappear about 30 seconds after their last heartbeat. Contact your primary administrator for access issues.',
          ('kullanici','yetki','online','aktif kisi','user','permission','role','active users'),('help',)),
)
from deporiaq_knowledge import CARDS
TOPICS=TOPICS+tuple(Topic(*row) for row in CARDS)
BY_KEY={topic.key:topic for topic in TOPICS}


def fold(text):
    text=str(text).replace('ı','i').replace('İ','i').casefold()
    return ' '.join(re.findall(r'[a-z0-9]+',''.join(c for c in unicodedata.normalize('NFKD',text) if not unicodedata.combining(c))))


def word_matches(term,word):
    if term==word:return True
    if len(term)>=3 and word.startswith(term):return True
    return len(term)>=5 and len(word)>=5 and SequenceMatcher(None,term,word).ratio()>=.84


def lookup(question):
    """Return authored instructions only; broad unmatched questions stay unanswered."""
    return GUIDE_INDEX.lookup(question)


FOLLOW_UP={'nereden acacagim','nereden acilir','nereye tiklayacagim','nereye tiklayayim','bunu ac','ekrani ac','how do i open it','where do i click','open it','where is it'}
GREETINGS={'merhaba','selam','selamlar','hello','hi','hey','tesekkurler','tesekkur ederim','thanks','thank you'}

from deporiaq_knowledge_index import GuideIndex
GUIDE_INDEX=GuideIndex(TOPICS,fold)
QUESTION_FORMS=GUIDE_INDEX.questions
