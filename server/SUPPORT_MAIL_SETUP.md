# Destek e-postasını etkinleştirme

Masaüstü uygulamasına parola veya yönetici anahtarı eklenmez. Gönder düğmesi talebi Supabase'e kaydeder; bu görev bekleyen talepleri deporiaq@gmail.com adresine SMTP üzerinden iletir.

GitHub → DeporiaQ/DeporiaQ-Updates → Settings → Secrets and variables → Actions:
1. Secrets sekmesinde DPQ_SERVICE_ROLE_KEY oluşturun: çalışan Supabase projesinin service_role anahtarı. Mevcut SUPABASE_URL aynı projeyi göstermelidir.
2. DPQ_SMTP_PASSWORD oluşturun: deporiaq@gmail.com için Google uygulama parolası. Normal Google hesap parolası kullanmayın.
3. Variables sekmesinde DPQ_SUPPORT_MAIL_ENABLED değerini true yapın.
4. Actions → DeporiaQ support email delivery → Run workflow ile ilk çalışmayı kontrol edin.

Görev etkinleştirilince önceden kaydedilmiş bekleyen talepler de gönderilir. Zamanlanmış görev yaklaşık 5 dakikada bir kontrol eder; GitHub gecikmeleri olabilir. Anında teslim garantisi yoktur. İş akışı kapalıysa veya secrets eksikse uygulama talebi kaydeder ancak e-posta iletimi gerçekleşmez. SMTP sunucusunun kabulü alıcı gelen kutusuna teslim garantisi değildir.

Gerekli dpq_claim_support ve dpq_finish_support SQL fonksiyonları server/003_support.sql içinde ve 0.24.0 sunucu geçişinde bulunur. Eksik fonksiyon hatası alınırsa önce ilgili geçişin uygulandığı doğrulanmalıdır.

Anahtarları sohbet mesajına veya kaynak koda koymayın. Gönderim görevi yalnızca güvenilir GitHub Actions secrets üzerinden okur.
