# Proje ve Tasarım

## Yeni Proje

Kullanıcının seçtiği klasör aktif proje köküdür.

Projenin amacı ve başlangıç yapısı kullanıcı isteğine göre oluşturulur.

Kullanıcı belirtmeden:

- teknoloji,
- framework,
- mimari,
- bağımlılık,
- dosya yapısı,
- klasör yapısı

belirlenmez.

Projede bulunan içerik kullanıcı isteği olmadan değiştirilmez veya üzerine yazılmaz.

---

## Tasarım

Tasarım yalnız mevcut görevi çözen yapıyı içerir.

Görevde kullanılmayan:

- özellik,
- katman,
- yardımcı sistem,
- soyutlama,
- bağımlılık

eklenmez.

Gelecekte kullanılabileceği düşüncesi yeni yapı oluşturma nedeni değildir.

---

## Mevcut Yapıyla Uyum

Mevcut projede değişiklikten önce ilgili yapı ve gerçek çağrı yolları incelenir.

Çalışan davranış görev kapsamında korunur.

Aynı işi yapan iki kalıcı yapı paralel bırakılmaz.

Yapı yenilenirken:

1. hedef davranış belirlenir,
2. korunacak çalışan davranışlar belirlenir,
3. tek uygulama oluşturulur,
4. çağrı noktaları bu uygulamaya yönlendirilir,
5. eski yol kaldırılır.

Geçici `thin wrapper`, eski yapıdan yeni yapıya geçiş sırasında kullanılır.

---

## Eski Davranış

Eski kodun bütün davranışları yeni yapıya taşınmaz.

Hata, kullanılmayan davranış ve geçersiz varsayım korunmaz.

Korunanlar:

- doğrulanmış çalışan özellikler,
- kullanıcı tarafından belirlenmiş davranışlar,
- mevcut kullanımın devamı için gereken uyumluluk.

---

## Değişiklik

Amaç en az satırı değiştirmek değil, görev sonunda tek ve temiz çözüm bırakmaktır.

Mevcut kod görev kapsamında değiştirilir, sadeleştirilir veya kaldırılır.

Görev dışı refaktör yapılmaz.

Karar mantığı MCP/Python teknik katmanına taşınmaz.

---

## Temel İlke

**Görevi anla → mevcut yapıyı incele → çözümü tasarla → tek temiz uygulama bırak.**

Proje kullanıcı isteğine göre geliştirilir.

Görev dışında mimari oluşturulmaz.