# Git Checkpoint Al

## Amaç

Test edilerek doğrulanmış mevcut çalışmayı, kullanıcı denetiminde güvenli biçimde Git kaydına almak.

Repository kökü aktif projenin doğrulanmış köküdür; kullanılacak branch `master`dır. Stage işleminden önce repository kökünü kullanıcıya göster. Kullanıcı açıkça istemedikçe branch değiştirme veya yeni branch oluşturma.

## Onay Kuralı

Stage, commit ve push birbirinden ayrı işlemlerdir. Her biri için işlemden hemen önce açık kullanıcı onayı al.

Kullanıcının `evet`, `onaylıyorum` veya `devam et` cevabı yalnız bekleyen işlem için geçerlidir; sonraki adıma peşin onay sayılmaz.

Kullanıcı dosyaları açıkça seçip bunlarla devam edilmesini isterse bu, yalnız belirtilen dosyalar için stage onayıdır. Kullanıcıdan commit mesajı isteme.

## İşlem Sırası

1. `git_status` ile branch, uzak dal durumu, staged, unstaged ve yeni dosyaları kontrol edip kullanıcıya göster.

2. Kayda girecek tam dosya listesini belirle. Kullanıcı dosyaları belirtmişse yalnız onları kullan; belirtmemişse ilgili dosyaları kendin seçip göster. Ardından `Bu dosyaları stage alanına eklememi onaylıyor musunuz?` diye sor.

3. Stage onayından sonra yalnız onaylanan dosyaları `git_add` ile ekle. Toplu veya ilgisiz dosya ekleme.

4. `git_diff_staged` ve `git_status` ile commit'e girecek tam dosya listesini doğrula. Kapsam onaylanan listeden farklıysa dur ve kullanıcıya göster.

5. Stage sonucunu ve değişikliklere göre kendin belirlediğin kısa commit mesajını göster. Ardından yalnızca `Commit almamı onaylıyor musunuz?` diye sor.

6. Commit onayından sonra `git_commit` kullan. `git_status` ve `git_log` ile sonucu doğrula; commit'i ve dışarıda kalan değişiklikleri kullanıcıya göster.

7. Commit başarılı olsa bile cevabı bitirme. Aynı cevap içinde tam olarak `Git push yapmamı onaylıyor musunuz?` diye sor.

8. Push onayından sonra GAKKO'nun özel `git_push` aracıyla aktif `master` branch'ini uzak depoya gönder. Sonucu göster ve `git_status` ile doğrula.

## Güvenlik

- Test edilmemiş veya kararsız çalışmayı commit etme.
- Onaylanmamış dosyayı stage ya da commit kapsamına alma.
- Açık onay olmadan değiştirici Git işlemi uygulama.
- `git_reset`, force push, branch değiştirme, branch oluşturma, merge veya rebase kullanma.
- Araç hata verirse gerçek hatayı göster; işlemi başarılı olmuş gibi bildirme.
- Push onayı verilmeden checkpoint akışını tamamlanmış sayma.
