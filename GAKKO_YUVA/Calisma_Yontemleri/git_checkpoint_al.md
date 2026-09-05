# Git Checkpoint Al

## Amaç

GAKKO üzerinde yapılan ve test edilerek doğrulanan bir geliştirmeyi güvenli biçimde Git checkpoint olarak kaydetmek.

Bu çalışma yöntemi yalnız mevcut çalışmanın güvenli Git kaydını almak içindir.

---

## Ne Zaman Kullanılır?

Kullanıcı açıkça Git kaydı, checkpoint, commit veya güvenli kayıt alınmasını istediğinde kullanılır.

Bir geliştirme henüz test edilmediyse veya sonuç kararlı değilse checkpoint alınmaz.

---

## Çalışma Sırası

1. Git durumunu kontrol et.

   ```powershell
   git status -sb
   ```

2. Yalnız mevcut çalışmayla ilgili değişen dosyaları belirle.

3. Yapılan değişikliğin gerekli test ve doğrulamalarının geçtiğinden emin ol.

4. Sadece bu çalışmaya ait dosyaları stage alanına ekle.

   İlgisiz dosyaları topluca ekleme.

5. Stage edilen değişiklikleri doğrula.

   ```powershell
   git diff --cached --check
   git status -sb
   ```

6. Beklenmeyen veya ilgisiz bir dosya varsa commit işlemine geçme.

7. Değişikliğin amacını anlatan kısa ve açık bir commit mesajı kullan.

8. Commit al.

9. Kullanıcı GitHub/uzak depo kaydı istiyorsa push yap.

10. Son durumu tekrar doğrula.

   ```powershell
   git status -sb
   ```

11. Çalışma ağacı temizse ve yerel dal uzak dal ile uyumluysa checkpoint tamamlanmış kabul edilir.

---

## Temel Kurallar

- Kullanıcı istemeden otomatik checkpoint alma.
- Test veya doğrulama geçmeden commit alma.
- İlgisiz dosyaları aynı commit içine katma.
- `git add .` veya benzeri toplu ekleme yöntemlerini, kapsam tamamen doğrulanmadıkça kullanma.
- Mevcut güvenli geçmişi bozacak işlemler yapma.
- Kullanıcı açıkça istemedikçe `reset`, `rebase`, `amend`, `clean`, force push veya geçmiş değiştiren işlemler kullanma.
- Hata veya belirsizlik varsa işlemi durdur ve gerçek Git durumunu göster.
- Başarılı commit veya push sonucunu görmeden işlemi tamamlanmış sayma.

---

## Başarı Ölçütü

Checkpoint tamamlandığında:

- yalnız ilgili ve doğrulanmış dosyalar kayda girmiş olmalı,
- commit başarıyla oluşmuş olmalı,
- istenmişse push başarıyla tamamlanmış olmalı,
- son `git status -sb` çıktısında beklenmeyen değişiklik bulunmamalıdır.

---

## Sınır

Bu çalışma yöntemi Git checkpoint almak içindir.

Branch yönetimi, geçmiş değiştirme, merge, rebase, reset, repository temizliği veya başka ileri Git işlemleri bu yöntemin kapsamında değildir.