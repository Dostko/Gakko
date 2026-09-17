# Proje ve Tasarım

## Yeni Proje

Kullanıcının seçtiği klasörü aktif proje kökü olarak kabul et.

Projenin amacı ve başlangıç yapısında kullanıcının isteğini esas al.

Kullanıcı belirtmedikçe:

* teknoloji,
* framework,
* mimari,
* bağımlılık,
* dosya veya klasör yapısı

varsayma.

Mevcut içerik varsa kullanıcı istemeden değiştirme veya üzerine yazma.

---

## Tasarım

Yalnız mevcut ihtiyacı karşılayacak yapıyı oluştur.

Henüz ihtiyaç olmayan:

* özellik,
* katman,
* yardımcı sistem,
* soyutlama,
* bağımlılık

ekleme.

Gelecekte gerekebilir düşüncesi tek başına yeni yapı oluşturmak için yeterli değildir.

---

## Mevcut Yapıyla Uyum

Mevcut projede değişiklik yapmadan önce ilgili yapıyı ve gerçek çağrı yollarını anla.

Çalışan çözüm yeterliyse gereksiz yere değiştirme.

Aynı görevi yapan eski ve yeni iki kalıcı yolu paralel bırakma.

Gerekirse:

1. doğru davranışı belirle,
2. korunacak mevcut davranışları seç,
3. tek temiz implementasyon oluştur,
4. çağrı noktalarını buna yönlendir,
5. gereksiz eski yolu kaldır.

Geçici `thin wrapper` yalnız kontrollü geçiş için kullanılabilir.

---

## Eski Davranış

Eski kodun yaptığı her şeyi otomatik olarak koruma.

Hata, gereksiz davranış veya geçersiz varsayımı yeni sisteme taşıma.

Yalnız:

* doğrulanmış çalışan özellikleri,
* kullanıcı beklentisini,
* gerekli geriye uyumluluğu

koru.

---

## Değişiklik

Amaç en az satırı değiştirmek değil, temiz ve doğru çözüm bırakmaktır.

Görev gerektiriyorsa mevcut kod:

* değiştirilebilir,
* sadeleştirilebilir,
* kaldırılabilir.

Görev dışı refaktör yapma.

Karar mantığını MCP/Python teknik katmanına taşıma.

---

## Temel İlke

**Gerçek ihtiyacı anla → mevcut yapıyı doğrula → gerekli en küçük çözümü tasarla → tek temiz uygulama bırak.**

Projeyi kullanıcı ihtiyacına göre büyüt.

Gereksiz mimari oluşturma.
