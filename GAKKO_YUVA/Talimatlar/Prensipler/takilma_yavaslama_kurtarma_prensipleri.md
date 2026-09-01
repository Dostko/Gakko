# Takılma, Yavaşlama ve Kurtarma Prensipleri

## Amaç

GAKKO; gecikme, takılma, donma, cevap vermeme veya beklenmeyen performans düşüşü yaşandığında
rastgele müdahale etmek yerine sorunun hangi katmanda oluştuğunu belirlemeli,
kanıt toplamalı ve kök nedene göre güvenli biçimde hareket etmelidir.

## Temel Prensipler

Uzun bekleme otomatik olarak model yavaşlığı kabul edilmez.

Önce hangi katmanın beklediği veya takıldığı belirlenir.

Model, Tool, terminal, process, GUI, worker, ağ, disk, CPU, GPU ve bellek yükü birbirinden ayrılarak değerlendirilir.

Ölçüm yapılmadan performans hakkında kesin hüküm verilmez.

Tek bir metriğe bakılarak neden-sonuç ilişkisi kurulmaz.

GPU, CPU, RAM, VRAM, güç, sıcaklık ve işlem süresi kendi anlamları doğrulandıktan sonra yorumlanır.

Sürekli çalışan veya bitmeyen process ve Tool çağrıları kontrolsüz bırakılmaz.

Uzun süren işler ile sonsuz çalışan işler birbirinden ayrılır.

Bir işlemin normalden uzun sürmesi durumunda önce görevin doğal çalışma süresi değerlendirilir.

Timeout yalnız güvenlik sınırı olarak kullanılmalı; uzun ama geçerli görevleri gereksiz yere kesmemelidir.

Sürekli çalışan görevler mümkünse yönetilen arka plan process'i olarak ele alınmalı ve durdurulabilir olmalıdır.

Bir worker veya child process uygulamanın güvenli kapanmasını engellememelidir.

Uygulama kapanırken çalışan işler güvenli biçimde sonlandırılmalı veya kontrollü şekilde beklenmelidir.

Semptomu bastırmak yerine kök neden bulunmalıdır.

Hata başka bir katmanda ortaya çıksa bile gerçek kaynak geriye doğru izlenmelidir.

Sorun çözülmeden aynı sistem üzerinde yeni özellik geliştirmeye geçilmemelidir.

Aynı hata tekrar ediyorsa yalnız kod satırı değil, mimari varsayım da sorgulanmalıdır.

Kurtarma işlemi kullanıcı verisini, proje dosyalarını veya çalışan sistemi riske atmamalıdır.

Riskli sonlandırma veya geri dönüşü zor işlem öncesinde mümkün olduğunda mevcut durum korunmalı ve doğrulanmalıdır.

Sorun geçici olarak ortadan kalksa bile neden doğrulanmadıysa çözülmüş kabul edilmez.

Kullanıcıya teknik ayrıntı yüklemek yerine sonuç, neden ve gerekli sonraki adım sade biçimde aktarılmalıdır.

## Kaynak Seçimi

Takılma veya yavaşlama durumunda ihtiyaç varsa:

Projeye özel yapı için Projeler / Kaynak alanına,

Geçmişte yaşanmış benzer durumlar için Bellek'e,

Teknik tanım veya referans için Bilgi'ye,

Güncel sürüm, driver, model veya dış sistem bilgisi için Internet'e,

Gerçek sistem durumunu ölçmek için uygun Tool ve runtime capability'lerine

başvurulmalıdır.

## Karar İlkesi

GAKKO'nun amacı mümkün olan en hızlı müdahaleyi yapmak değil,
doğru katmanı bulup en küçük güvenli müdahaleyle sistemi tekrar kararlı hale getirmektir.

## Sonraki Yönlendirme

Bu prensip mevcut durumu çözmek için yeterliyse göreve devam et.

Yeterli değilse Fihrist/PRENSIPLER_FIHRISTI.md dosyasına dön ve yeni duruma uygun prensibi seç.