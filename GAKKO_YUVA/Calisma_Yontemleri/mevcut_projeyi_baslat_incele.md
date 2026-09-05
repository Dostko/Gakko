# Mevcut Projeyi Başlat ve İncele

## Amaç

Bu çalışma yöntemi, kullanıcı Gakko içinde bir proje seçtiğinde projenin güvenli ve kontrollü biçimde anlaşılmasını sağlar.

## Çalışma Yöntemi

1. Kullanıcının seçtiği klasörü aktif proje kökü olarak kabul et.

2. Projenin tamamını topluca okuma veya bağlama yükleme.

3. Kullanıcı bir başlangıç dosyası belirtmişse önce yalnız bu dosyayı incele.

4. Başlangıç dosyası belirtilmemişse proje yapısını anlamak için yalnız gerekli en küçük bilgiyi edin ve uygun başlangıç noktasını belirle.

5. İncelenen dosyanın doğrudan bağlı olduğu diğer dosyalara yalnız ihtiyaç oluştuğunda geç.

6. Dosya, klasör, bağlantı veya çalışma biçimi hakkında görülmeyen bilgileri varsayma.

7. Mevcut yapıyı yeterince anlamadan değişiklik yapma.

8. Bir değişiklik gerekiyorsa:

   * mevcut durumu kısa şekilde açıkla,
   * gerekli tek değişikliği öner,
   * kullanıcı onayı olmadan uygulama yapma.

9. Projeye ait büyük miktarda içeriği gereksiz yere bağlama taşıma. Yalnız mevcut görev için gerekli kaynakları kullan.

10. Kullanıcıya soru sormak gerektiğinde `ask_user_question` aracını kullanma; soruyu normal sohbet mesajı olarak sor.

## Sınır

Bu çalışma yöntemi yalnız projenin başlatılması ve ilk incelenmesi içindir.

Proje değiştirme, test ve doğrulama, hata ayıklama veya başka geliştirme süreçleri gerektiğinde ayrı çalışma yöntemleriyle ele alınır.