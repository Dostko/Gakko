# GAKKO — Yapılacaklar

Bu dosya yalnızca henüz tamamlanmamış güncel işleri içerir.

Bir iş tamamlandığında bu listeden kaldırılır ve gerekiyorsa `Guncel_Durum.md` içine yansıtılır.


## 1. Bilgi Kaynaklarını Tamamlama

- `Ana_sistem.md` içindeki QWEN.md konumunu gerçek proje yapısıyla doğrulamak ve gerekiyorsa düzeltmek.
- Yeni oluşturulan Bilgi kaynakları tamamlandıktan sonra `Bilgi_Fihristi.md` dosyasını tek seferde güncellemek.
- Fihriste yalnız yaşayan ve güncel kaynakları eklemek.


## 2. GAKKO Performansı

- İlk model çağrısındaki yüksek gecikmenin nedenini incelemek.
- Qwen'in basit proje görevlerinde yaptığı gereksiz araç turlarını azaltmak.
- Aktif proje kökü biliniyorken gereksiz dosya yolu tahmini ve klasör keşfini azaltmak.
- Ripgrep `search` aracının Qwen'e sunulan gerçek şemasını incelemek.
- Proje kökü ve dosya filtrelerinin Ripgrep ile daha doğrudan kullanılmasını doğrulamak.
- Prompt cache kullanımını doğrudan ölçebilecek metriği değerlendirmek.


## 3. Proje ve Dosya Çalışmaları

- Dosya arama → okuma → düzenleme akışlarının mümkün olduğunca az araç turuyla çalışmasını sağlamak.
- Büyük dosyaların gereksiz yere tamamen bağlama alınmasını önlemek.
- MCP tabanlı dosya erişiminde eski veya paralel özel yollar kalmadığını doğrulamak.


## 4. Dosya_Yon Projesi

GAKKO performans çalışmaları tamamlandıktan sonra:

- İşlem geçmişi oluşturmak.
- Taşınan dosyaların kaynak ve hedef konumlarını kaydetmek.
- Güvenli `Geri Al` işlevi eklemek.
- Geri alma sırasında kaynak konum doluysa işlemi güvenli şekilde durdurmak.
- Mevcut çalışan dosya düzenleme davranışlarını regresyon açısından doğrulamak.


## 5. Arayüz Rötuşları

Ana sistem çalışmaları tamamlandıktan sonra gerekli görülürse:

- Sohbet cevap alanının kullanılabilir genişliğini iyileştirmek.
- Sağ kaydırma çubuğunun konumunu ve görünümünü düzenlemek.
- Uzun süren Qwen yanıtını güvenli şekilde durdurabilen `Durdur` işlevini tamamlamak.


## Öncelik

Şu anki çalışma sırası:

**Bilgi kaynakları ve fihrist → GAKKO performansı → proje/dosya akışı → Dosya_Yon → arayüz rötuşları**