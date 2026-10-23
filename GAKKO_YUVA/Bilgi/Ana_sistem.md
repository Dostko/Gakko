# GAKKO — ANA SİSTEM

## 1. GAKKO'nun Amacı

GAKKO, yapay zekâ modelleriyle çalışan bir AI agent ve proje çalışma ortamıdır.

Temel amaç; anlama, muhakeme, kaynak seçimi, araştırma, araç kullanımı ve proje çalışmalarını yapay zekâya bırakırken teknik katmanı mümkün olduğunca sade tutmaktır.

Ana ilke:

- Kararları GAKKO AI verir.
- GAKKO_YUVA kalıcı bilgi, talimat ve çalışma kaynaklarını sağlar.
- Kod_Blok yalnızca uygulama, bağlantı, araç erişimi ve arayüz gibi teknik görevleri yürütür.

## 2. Yapay Zekâ Modelleri

GAKKO AI iki çalışma seviyesi kullanır.

### Normal

**Swift 1.5 / Qwen3.8-Flash-Next 125B IQ2_XS**

Sohbet, araştırma, genel çalışma, planlama ve normal teknik görevlerde kullanılır.

Hızlı ana çalışma modelidir.

### Yüksek

**Swift 1.5 / Qwen3.8-Flash-Next 125B IQ3_S**

Zor muhakeme, karmaşık analiz, kritik teknik doğrulama, yoğun kodlama ve derin değerlendirme içeren görevlerde kullanılır.

Görevi ve araç kullanımını baştan sona kendisi yürütür.

## 3. Model Çalıştırma Altyapısı

GAKKO_R1 modellerini Strata üzerinden çalıştırır.

- Çalışma anında sadece 1 yapay zekâ modeli aktif tutulur.
- Model değiştirildiğinde mevcut Strata modeli kapatıldıktan sonra seçilen model başlatılır.
- Modeller 128K bağlam ile çalıştırılır.
- GAKKO ile Strata arasındaki bağlantı API üzerinden sağlanır.

## 4. GAKKO_YUVA

`GAKKO_YUVA`, GAKKO'nun kalıcı kaynak merkezidir.

Ana alanlar:

- `Talimatlar` → Kaynak yönlendirmesi
- `Prensipler` → Davranış ve karar ilkeleri
- `Calisma_Yontemleri` → Belirtilen görevlerin nasıl yürütüleceği
- `Bilgi` → Doğrulanmış sistem ve teknik bilgiler
- `Hafiza` → Yakın geçmiş ve çalışma bağlamı
- `Kayitlar` → Kalıcı kayıtlar
- `Projeler` → Proje özel kaynakları

`QWEN.md` başlangıç kapısıdır.

`QWEN.md`'den `GAKKO_YUVA/Talimatlar/Pusula.md` yönlendirmesine geçilir.

`Pusula.md` kaynağın nerede olduğunu gösterir. Davranış ve çalışma kuralları ilgili kaynak dosyalarında bulunur.

## 5. Kod_Blok

`Kod_Blok`, GAKKO'nun teknik uygulama katmanıdır.

Başlıca sorumlulukları:

- GAKKO arayüzünü çalıştırmak
- Strata ve yapay zekâ modelleriyle bağlantı kurmak
- MCP ve diğer araç bağlantılarını sağlamak
- internet erişimini sağlamak
- dosya ve proje erişimini sağlamak
- sohbet geçmişi ve dosya eklerini yönetmek

## 6. Projeler ve Araçlar

GAKKO seçilen projede çalışır.

- proje yapısını inceleyebilir,
- dosya ve içerik arayabilir,
- ilgili kaynakları okuyabilir,
- izin verilen araçları kullanabilir,
- kullanıcı onayına bağlı işlemlerde ilgili prensipleri uygular.

Dosya ve proje erişimi MCP üzerinden sağlanır.

Araç kullanımının nasıl yapılacağı `Prensipler` ve `Calisma_Yontemleri` kaynaklarında tanımlanır.

## 7. Ana Çalışma Zinciri

Kullanıcı  
↓  
GAKKO AI (Normal veya Yüksek Model)  
↓  
QWEN.md  
↓  
Pusula.md  
↓  
Kaynak veya Araç  
↓  
GAKKO AI Değerlendirmesi  
↓  
Kullanıcı

Sohbet için model doğrudan cevap verebilir.

## 8. Ana Mimari İlke

GAKKO_YUVA, GAKKO AI'ye bilgi ve çalışma kaynaklarını sağlar.

Kod_Blok teknik bağlantı ve uygulama görevlerini yürütür.

Strata yapay zekâ modellerini çalıştırır.

MCP, yapay zekânın dosya sistemi ve teknik araçlara erişimini sağlar.

GAKKO AI tüm çalışmayı yürütür. Kodlar ise yalnızca GAKKO AI'nin kararlarını ve isteklerini teknik olarak uygular.