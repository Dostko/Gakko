# Git Checkpoint Al

## Ne Zaman Kullanılır

Kullanıcı:

- `/git`
- `git kaydı alalım`
- `git checkpoint alalım`
- `checkpoint alalım`
- `kayıt alalım`

ifadelerinden biriyle mevcut çalışmanın Git kaydını istediğinde bu yöntem uygulanır.

Git checkpoint işlemi aşağıdaki sırayla yürütülür. Bir adım tamamlanmadan sonraki adıma geçilmez.

## İşlem Sırası

### 1. Repository Kontrolü

Seçilen projenin repository kökünü doğrula ve sohbet ekranında kullanıcıya göster.

`git_status` ile:

- branch,
- staged dosyalar,
- unstaged dosyalar,
- yeni dosyalar,
- uzak depo durumu

kontrol edilir ve sohbet ekranında kullanıcıya gösterilir.

Kullanılacak branch `master`dır.

Branch değiştirme veya yeni branch oluşturma.

### 2. Stage Kapsamı

Checkpoint'e girecek dosyaları belirle ve tam listeyi sohbet ekranında kullanıcıya göster.

Ardından:

`Bu dosyaları stage alanına eklememi onaylıyor musunuz?`

diye sor.

Kullanıcı onay sırasında dosya ekleyebilir veya çıkarabilir.

Kullanıcının cevabını bekle.

### 3. Stage

Stage onayından sonra onaylanan dosyaları `git_add` ile ekle.

`git_diff_staged` ve `git_status` ile sonucu doğrula.

Stage alanına eklenen dosyaları sohbet ekranında kullanıcıya göster.

Onaylanan liste ile stage kapsamı farklıysa dur ve farkı kullanıcıya göster.

### 4. Commit Hazırlığı

Stage alanındaki dosyaları sohbet ekranında kullanıcıya göster.

Değişiklikleri açıklayan kısa commit mesajını oluştur ve sohbet ekranında kullanıcıya göster.

Kullanıcıdan commit mesajı isteme.

Ardından:

`Commit almamı onaylıyor musunuz?`

diye sor.

Kullanıcının cevabını bekle.

### 5. Commit

Commit onayından sonra `git_commit` kullan.

`git_status` ve `git_log` ile commit sonucunu doğrula.

Oluşan commit'i ve checkpoint dışında kalan değişiklikleri sohbet ekranında kullanıcıya göster.

### 6. Push Onayı

Commit tamamlandıktan sonra işlemi bitirme.

Aynı cevap içinde:

`Git push yapmamı onaylıyor musunuz?`

diye sor.

Kullanıcının cevabını bekle.

### 7. Push

Push onayından sonra GAKKO'nun `git_push` aracıyla `master` branch'ini uzak depoya gönder.

Push sonucunu sohbet ekranında kullanıcıya göster.

Commit önceki adımda doğrulandıysa push aşamasında commit doğrulamasını yeniden başlatma.

### 8. Son Kontrol

`git_status` ile repository ve çalışma ağacının son durumunu kontrol et.

Son durumu sohbet ekranında kullanıcıya göster.

Push başarılıysa checkpoint işleminin tamamlandığını kullanıcıya bildir.

## Doğrulama Sınırı

Checkpoint sırasında yalnız değişen dosyalar, ilgili diff ve checkpoint işlemi için gerekli doğrulamalar incelenir.

Doğrulanmamış bir değişiklik görülürse yalnız o değişikliğin doğrudan çalışma yolu kontrol edilir.

Checkpoint doğrulaması:

- proje geneli taramaya,
- ek araştırmaya,
- görev dışı regresyon kontrolüne,
- ilgili olmayan kaynak veya talimatların incelenmesine

dönüştürülmez.

Gerekli bilgi elde edildiğinde doğrulama durdurulur ve checkpoint akışına devam edilir.

Bir değişikliğin doğrulanması ayrı ve kapsamlı bir çalışma gerektiriyorsa checkpoint işlemi genişletilmez; durum kullanıcıya bildirilir.

Commit doğrulandıktan sonra push aşamasında aynı commit yeniden doğrulama görevine dönüştürülmez.

Push tamamlandıktan sonra yalnız repository durumu, `origin/master` eşitliği ve çalışma ağacı kontrol edilerek checkpoint tamamlanır.

## Onay Kuralı

Stage, commit ve push birbirinden ayrı üç işlemdir.

Her işlem kendi kullanıcı onayını ister.

`Evet`, `onaylıyorum` veya `devam et` cevabı yalnızca o anda bekleyen işlem için geçerlidir.

Bir adıma verilen onay sonraki adıma aktarılmaz.

## Güvenlik

- Test sonucu doğrulanmamış çalışma doğrudan doğrulanmış olarak kabul edilmez.
- Doğrulama checkpoint sırasında yapılacaksa yalnız ilgili değişikliğin doğrudan çalışma yolu kontrol edilir.
- Kullanıcı onayı olmadan stage, commit veya push yapma.
- `git_reset`, force push, branch değiştirme, branch oluşturma, merge veya rebase kullanma.
- Araç hata verirse gerçek hatayı sohbet ekranında kullanıcıya göster.
- Başarısız işlemi başarılı olarak bildirme.
- Push ve son kontrol tamamlanmadan checkpoint işlemini tamamlanmış sayma.