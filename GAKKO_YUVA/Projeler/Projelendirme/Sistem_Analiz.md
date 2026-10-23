# Sistem Analizi

## Başlangıç

Mevcut projede değişiklikten önce ilgili yapı incelenir.

Kullanıcının verdiği başlangıç dosyası önce okunur.

Başlangıç noktası verilmemişse proje yapısından görevle ilişkili dosya veya bölüm bulunur. Dosya adı tahmin edilmez.

---

## Gerçek Yapıyı Doğrulama

Görülmeyen veya doğrulanmayan:

- dosya,
- klasör,
- sınıf,
- fonksiyon,
- araç,
- bağlantı,
- davranış

varmış gibi kabul edilmez.

Görevle ilişkili çağrı noktaları, bağımlılıklar ve dosyalar incelenir.

Tüm proje çalışma bağlamına yüklenmez.

---

## Kök Nedeni Bulma

Sorun yalnız görünen belirti üzerinden çözülmez.

Analizde:

1. sorunun başladığı nokta,
2. çağrı yolu,
3. sorunu oluşturan koşul,
4. etkilenen bileşenler

belirlenir.

Düzeltme kök nedene uygulanır. Geçici yama, gerçek nedenin yerine kullanılmaz.

---

## API ve Framework Doğruluğu

API, framework, sınıf, metot ve parametre bilgileri güncel resmî dokümantasyondan doğrulanır.

Framework sınıfı kullanım amacına göre seçilir.

Pseudo-code ile çalışabilir kod açıkça ayrılır.

Doğrulanmamış kod çalışır kod olarak sunulmaz.