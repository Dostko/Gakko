# GAKKO — ANA SİSTEM

## 1. Yapay Zekâ Modelleri

### Ana Model

**gakko-qwen38-64k-gpu:latest**

- GAKKO'nun asıl yapay zekâ modelidir.
- Qwen 3.8 27B tabanlıdır.
- 64K context ile çalışır.
- Anlama, düşünme, karar verme ve cevap üretme görevlerini yürütür.
- GAKKO'nun ana karar merkezi bu modeldir.

### Yardımcı Görsel Model

**qwen3-vl:8b**

- GAKKO'nun görsel işlemler için kullandığı yardımcı yapay zekâ modelidir.
- Resim ve ekran görüntülerini incelemek için kullanılır.
- OCR ile görsellerdeki yazıların okunmasına yardımcı olur.
- Görsel içeriklerin tanınması ve açıklanmasını sağlar.
- Video işlemlerinde gerekli görsel/kare analizlerinde yardımcı model olarak kullanılabilir.
- Nihai karar ve cevap üretimi ana Qwen modeli tarafından yapılır.

## 2. Model Çalıştırma Servisi

**Ollama**

- GAKKO'nun yerel yapay zekâ modellerini bilgisayarda çalıştırır.
- Ana model `gakko-qwen38-64k-gpu:latest` ve yardımcı görsel model `qwen3-vl:8b` Ollama üzerinden çalışır.
- Modeller ile bilgisayar donanımı arasındaki çalışma altyapısını sağlar.

## 3. Çalışma ve Erişim Katmanı

- GAKKO ile yerel Qwen modeli arasındaki mümkün olan en sade teknik köprüdür.
- Kullanıcı mesajını doğrudan Qwen'e ulaştırır.
- Qwen'in sistemin ana giriş noktası olan `QWEN.md` üzerinden GAKKO_YUVA yapısına erişebilmesini sağlar.
- Qwen hangi dosyaya veya kaynağa ihtiyaç duyacağını kendisi belirler.
- Python dosya seçmez, fihrist takip etmez, belge içeriğini yorumlamaz ve karar vermez.
- Python, Qwen'in istediği dosyanın içeriğini diskten teknik olarak okur ve Qwen'e taşır.
- Bu teknik okuma yalnızca içeriğin modele ulaştırılması içindir; Python içerikten anlam çıkarmaz, filtreleme yapmaz veya karar üretmez.
- Dosyalarda değişiklik yapmaz ve içerik hakkında kendi adına işlem veya değerlendirme yapmaz.
- Kaynaktan alınan içerik tekrar Qwen'e verilir; değerlendirme, yorumlama, karar ve cevap tamamen Qwen tarafından üretilir.

## 4. Gakko

- Kullanıcı ile ana Qwen modeli arasındaki ana uygulamadır.
- Kullanıcı mesajlarını Qwen'e ulaştırır.
- Qwen'in ürettiği cevapları kullanıcıya sunar.
- Sohbet, dosya, geçmiş ve diğer kullanıcı arayüzü işlevlerini sağlar.
- Karar verme, kaynak seçme ve içerik yorumlama görevlerini üstlenmez.
- Yapay zekâ kararları Qwen tarafından verilir.

## 5. GAKKO_YUVA

- GAKKO_YUVA, Qwen'in ana çalışma ve karar evidir.
- Talimatlar, Prensipler, Calisma_Yontemleri, Bilgi ve Bellek kaynaklarını barındırır.
- Qwen bu yapı içinde ihtiyaç duyduğu kaynağı kendisi seçer, okur, yorumlar ve karar verir.
- Fihristler, Qwen'in doğru kaynağa ulaşmasını sağlayan yönlendirme noktalarıdır.
- GAKKO_YUVA kendi başına karar veren bir sistem değildir; karar veren Qwen'dir.
- GAKKO_YUVA, Qwen'in karar verirken dayandığı düzenli ve kalıcı ana kaynak merkezidir.

## 6. Temel Çalışma Akışı

Kullanıcı

↓

Gakko

↓

Ana Qwen modeli

↓

QWEN.md

↓

GAKKO.md

↓

GAKKO_FIHRIST_1.md

↓

gerekirse GAKKO_FIHRIST_2.md

↓

ilgili kaynak

↓

Qwen okur, yorumlar ve karar verir

↓

cevap

↓

Gakko

↓

Kullanıcı

### Dosya Erişimi Gerektiğinde

Qwen dosyayı ister

↓

Python dosyayı teknik olarak açar ve içeriği taşır

↓

içerik Qwen'e geri verilir

↓

Qwen içeriği okur, yorumlar ve karar vermeye devam eder