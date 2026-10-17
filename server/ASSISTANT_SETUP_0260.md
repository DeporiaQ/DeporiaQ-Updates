# DeporiaQ 0.26.0 — Asistan ve arama kurulumu

Bu geçiş mevcut 0.25.0 sunucusuna uygulanır. Abonelik bitiş tarihlerini, satışları, ürünleri veya stok adetlerini değiştirmez.

1. Supabase → **SQL Editor → New query**: `DEPORIAQ_CLOUD_0.26.0_UPDATE.sql` içeriğinin tamamını çalıştırın. Sonuç `installed_version = 0.26.0` olmalıdır.
2. OpenAI API projenizde sunucu için bir API anahtarı oluşturun. Anahtarı sohbet mesajına, masaüstü ayarlarına veya kod dosyasına yazmayın.
3. GitHub → **DeporiaQ/DeporiaQ-Updates → Settings → Secrets and variables → Actions → New repository secret**: Adı `OPENAI_API_KEY`, değeri API anahtarı olsun. Mevcut Supabase ve destek e-posta sırlarını değiştirmeyin.
4. `DeporiaQ 0.26 Assistant Deployment` iş akışını `codex/deporiaq-0.26.0` dalından çalıştırın. Dağıtım, SQL sürümünü ve gerekli sırların varlığını denetler. Eksik varsa hiçbir sunucu değişikliği yapmadan bekler.
5. Dağıtım testi bir kısa kullanım sorusunu gerçek API'ye gönderir. OpenAI API hesabında kullanılabilir bakiye/ödeme ve model erişimi gereklidir. API kullanımı ayrıca ücretlenir.
6. Dağıtım başarılı olduktan sonra uygulamada Asistan → “Şubeler arası stok transferi nasıl yapılır?” sorusunu deneyin. Yanıt uygulama içinde kalmalıdır.

API anahtarı yalnızca sunucuda bulunur; kurulum EXE'sine eklenmez. GitHub'dan Supabase Secrets'a aktarılır. Varsayılan model `gpt-5.4-mini`; sonraki değişiklikler doğrulama gerektirir.

Asistan yalnızca yazılan sohbeti ve uygulama kullanım rehberini gönderir. Ürün, müşteri, satış, fiyat, stok veya parola kayıtlarını otomatik olarak modele göndermez. Sohbet geçmişi uygulama belleğinde son üç soru/yanıtla sınırlıdır. “Yeni sohbet” bu geçmişi temizler. OpenAI isteğinde `store:false` kullanılır; bunun tüm sağlayıcı güvenlik günlüklerinin tutulmayacağı anlamına geldiği iddia edilmez.

Günlük limitler UTC gününe göre kullanıcı başına 50, işletme başına 200 istektir. Sorular arasında en az 5 saniye gerekir. Başarısız sağlayıcı istekleri de kötüye kullanımı sınırlamak için kotaya sayılır. Bu limitler OpenAI hesabının genel bütçe ayarının yerini almaz.

Asistan canlı stok okumaz ve işlem yapmaz; yalnızca kullanım desteği verir. Uygulama sunucu tarafında etkin üyelik, abonelik ve cihaz kaydı denetler. Eksik anahtar ve servis hatası durumunda uydurulmuş yanıt veya başarı mesajı göstermez.

Kaynak: https://developers.openai.com/api/docs/guides/text
