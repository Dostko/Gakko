# Git Checkpoint Al

## Amaç

Test edilmiş ve doğrulanmış mevcut çalışmayı güvenli biçimde Git checkpoint olarak kaydetmek.

Repository kökü:

`D:\Gakko\`

## Kullanım

Kullanıcı açıkça Git kaydı, checkpoint veya commit istediğinde kullanılır.

Test edilmemiş veya kararsız çalışma commit edilmez.

## Çalışma Sırası

1. `git_status` ile mevcut Git durumunu kontrol et.

2. Değişen dosyaları, branch durumunu ve varsa yeni dosyaları kullanıcıya göster.

3. Gerekirse yalnız değişiklik kapsamını görmek için `git_diff_unstaged` kullan.

4. Bu aşamadan sonra dosya içeriklerini ayrıca okuma, başka kaynak arama veya ek inceleme yapma.

5. Stage edilecek dosyaları kullanıcıya göster ve açık onay bekle.

6. Onaydan sonra yalnız belirtilen dosyaları `git_add` ile stage et.

7. `git_diff_staged` ve `git_status` ile stage sonucunu doğrula ve kullanıcıya göster.

8. Commit mesajını kullanıcıya göster ve commit için açık onay iste.

9. Onaydan sonra `git_commit` çalıştır.

10. `git_status` ve `git_log` ile sonucu doğrula ve kullanıcıya göster.

## Temel Kurallar

- Kullanıcı onayı olmadan Git durumunu değiştiren işlem yapma.
- İlgisiz dosyaları stage veya commit etme.
- Toplu stage kullanma.
- Kullanıcı istemedikçe `git_reset`, branch değiştirme veya branch oluşturma.
- Hata veya belirsizlikte işlemi durdur ve gerçek Git durumunu göster.
- Başarılı commit görülmeden işlemi tamamlanmış sayma.
- Git MCP'nin sunmadığı işlemi yapılmış gibi gösterme.

## Push

Git MCP push sunmuyorsa push yapılmış gibi davranma.

Kullanıcı push isterse mevcut araçlarla yapılamadığını açıkça belirt.

## Başarı Ölçütü

Checkpoint tamamlandığında:

- yalnız ilgili dosyalar commit edilmiş olmalı,
- commit başarıyla oluşmuş olmalı,
- son Git durumu doğrulanmış olmalı,
- kullanıcı yapılan adımları görmüş olmalı.