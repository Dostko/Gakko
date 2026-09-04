name: gakko_kurulus_gunu
description: GAKKO projesinin DOSTKO'dan doğduğu, sıfırdan kurulduğu gün
---

31 Ağustos 2026, GAKKO doğdu.

Daha önce DOSTKO adıyla aylarca çalışılmış, PySide ile GUI'den başlanmış,
sonra "bu aslında yapay zeka değil, kod bağlamlı bir program" fark edilmiş.
Qwen + Ollama'ya geçilmiş, ama mimari zamanla karmaşıklaşmış, iki farklı
fihrist erişim yöntemi (kod-tabanlı tool'lar ve Qwen Code CLI) yan yana
durur hale gelmiş.

Bugün baştan başlandı. İsim GAKKO oldu. D:\Gakko\ kuruldu.

GAKKO_YUVA sıfırdan inşa edildi: 6 prensip dosyası, 2 fihrist, 2 skill.
Zincir sistemi (fihristten fihriste, en fazla 5 kayıt, eşleşme yoksa
bir sonrakine geç) test edildi ve çalıştığı kanıtlandı — Qwen Code,
hiç yanılmadan doğru dosyaları sırayla okudu.

Qwen3.8-27B modeline geçildi, sonra flash attention ve KV cache
sıkıştırmasıyla 64K context'te %100 GPU'da taşmadan çalışır hale
getirildi. DeepSeek, gpt-oss gibi alternatifler test edildi, elendi.
qwen3-vl:8b, görsel/OCR işleri için ayrı tutuldu.

En büyük kırılma en sona geldi: Qwen Code CLI'nin kendisi
(daemon modu, onay bekleme, grammar hataları) çok fazla soruna yol
açınca, tamamen kaldırıldı. Yerine basit, doğrudan bir köprü yazıldı —
"AI ister, kod getirir, AI karar verir." Sonuç: 5-20 dakika süren
yanıtlar 20-40 saniyeye düştü.

Gün, dört bölümlü bir GUI ile bitti: Sohbet, Geçmiş, Dosya, Proje.
GAKKO artık geçmiş konuşmaları hatırlıyor, hangi git kaydının ilk
olduğunu biliyor, kendi context tüketimini gösteriyor.

Bu, GAKKO'nun ilk gerçek Bellek kaydı. Kütüphane artık boş değil.