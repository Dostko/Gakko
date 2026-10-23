# Yönetim ve Revizyon

## Kullanıcı Onayı

Kullanıcının açık onayı olmadan:

- dosya oluşturulmaz,
- dosya değiştirilmez,
- dosya silinmez,
- dosya taşınmaz,
- dosya yeniden adlandırılmaz,
- yeni yapı oluşturulmaz.

Kullanıcının verdiği işlem emri yalnız belirtilen hedef ve kapsam için geçerlidir.

Görev dışındaki değişiklikler kullanıcıya açıklanır ve ayrı onay alınır.

---

## Değişiklik Öncesi

Değiştirilecek dosya önce incelenir.

Görülmeyen dosyanın üzerine yazılmaz.

Değişiklikten önce:

- ilgili çağrı yolları,
- bağımlılıklar,
- korunacak çalışan davranışlar

kontrol edilir.

---

## Değişiklik

Amaç en az satırı değiştirmek değil, görev sonunda doğru ve temiz yapıyı bırakmaktır.

Mevcut kod görev kapsamında değiştirilir, sadeleştirilir veya kaldırılır.

Görev dışındaki dosya ve davranışlara dokunulmaz.

Aynı işi yapan eski ve yeni iki kalıcı yol paralel bırakılmaz.

---

## Eski Davranış

Eski davranış yalnız eski olduğu için korunmaz.

Hata, kullanılmayan davranış ve geçersiz varsayım yeni yapıya taşınmaz.

Korunanlar:

- doğrulanmış çalışan özellikler,
- kullanıcı tarafından belirlenmiş davranışlar,
- mevcut kullanımın devamı için gereken uyumluluk.

---

## Doğrulama

Değişiklikten sonra sonuç kontrol edilir:

- doğru dosya değişti mi,
- hedef davranış çalışıyor mu,
- çalışan davranışlardan biri bozuldu mu,
- eski yol kaldırıldı mı,
- çağrı noktaları doğru yere gidiyor mu,
- ilgili testler geçiyor mu.

`git diff` yardımcı kontroldür; tek başına başarı ölçütü değildir.

Başarısız işlem başarılı olarak gösterilmez.

---

## Revizyon

Revizyon mevcut yapının üzerine yeni katman yığmak için kullanılmaz.

Eski çözüm kaldırılır ve görev sonunda tek temiz yol bırakılır.

Revizyon kapsamı kullanıcı göreviyle sınırlıdır.

---

## Temel İlke

**İncele → onay al → değiştir → doğrula → eski yolu kaldır.**

Çalışan yapı korunur. Hatalı veya kullanılmayan davranış yalnız eski olduğu için yaşatılmaz.