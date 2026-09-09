# GAKKO — Güncel Durum

## Genel Durum

GAKKO aktif geliştirme aşamasındadır.

Ana mimari Qwen merkezlidir. Karar verme, kaynak seçimi, araç seçimi ve yorumlama Qwen tarafından yapılır. Teknik katmanlar yalnızca bağlantı ve uygulama görevlerini yürütür.

## Yapay Zekâ

Ana model:

**gakko-qwen38-64k-gpu:latest**

- Qwen 3.8 27B tabanlıdır.
- 64K bağlam ile çalışır.
- Ana karar ve cevap üretim modelidir.

Yardımcı görsel model:

**qwen3-vl:8b**

- Görsel ve ekran görüntüsü analizlerinde kullanılır.
- Nihai cevap ana model tarafından üretilir.

Modeller Ollama üzerinden yerel olarak çalışır.

## GAKKO_YUVA

GAKKO_YUVA aktif olarak kullanılmaktadır.

Mevcut ana kaynak alanları:

- Talimatlar
- Prensipler
- Calisma_Yontemleri
- Bilgi
- Hafiza
- Kayitlar

QWEN.md üzerinden GAKKO kaynak zincirine giriş yapılır.

## Proje Çalışmaları

GAKKO aktif proje köküyle çalışabilir.

Qwen:

- proje yapısını inceleyebilir,
- dosya ve klasörlere erişebilir,
- dosya içeriklerinde arama yapabilir,
- gerekli dosyaları okuyabilir,
- kullanıcı onayı kapsamındaki dosya değişikliklerini yapabilir.

## MCP Sistemi

Dosya erişimi MCP tabanlıdır.

### Filesystem MCP

Dosya ve klasör işlemlerinde kullanılmaktadır.

Eski özel dosya erişim yolları ana mimariden kaldırılmıştır.

### Ripgrep

Dosya içeriklerinde hızlı metin araması için kullanılmaktadır.

Eski `search_files` Qwen'e sunulan araçlardan kaldırılmıştır.

Ripgrep sayesinde büyük dosyaların tamamını modele taşımadan ilgili satırlar bulunabilmektedir.

## İnternet

Qwen'in internet erişimi için mevcut internet araçları kullanılmaktadır.

İnterneti ne zaman ve neden kullanacağına Qwen karar verir.

## Sohbet ve Arayüz

Mevcut GAKKO arayüzünde:

- Sohbet
- Geçmiş
- Dosya / proje çalışma alanları

bulunmaktadır.

Web tabanlı arayüz HTML, CSS ve JavaScript ile çalışır.

## Performans

Ana model üretim hızında yaklaşık **46–49 token/sn** seviyeleri gözlemlenmiştir.

Sıcak oturumda basit sohbet yanıtı yaklaşık **4–5 saniye** seviyesine inebilmektedir.

Prompt cache'in ardışık çağrılarda giriş işleme süresini ciddi biçimde düşürdüğü gözlemlenmiştir.

## Güncel Performans Sorunları

Şu anda ana performans çalışması şu alanlardadır:

- İlk model çağrısındaki gecikme.
- Basit proje görevlerinde gereğinden fazla araç turu oluşması.
- Qwen'in bazı durumlarda dosya yolunu önce tahmin edip ardından proje keşfine çıkması.
- Araç kullanımında gereksiz bağlam ve tur maliyetinin azaltılması.

## Güncel Mimari Hedef

GAKKO'nun mevcut yönü:

**Qwen karar verir → gerekli kaynağı veya aracı seçer → teknik katman işlemi uygular → sonuç Qwen'e döner.**

Amaç bu zinciri mümkün olduğunca sade, hızlı ve doğrudan tutmaktır.