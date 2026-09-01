# GAKKO — ANA SİSTEM

## 1. Yapay Zekâ Modeli
Qwen 3.8 27B
- Asıl yapay zekâ modelidir.
- Anlama, düşünme, karar verme ve cevap üretme gücünü sağlar.

## 2. Model Çalıştırma Servisi
Ollama
- Qwen 3.8 27B modelini bilgisayarda çalıştırır.
- Model ile donanım arasındaki çalışma altyapısını sağlar.

## 3. Çalışma ve Erişim Katmanı
Qwen Code
- Qwen modeline erişimi sağlar.
- Gakko çalışma akışının Qwen tarafında yürütülmesini sağlar.
- QWEN.md ve GAKKO_YUVA kaynak yapısının kullanılmasına aracılık eder.

## 4. Gakko
- Kullanıcı ile yapay zekâ arasındaki ana uygulamadır.
- Kullanıcı mesajını Qwen çalışma akışına ulaştırır.
- Qwen'in sonucunu kullanıcıya sunar.

## 5. GAKKO_YUVA
- Qwen'in kullandığı talimat, prensip, bilgi, hafıza ve proje kaynaklarının bulunduğu yapıdır.
- Bilgi gerektiğinde doğrudan ilgili kaynaklara gidilir.

## 6. Temel Çalışma Akışı

Gakko
↓
Qwen Code
↓
QWEN.md
↓
GAKKO.md
↓
Fihrist
↓
ilgili MD
↓
Qwen 3.8 27B
↓
karar / cevap
↓
Gakko