# Git Checkpoint Al

## Amaç

Test edilmiş ve doğrulanmış mevcut çalışmayı güvenli biçimde Git checkpoint olarak kaydetmek.

Git depo kökü:

`D:\Gakko\`

## Kullanım

Kullanıcı açıkça Git kaydı, checkpoint veya commit istediğinde kullanılır.

Test edilmemiş veya kararsız çalışma commit edilmez.

## Kullanıcıya Görünür İlerleme

Git işlemlerini arka planda sessizce tamamlayıp yalnız sonucu bildirme.

Her önemli aşamada kullanıcıya ne bulunduğunu ve sırada ne yapılacağını kısa ve açık biçimde göster.

Git durumunu değiştiren işlemlerden önce kullanıcıdan açık onay al.

## Çalışma Sırası

1. `git_status` ile gerçek Git durumunu kontrol et.

2. Kullanıcıya şunları göster:
   - değişen dosyalar,
   - yeni dosyalar,
   - mevcut dal,
   - uzak dala göre durum.

3. Değişiklik kapsamını anlamak gerekiyorsa yalnız `git_diff_unstaged` kullan.

4. Bu aşamadan sonra değişen dosyaların içeriğini ayrıca okuma, başka kaynak arama veya ek inceleme yapma.

5. Hazırlama alanına eklenecek dosyaları kullanıcıya açıkça göster.

6. Burada dur ve hazırlama alanına ekleme için açık onay bekle.

7. Kullanıcı onay vermeden `git_add` çalıştırma.

8. Onaydan sonra yalnız belirtilen dosyaları `git_add` ile hazırlama alanına ekle.

9. `git_diff_staged` ve `git_status` ile hazırlanan değişiklikleri doğrula.

10. Kullanıcıya hazırlanan dosyaları ve kullanılacak commit mesajını göster.

11. Burada dur ve commit için ayrı açık onay bekle.

12. Kullanıcı commit onayı vermeden `git_commit` çalıştırma.

13. Onaydan sonra `git_commit` çalıştır.

14. Commit sonrasında `git_status` ve `git_log` ile sonucu doğrula.

15. Kullanıcıya şunları göster:
    - oluşan commit,
    - son Git durumu,
    - varsa commit dışında kalan değişiklikler.

## Temel Kurallar

- Kullanıcı istemeden otomatik checkpoint alma.
- Test veya doğrulama geçmeden commit alma.
- Kullanıcı onayı olmadan Git durumunu değiştiren işlem yapma.
- İlgisiz dosyaları hazırlama alanına veya commit içine alma.
- Kapsam tamamen doğrulanmadıkça toplu `git_add` kullanma.
- Hazırlama alanına ekleme ile commit için ayrı ayrı açık onay al.
- Kullanıcı istemedikçe `git_reset`, dal değiştirme veya dal oluşturma.
- Mevcut güvenli Git geçmişini bozacak işlem yapma.
- Hata veya belirsizlikte işlemi durdur ve gerçek Git durumunu kullanıcıya göster.
- Başarılı commit görülmeden işlemi tamamlanmış sayma.
- Git MCP'nin sunmadığı bir işlemi yapılmış gibi gösterme.

## Uzak Depoya Gönderme

Git MCP push aracı sunmuyorsa push yapma ve push yapabileceğini teklif etme.

Kullanıcı açıkça push isterse mevcut araçlarla gerçekleştirilemiyorsa bunu açıkça belirt.

## Başarı Ölçütü

Checkpoint tamamlandığında:

- yalnız ilgili ve doğrulanmış dosyalar commit edilmiş olmalı,
- commit başarıyla oluşmuş olmalı,
- son Git durumu doğrulanmış olmalı,
- kullanıcı hazırlama alanına ekleme ve commit işlemlerine ayrı ayrı onay vermiş olmalı,
- kullanıcı işlem boyunca uygulanan önemli Git adımlarını görmüş olmalıdır.

## Sınır

Bu çalışma yöntemi yalnız güvenli Git checkpoint almak içindir.

Dal yönetimi, geçmiş değiştirme, merge, rebase, reset, depo temizliği veya başka ileri Git işlemleri bu yöntemin kapsamında değildir.