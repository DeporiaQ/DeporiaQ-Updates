# DeporiaQ 0.26.0 — Asistan ve arama kurulumu

Bu geçiş mevcut 0.25.0 sunucusuna uygulanır. Abonelik bitiş tarihlerini, satışları, ürünleri veya stok adetlerini değiştirmez.

1. [SQL dosyasını](https://github.com/DeporiaQ/DeporiaQ-Updates/blob/codex/deporiaq-0.26.0/DEPORIAQ_CLOUD_0.26.0_UPDATE.sql) açın. **Raw** ile yalnızca SQL metnini gösterin; **Ctrl+A → Ctrl+C** ile tamamını kopyalayın. Supabase → **SQL Editor → New query** alanına yapıştırıp **Run** seçin. Sonuç `installed_version = 0.26.0` olmalıdır.
2. [OpenAI API anahtarları](https://platform.openai.com/api-keys) sayfasında DeporiaQ için bir anahtar oluşturun. Anahtarı sohbet mesajına, masaüstü ayarlarına veya kod dosyasına yazmayın.
3. [GitHub Actions sırları](https://github.com/DeporiaQ/DeporiaQ-Updates/settings/secrets/actions) → **New repository secret**: **Name** alanına `OPENAI_API_KEY`, **Secret** alanına API anahtarını girip **Add secret** seçin. Mevcut Supabase ve destek e-posta sırlarını değiştirmeyin.
4. SQL ve anahtar hazır olduğunda `DeporiaQ 0.26 Assistant Deployment` iş akışı çalıştırılır. Teknik tetikleme: `codex/deporiaq-0.26.0` dalındaki `server/ACTIVATE_ASSISTANT_0260` dosyasına yeni bir etkinleştirme notu commit edilir. Kullanıcının Actions ekranından iş akışı araması gerekmez. Dağıtım SQL sürümünü ve gerekli sırların varlığını denetler. Eksik varsa sunucu değişikliği yapmadan bekler; yeşil ön kontrol tek başına dağıtımın yapıldığı anlamına gelmez, `deploy` işi de başarılı olmalıdır.
5. Dağıtım testi bir kısa kullanım sorusunu gerçek API'ye gönderir. OpenAI API hesabında kullanılabilir bakiye/ödeme ve model erişimi gereklidir. API kullanımı ayrıca ücretlenir.
6. Dağıtım başarılı olduktan sonra uygulamada Asistan → “Şubeler arası stok transferi nasıl yapılır?” sorusunu deneyin. Yanıt uygulama içinde kalmalıdır.

API anahtarı yalnızca sunucuda bulunur; kurulum EXE'sine eklenmez. GitHub'dan Supabase Secrets'a aktarılır. Varsayılan model `gpt-5.4-mini`; sonraki değişiklikler doğrulama gerektirir.

Asistan yalnızca yazılan sohbeti ve uygulama kullanım rehberini gönderir. Ürün, müşteri, satış, fiyat, stok veya parola kayıtlarını otomatik olarak modele göndermez. Sohbet geçmişi uygulama belleğinde son üç soru/yanıtla sınırlıdır. “Yeni sohbet” bu geçmişi temizler. OpenAI isteğinde `store:false` kullanılır; bunun tüm sağlayıcı güvenlik günlüklerinin tutulmayacağı anlamına geldiği iddia edilmez.

Günlük limitler UTC gününe göre kullanıcı başına 50, işletme başına 200 istektir. Sorular arasında en az 5 saniye gerekir. Başarısız sağlayıcı istekleri de kötüye kullanımı sınırlamak için kotaya sayılır. Bu limitler OpenAI hesabının genel bütçe ayarının yerini almaz.

Asistan canlı stok okumaz ve işlem yapmaz; yalnızca kullanım desteği verir. Uygulama sunucu tarafında etkin üyelik, abonelik ve cihaz kaydı denetler. Eksik anahtar ve servis hatası durumunda uydurulmuş yanıt veya başarı mesajı göstermez.

Kaynaklar:
- https://developers.openai.com/api/docs/guides/text
- https://help.openai.com/en/articles/9039756-managing-billing-for-chatgpt-and-the-api-platform
- https://help.openai.com/en/articles/4936850-where-do-i-find-my-openai-api-key
