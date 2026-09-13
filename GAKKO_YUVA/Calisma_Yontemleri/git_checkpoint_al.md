# Git Checkpoint Al

## Amaç

GAKKO üzerinde yapılan ve test edilerek doğrulanan bir geliştirmeyi güvenli biçimde Git checkpoint olarak kaydetmek.

Bu çalışma yöntemi yalnız mevcut çalışmanın güvenli Git kaydını almak içindir.

## Repository Kökü

GAKKO ana Git repository kökü:

`D:\Gakko\`

Bu yöntemdeki tüm Git işlemleri bu repository kökünde çalıştırılır.

Kullanıcı kayda alınacak dosyaları açıkça belirttiyse yalnız bu dosyalar işleme alınır.

Dosyalar açıkça belirtilmediyse `git_status` ile değişen dosyalar kontrol edilir ve yalnız mevcut çalışmayla ilgili olanlar seçilir.

---

## Ne Zaman Kullanılır?

Kullanıcı açıkça Git kaydı, checkpoint, commit veya güvenli kayıt alınmasını istediğinde kullanılır.

Bir geliştirme henüz test edilmediyse veya sonuç kararlı değilse checkpoint alınmaz.

---

## Kullanıcıya Görünür İlerleme

Git checkpoint işlemlerini arka planda sessizce tamamlayıp yalnız sonuç bildirme.

Her önemli aşamada kullanıcıya ne bulunduğunu, sırada ne yapılacağını ve hangi dosyaların işleme alınacağını kısa ve açık biçimde göster.

Dosya ekleme, commit alma veya Git durumunu değiştiren başka bir işlemden önce kullanıcıya uygulanacak işlemi göster ve açık onay al.

Kullanıcı onay vermeden değiştirici Git işlemi uygulama.

Salt okuma işlemleriyle mevcut durumu inceleyebilir ve sonucu kullanıcıya gösterebilirsin.

---

## Çalışma Sırası

1. `git_status` ile gerçek Git durumunu kontrol et.

2. Sonucu kullanıcıya göster:
   - değişen dosyalar,
   - yeni dosyalar,
   - mevcut branch,
   - uzak dala göre mevcut durum.

3. Yalnız mevcut çalışmayla ilgili dosyaları belirle.

4. Yapılan değişikliğin gerekli test ve doğrulamalarının geçtiğinden emin ol.

5. Kullanıcıya hangi dosyaların stage alanına ekleneceğini açıkça göster ve onay iste.

6. Kullanıcı onay verdikten sonra yalnız belirtilen dosyaları `git_add` ile stage alanına ekle.
   İlgisiz dosyaları topluca ekleme.

7. `git_diff_staged` ve `git_status` ile stage edilen değişiklikleri doğrula.

8. Stage sonucunu kullanıcıya göster.
   Beklenmeyen veya ilgisiz bir dosya varsa commit işlemine geçme.

9. Kullanıcıya kullanılacak kısa ve açık commit mesajını göster ve commit için açık onay iste.

10. Kullanıcı onay verdikten sonra `git_commit` ile commit al.

11. Commit sonrasında `git_status` ve `git_log` ile sonucu doğrula.

12. Sonucu kullanıcıya göster:
    - oluşan commit,
    - son Git durumu,
    - varsa commit dışında kalan değişiklikler.

13. Çalışma ağacı beklenen durumdaysa checkpoint tamamlanmış kabul edilir.

---

## Temel Kurallar

- Kullanıcı istemeden otomatik checkpoint alma.
- Test veya doğrulama geçmeden commit alma.
- İlgisiz dosyaları aynı commit içine katma.
- Kapsam tamamen doğrulanmadıkça toplu stage yapma.
- Mevcut güvenli geçmişi bozacak işlemler yapma.
- Kullanıcı açıkça istemedikçe `git_reset`, branch değiştirme, branch oluşturma veya benzeri Git durumunu değiştiren işlemleri kullanma.
- Değiştirici Git işlemlerinden önce kullanıcıya ne yapılacağını göster ve açık onay al.
- Hata veya belirsizlik varsa işlemi durdur ve gerçek Git durumunu göster.
- Başarılı commit sonucunu görmeden işlemi tamamlanmış sayma.
- Git MCP'nin sunmadığı bir işlemi yapılmış gibi gösterme.

---

## Push

Mevcut Git MCP araçları push işlemi sunmuyorsa push yapılmış gibi davranma.

Kullanıcı uzak depoya push isterse mevcut araçlarla bunun gerçekleştirilemediğini açıkça belirt.

---

## Başarı Ölçütü

Checkpoint tamamlandığında:

- yalnız ilgili ve doğrulanmış dosyalar kayda girmiş olmalı,
- commit başarıyla oluşmuş olmalı,
- son `git_status` çıktısında beklenmeyen değişiklik bulunmamalı,
- kullanıcı işlem boyunca hangi dosyaların ve hangi Git adımlarının uygulandığını görmüş olmalıdır.

---

## Sınır

Bu çalışma yöntemi Git checkpoint almak içindir.

Branch yönetimi, geçmiş değiştirme, merge, rebase, repository temizliği veya başka ileri Git işlemleri bu yöntemin kapsamında değildir.
