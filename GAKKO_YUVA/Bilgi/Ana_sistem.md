# GAKKO — ANA SİSTEM

## 1. GAKKO'nun Amacı

GAKKO, yapay zekâ modelleriyle çalışan bir AI agent ve proje çalışma ortamıdır.

Temel amaç; anlama, muhakeme, kaynak seçimi, araştırma, araç kullanımı ve proje çalışmalarını yapay zekâya bırakırken teknik katmanı mümkün olduğunca sade tutmaktır.

Ana ilkeler:

- Kararları GAKKO AI verir.
- GAKKO_YUVA kalıcı bilgi, talimat ve çalışma kaynaklarını sağlar.
- Kod_Blok yalnızca uygulama, bağlantı, araç erişimi ve arayüz gibi teknik görevleri yürütür.

## 2. Yapay Zekâ Modelleri

GAKKO AI iki çalışma seviyesi kullanır.

### Normal

**Qwen3.6-35B-A3B UD-Q6_K_XL**

Sohbet, araştırma, genel çalışma, planlama ve normal teknik görevlerde kullanılır.

GAKKO'nun ana çalışma modelidir.

Bağlam: **64K (65536)**

### Yüksek

**Swift 1.5 / Qwen3.8-Flash-Next 125B IQ3_S**

Zor muhakeme, karmaşık analiz, kritik teknik doğrulama, yoğun kodlama ve derin değerlendirme içeren görevlerde kullanılır.

Görevi ve araç kullanımını baştan sona kendisi yürütür.

Bağlam: **128K (131072)**

## 3. Model Çalıştırma Altyapısı

GAKKO_R1 modellerini Strata üzerinden çalıştırır.

- Çalışma anında yalnızca 1 yapay zekâ modeli aktif tutulur.
- Model değiştirildiğinde mevcut Strata modeli tamamen kapatılır ve ardından seçilen model başlatılır.
- Normal model 64K (65536), Yüksek model 128K (131072) bağlam ile çalıştırılır.
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
- `Projeler` → Projeye özel kaynaklar

`QWEN.md` başlangıç kapısıdır.

`QWEN.md` üzerinden `GAKKO_YUVA/Talimatlar/Pusula.md` yönlendirmesine geçilir.

`Pusula.md`, gerekli kaynağın nerede olduğunu gösterir. Davranış ve çalışma kuralları ilgili kaynak dosyalarında bulunur.

## 5. Kod_Blok

`Kod_Blok`, GAKKO'nun teknik uygulama katmanıdır.

Başlıca sorumlulukları:

- GAKKO arayüzünü çalıştırmak
- Strata ve yapay zekâ modelleriyle bağlantı kurmak
- MCP ve diğer araç bağlantılarını sağlamak
- İnternet erişimini sağlamak
- Dosya ve proje erişimini sağlamak
- Sohbet geçmişini ve dosya eklerini yönetmek

## 6. Projeler ve Araçlar

GAKKO seçilen projede çalışır.

GAKKO AI:

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

Kaynak veya araç gerektirmeyen sohbetlerde model doğrudan cevap verebilir.

## 8. Ana Mimari İlke

GAKKO_YUVA, GAKKO AI'ye bilgi ve çalışma kaynaklarını sağlar.

Kod_Blok teknik bağlantı ve uygulama görevlerini yürütür.

Strata yapay zekâ modellerini çalıştırır.

MCP, yapay zekânın dosya sistemi ve teknik araçlara erişimini sağlar.

GAKKO AI tüm çalışmayı yürütür. Kod katmanı yalnızca GAKKO AI'nin kararlarını ve isteklerini teknik olarak uygular.