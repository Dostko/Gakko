# Sohbet Geçmişi

## Amaç

Gakko'nun geçmiş sohbetlerden gerektiğinde bilgi bulmasını sağlamak.

Sohbet geçmişi, proje dosyalarının veya GAKKO_YUVA içeriğinin yerine geçmez.
Yalnızca daha önce kullanıcı ile yapılan konuşmalarda bulunan bilgiyi geri çağırmak için kullanılır.

---

## Kaynak

Sohbet geçmişinin kaynağı Gakko'nun mevcut yerel geçmiş veritabanıdır:

`history.sqlite3`

Bu kaynak salt okunur kullanılır.

Geçmiş araması:

- kayıt eklemez,
- kayıt değiştirmez,
- kayıt silmez,
- aktif projeyi değiştirmez,
- herhangi bir çalışma yöntemini otomatik başlatmaz.

---

## Ne Zaman Kullanılır

Kullanıcının isteği geçmiş konuşmalardaki bilgiye dayanıyorsa sohbet geçmişi aranabilir.

Örnekler:

- "trafel projesinde ne yapmıştık?"
- "geçen sefer bu konuda ne karar vermiştik?"
- "daha önce bununla ilgili ne konuşmuştuk?"
- "en son bu projede hangi işi yapmıştık?"

Güncel proje dosyasında, Git geçmişinde, GAKKO_YUVA içinde veya doğrudan mevcut bağlamda cevap açıkça bulunuyorsa gereksiz geçmiş araması yapılmaz.

---

## Arama Sınırı

Bir kullanıcı isteği için en fazla **1 sohbet geçmişi araması** yapılır.

Bir aramada Qwen'e en fazla **3 ilgili sohbet kaydı** verilir.

Bütün sohbet geçmişi bağlama yüklenmez.

Amaç:

- gereksiz bağlam büyümesini önlemek,
- uzun taramaları engellemek,
- aynı istekte tekrar tekrar geçmiş aramasına girilmesini önlemek.

---

## Sonuç Seçimi

Arama sonucu seçilirken kullanıcının isteğiyle en doğrudan ilişkili kayıtlar tercih edilir.

Mümkün olduğunda şu bilgiler dikkate alınır:

- proje adı,
- konuşma başlığı,
- tarih ve saat,
- kullanıcı mesajı,
- Gakko cevabı.

Aynı bilgiyi tekrar eden kayıtlar gereksiz yere çoğaltılmaz.

Yarım kalmış konuşmalar geçmiş bilgi kaynağı olarak kullanılmaz.
Bir kaydın geçmiş bağlamı olarak seçilebilmesi için en az bir kullanıcı mesajı ve
ona ait en az bir Gakko cevabı bulunmalıdır. Yalnız kullanıcı sorusu bulunan,
cevabı oluşmadan kapanmış veya iptal edilmiş konuşmalar Qwen'e geçmiş sonucu
olarak verilmez.

---

## Sonuç Bulunamazsa

İlgili sohbet kaydı bulunamazsa bu açıkça belirtilir.

Geçmiş bulunamadığı için:

- proje klasörlerinde sınırsız tarama yapılmaz,
- aynı geçmiş araması tekrar edilmez,
- tahmin veya uydurma bilgi üretilmez.

Gerekirse mevcut proje, Git veya GAKKO_YUVA kaynakları ayrı bir ihtiyaç olarak değerlendirilir.

---

## 30 Günlük Kural

Mevcut sohbet geçmişi saklama süresi **30 gün** olarak korunur.

Bu çalışma yöntemi:

- saklama süresini değiştirmez,
- otomatik temizleme davranışını değiştirmez,
- silinmiş geçmişi geri getirmeye çalışmaz.

---

## Qwen ve Proje Akışı

Bu özellik mevcut Qwen Code bağlantısını değiştirmez.

Özellikle:

- Qwen başlatma zinciri değiştirilmez,
- `build_qwen_args` değiştirilmez,
- aktif proje erişimi değiştirilmez,
- GAKKO_YUVA çalışma düzeni değiştirilmez.

Sohbet geçmişi yalnızca gerektiğinde kullanılan ek bir bilgi kaynağıdır.

---

## Temel Akış

```text
Kullanıcı isteği
↓
Qwen isteği değerlendirir
↓
Geçmiş konuşma bilgisi gerekiyor mu?
↓
Hayır → normal akış
Evet
↓
Sohbet geçmişinde 1 kez ara
↓
En fazla 3 ilgili kayıt al
↓
Qwen kayıtları yorumlar
↓
Kullanıcıya cevap verir
```

---

## Temel İlke

Sohbet geçmişi:

**"Daha önce ne konuşmuştuk?"**

sorusunun kaynağıdır.

Proje dosyaları:

**"Projede şu anda ne var?"**

sorusunun kaynağıdır.

GAKKO_YUVA:

**"Gakko nasıl çalışmalı ve hangi kalıcı bilgiye sahip?"**

sorusunun kaynağıdır.

Bu üç sorumluluk birbirine karıştırılmaz.