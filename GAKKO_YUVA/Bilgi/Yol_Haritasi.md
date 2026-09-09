# GAKKO — Yol Haritası

## Ana Hedef

GAKKO'yu sade, yerel, Qwen merkezli ve gerçek projeler üzerinde çalışabilen güçlü bir yapay zekâ çalışma ortamı haline getirmek.

Temel yön:

**Qwen karar verir → gerekli kaynak veya aracı seçer → teknik katman işlemi uygular → sonuç Qwen'e döner.**

Teknik katmanların Qwen adına karar vermediği, gereksiz özel kodların bulunmadığı mümkün olduğunca doğrudan bir yapı korunacaktır.


## 1. Ana Mimarinin Sağlamlaştırılması

Öncelik mevcut çalışan yapının sade ve güvenilir hale gelmesidir.

Hedefler:

- Qwen merkezli karar yapısını korumak.
- Eski veya aynı işi yapan paralel sistemleri kaldırmak.
- MCP tabanlı dosya ve araç erişimini ana standart olarak kullanmak.
- Qwen ile GAKKO_YUVA arasındaki gereksiz teknik katmanları azaltmak.
- Çalışan özelliklerde regresyon oluşturmadan sistemi sadeleştirmek.


## 2. Araç Kullanımının Hızlandırılması

Qwen'in proje ve dosya çalışmalarında daha az turla sonuca ulaşması hedeflenmektedir.

Özellikle:

- Gereksiz araç çağrılarını azaltmak.
- Bilinen aktif proje kökünü doğrudan kullanmak.
- Dosya yolu tahminlerinden kaynaklanan gereksiz keşifleri azaltmak.
- Ripgrep ile gerekli içeriği dosyanın tamamını okumadan bulmak.
- Büyük araç çıktılarının bağlamı gereksiz büyütmesini önlemek.


## 3. Model ve Oturum Performansı

Ana modelin mevcut kalite seviyesi korunurken çalışma süresinin iyileştirilmesi hedeflenmektedir.

Odak noktaları:

- İlk model çağrısındaki gecikmeyi incelemek.
- Sıcak oturum performansını korumak.
- Prompt cache kullanımını ve etkisini daha net ölçmek.
- Çok turlu araç görevlerinde toplam model işleme süresini azaltmak.

Model değişimi yalnız açık ve anlamlı bir kalite veya performans avantajı oluşursa değerlendirilecektir.


## 4. GAKKO_YUVA'nın Olgunlaştırılması

GAKKO_YUVA, Qwen'in ana kalıcı kaynak merkezi olarak geliştirilmeye devam edecektir.

Hedefler:

- Kaynakların görevlerinin net kalması.
- Aynı bilginin birden fazla yerde tekrar edilmemesi.
- Güncelliğini kaybeden bilgilerin kaldırılması veya doğrudan güncellenmesi.
- Fihristlerin yalnız yaşayan ve gerçek kaynakları göstermesi.
- Qwen'in gerekli kaynağa mümkün olan en kısa yoldan ulaşması.

Bilgi katmanındaki güncel sistem belgeleri GAKKO'nun yaşayan teknik ve mimari referansı olacaktır.


## 5. Proje Çalışma Yeteneğinin Geliştirilmesi

GAKKO'nun gerçek projelerde günlük çalışma aracı olarak kullanılabilmesi geliştirilecektir.

Qwen'in:

- projeyi anlaması,
- gerekli dosyayı bulması,
- kod ve içerik incelemesi,
- kontrollü değişiklik yapması,
- sonucu doğrulaması

mümkün olduğunca doğal ve doğrudan hale getirilecektir.

Aktif proje bilgisi mevcutken gereksiz proje keşfi yapılmaması temel hedeflerden biridir.


## 6. İnternet ve Görsel Yetenekler

Mevcut internet ve görsel erişimlerinin Qwen merkezli yapı içinde doğal biçimde kullanılması sürdürülecektir.

- İnternet erişimi yalnız gerektiğinde kullanılacaktır.
- Kaynak seçimi ve değerlendirme Qwen tarafından yapılacaktır.
- Görsel analiz yardımcı model tarafından gerçekleştirilebilir.
- Nihai yorum ve karar ana Qwen modeline ait olacaktır.


## 7. Arayüz ve Kullanım Deneyimi

GAKKO arayüzü mevcut işlevleri korunarak geliştirilecektir.

Amaç:

- sade,
- hızlı,
- dikkat dağıtmayan,
- proje çalışmasına uygun

bir çalışma ortamı oluşturmaktır.

Arayüz değişiklikleri ana yapının ve çalışan özelliklerin önüne geçmeyecektir.


## Uzun Vadeli Yön

GAKKO'nun hedefi yalnızca sohbet eden bir yerel yapay zekâ olmak değildir.

Hedef; kendi kaynaklarını kullanabilen, projeleri anlayabilen, araçlarla çalışabilen, geçmiş çalışma bilgisinden yararlanabilen ve kullanıcının gerçek işlerini sürdürebilen yerel bir yapay zekâ çalışma ortamı oluşturmaktır.

Bu gelişim sırasında temel ilke değişmeyecektir:

**Karar Qwen'de, teknik uygulama araçlarda, kalıcı kaynaklar GAKKO_YUVA'dadır.**