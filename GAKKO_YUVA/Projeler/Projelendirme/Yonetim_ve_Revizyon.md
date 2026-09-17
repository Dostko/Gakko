# Yönetim ve Revizyon

## Kullanıcı Onayı

Kullanıcının açık onayı olmadan:

* dosya oluşturma,
* dosya değiştirme,
* dosya silme,
* taşıma,
* yeniden adlandırma,
* yeni yapı oluşturma

işlemi yapma.

Kullanıcının açıkça verdiği işlem emri, yalnız belirtilen hedef ve kapsam için onaydır.

Görev dışında ek değişiklik gerekiyorsa önce açıkla ve onay al.

---

## Değişiklik Öncesi

Mevcut bir dosyayı değiştirmeden önce gerekli mevcut içeriği incele.

Görmediğin dosyanın üzerine yazma.

Değişiklikten önce:

* ilgili çağrı yollarını,
* bağımlılıkları,
* korunması gereken çalışan davranışları

gerektiği kadar doğrula.

---

## Değişiklik

Amaç en az satırı değiştirmek değil, doğru ve temiz sonucu bırakmaktır.

Görev gerektiriyorsa mevcut kod:

* değiştirilebilir,
* sadeleştirilebilir,
* kaldırılabilir.

Görev dışı dosyalara veya davranışlara dokunma.

Eski ve yeni aynı işi yapan iki kalıcı yolu paralel bırakma.

---

## Eski Davranışı Koruma

Eski davranışı otomatik olarak doğru kabul etme.

Hata, gereksiz davranış veya geçersiz varsayımı yeni yapıya taşıma.

Yalnız:

* doğrulanmış çalışan özellikleri,
* kullanıcı beklentisini,
* gerekli geriye uyumluluğu

koru.

---

## Doğrulama

Değişiklik sonrası gerçekten uygulandığını kontrol et.

Doğrula:

* hedef dosya doğru mu,
* yeni davranış çalışıyor mu,
* mevcut davranışlardan biri bozuldu mu,
* gereksiz eski yol kaldırıldı mı,
* çağrı noktaları doğru yere gidiyor mu,
* ilgili testler geçiyor mu.

`git diff` yalnız yardımcı kontroldür; başarı ölçütünün kendisi değildir.

Bir işlem başarısızsa başarılı olmuş gibi gösterme.

---

## Revizyon

Yeni ihtiyaç çıktığında mevcut yapıyı kontrollü biçimde revize et.

Yeni çözümü eski yapının üzerine yığma.

Gerekirse eski çözümü kaldır ve tek temiz yol bırak.

Revizyonun kapsamını kullanıcı göreviyle sınırlı tut.

---

## Temel İlke

**İncele → onay sınırını koru → değiştir → doğrula → gereksiz eski yolu kaldır.**

Çalışan yapıyı koru, fakat hatalı veya gereksiz davranışı sırf eski diye yaşatma.
