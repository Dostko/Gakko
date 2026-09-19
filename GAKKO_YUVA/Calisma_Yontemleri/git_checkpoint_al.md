# Git Checkpoint Al

## Amaç

GAKKO üzerinde yapılan ve test edilerek doğrulanan bir geliştirmeyi güvenli biçimde Git checkpoint olarak kaydetmek.

Bu çalışma yöntemi yalnız mevcut çalışmanın güvenli Git kaydını almak içindir.
Commit mesajını stage işleminden önce hazırlama veya kullanıcıya gösterme. Commit mesajı yalnız stage sonucu doğrulanıp kullanıcıya gösterildikten sonra hazırlanır.

## Repository Kökü

GAKKO ana Git repository kökü:

`D:\Gakko\`

Bu yöntemdeki tüm Git işlemleri bu repository kökünde çalıştırılır.

Git kaydı aktif `master` branch'i üzerinde alınır. Kullanıcı açıkça istemedikçe ayrı checkpoint branch'i oluşturma, branch değiştirme veya yeni branch oluşturma.

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

Onay beklerken kullanıcıdan komut, dosya listesi veya commit mesajı yazmasını isteme. Uygulanacak işlemi ve kapsamını kendin belirleyip göster, ardından kısa bir onay sorusu sor.

Kullanıcının `evet`, `onaylıyorum` veya `devam et` cevabı yalnız o anda bekleyen tek işlem için geçerlidir. Bu cevap sonraki Git adımlarına peşinen onay sayılmaz.

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

5. Mevcut çalışmayla ilgili olduğunu belirlediğin dosyaları kullanıcıya göster ve açıkça `Bu dosyaları stage alanına eklememi onaylıyor musunuz?` diye sor.
   Kullanıcıdan dosya adlarını yeniden yazmasını isteme.

6. Kullanıcı onay verdikten sonra yalnız belirtilen dosyaları `git_add` ile stage alanına ekle.
   İlgisiz dosyaları topluca ekleme.

7. `git_diff_staged` ve `git_status` ile stage edilen değişiklikleri doğrula.

8. Stage sonucunu kullanıcıya göster.
   Beklenmeyen veya ilgisiz bir dosya varsa commit işlemine geçme.

9. Stage edilen değişikliklere göre kısa ve uygun commit mesajını kendin belirle; kullanıcıdan commit mesajı isteme.
   Stage sonucunu ve belirlediğin commit mesajını gösterdikten sonra yalnızca `Commit almamı onaylıyor musunuz?` diye sor.

10. Kullanıcı onay verdikten sonra `git_commit` ile commit al.

11. Commit sonrasında `git_status` ve `git_log` ile sonucu doğrula.

12. Sonucu kullanıcıya göster:
    - oluşan commit,
    - son Git durumu,
    - varsa commit dışında kalan değişiklikler.

13. Çalışma ağacı beklenen durumdaysa checkpoint tamamlanmış kabul edilir.

14. Checkpoint tamamlandıktan sonra kullanıcıya tam olarak `Git push yapmamı onaylıyor musunuz?` diye sor.

15. Kullanıcı açıkça onay vermeden push işlemine geçme.

16. Kullanıcı açıkça onay verdikten sonra `git_push` ile aktif `master` branch'ini uzak depoya gönder ve sonucu doğrula.

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

Checkpoint tamamlandıktan sonra kullanıcıya `Git push yapmamı onaylıyor musunuz?` diye sor.

Kullanıcı açıkça onay vermeden push yapma.

Kullanıcı onay verirse `git_push` ile aktif `master` branch'ini uzak depoya gönder ve ardından `git_status` ile sonucu doğrula.

Mevcut Git MCP araçları push işlemi sunmuyorsa push yapılmış gibi davranma.

Kullanıcı push istediğinde mevcut araçlarla gerçekleştirilemiyorsa bunu açıkça belirt.

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
