# GAKKO — Proje Ağacı ve Mimari

Bu belge GAKKO'nun güncel fiziksel yapısını ve ana parçaların görevlerini gösterir.

Ağaç yalnız mimari açıdan anlamlı dosya ve klasörleri içerir.
Geçici dosyalar, önbellekler ve model iç dosyaları gösterilmez.

## 1. Güncel Proje Ağacı

```text
D:\Gakko
├── .qwen
│   └── QWEN.md
├── GAKKO_YUVA
│   ├── Bilgi
│   │   ├── Ana_sistem.md
│   │   ├── dosya_formatlari.md
│   │   ├── Guncel_Durum.md
│   │   ├── Proje_Agaci_ve_Mimari.md
│   │   ├── Yapilacaklar.md
│   │   └── Yol_Haritasi.md
│   ├── Calisma_Yontemleri
│   │   ├── git_checkpoint_al.md
│   │   ├── Internet_arastirma.md
│   │   ├── projeler.md
│   │   ├── sohbet_gecmisi.md
│   │   └── Takilma_yavaslama_ve_kurtarma.md
│   ├── Hafiza
│   │   ......
│   │   └── Yakin_Gecmis_Fihristi.md
│   ├── Kayitlar
│   │   └── gakko_kurulus_gunu.md
│   ├── Prensipler
│   │   ├── Arac_kullanimi_prensipleri.md
│   │   ├── Belirsizlik_ve_halusinasyon_prensipleri.md
│   │   ├── Hafiza_ve_kaynak_prensipleri.md
│   │   └── Karar_ve_kaynak_secimi_prensipleri.md
│   └── Talimatlar
│       ├── Bilgi_Fihristi.md
│       ├── Calisma_Yontemleri_Fihristi.md
│       ├── GAKKO.md
│       ├── Hafiza_Fihristi.md
│       ├── Kayitlar_Fihristi.md
│       └── Prensipler_Fihristi.md
├── Gorseller
├── Kod_Blok
│   ├── Kod_Atolyesi_Sohbet
│   │   ├── css
│   │   │   ├── style_bolumler
│   │   │   │   ├── dosya_menu.css
│   │   │   │   ├── gecmis_sohbet.css
│   │   │   │   ├── menu_ayarlari.css
│   │   │   │   ├── sohbet_alani.css
│   │   │   │   └── sol_panel.css
│   │   │   └── style.css
│   │   ├── js
│   │   │   ├── app_bolumler
│   │   │   │   ├── dosya_koprusu_app.js
│   │   │   │   ├── dosya_menu_app.js
│   │   │   │   ├── gorsel_app.js
│   │   │   │   ├── sohbet_ekran_ayarlari_app.js
│   │   │   │   ├── sohbet_gorunumleri_app.js
│   │   │   │   └── sol_menuler_app.js
│   │   │   └── app.js
│   │   ├── Sohbet_Bilesenleri
│   │   │   ├── internet_kapisi
│   │   │   │   └── image_arama.py
│   │   │   ├── Qwen_oturum
│   │   │   │   ├── Dosya_ekleri
│   │   │   │   │   └── pdf_ayarlari.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── qwen_araclari.py
│   │   │   │   ├── qwen_ayarlar.py
│   │   │   │   ├── qwen_dosya_ekleri.py
│   │   │   │   ├── qwen_mcp.py
│   │   │   │   └── qwen_model.py
│   │   │   ├── sohbet_koprusu
│   │   │   │   ├── sohbet_gecmisi_koprusu.py
│   │   │   │   └── sohbet_gezgini.py
│   │   │   ├── internet_giris.py
│   │   │   ├── proje_dosya_yardimcilari.py
│   │   │   ├── qwen_oturumu.py
│   │   │   ├── sohbet_gecmisi.py
│   │   │   └── sohbet_koprusu.py
│   │   ├── gakko_sohbet_penceresi.pyw
│   │   └── index.html
│   ├── gakko_gui.pyw
│   └── main.py
├── yapay_zeka_modeli
│   ├── blobs
│   │   ├── ...
│   ├── Modelfile
│   └── Qwen3.8-27B-UD-IQ4_XS.gguf
├── .gitignore
└── Modelfile_64K_gpu


## 2. Ana Mimari

### .qwen

Qwen'in GAKKO çalışma ortamına giriş noktası ve yardımcı becerilerinin bulunduğu alandır.

`QWEN.md`, Qwen'in GAKKO kaynak zincirine giriş dosyasıdır.


### GAKKO_YUVA

Qwen'in kalıcı kaynak merkezidir.

- `Talimatlar` → ana yönlendirme ve fihristler
- `Prensipler` → davranış ve karar ilkeleri
- `Calisma_Yontemleri` → belirli işlerin nasıl yürütüleceği
- `Bilgi` → GAKKO ve teknik sistem hakkında güncel doğrulanmış bilgiler
- `Hafiza` → yakın geçmiş ve geçmiş çalışma bilgileri
- `Kayitlar` → önemli tarihsel kayıtlar


### Kod_Blok

GAKKO'nun teknik uygulama katmanıdır.

Burada:

- uygulamanın başlatılması,
- sohbet arayüzü,
- Qwen/Ollama bağlantısı,
- MCP araç bağlantıları,
- internet erişimi,
- sohbet geçmişi,
- dosya ekleri,
- GUI ve web arayüzü

gibi teknik işlevler bulunur.

Karar verme görevi bu katmana ait değildir.


### yapay_zeka_modeli

Yerel yapay zekâ modelinin fiziksel model dosyalarının ve Ollama model yapılandırmasının bulunduğu alandır.

Ana model:

`Qwen3.8-27B-UD-IQ4_XS.gguf`


## 3. Ana Çalışma Zinciri

Kullanıcı
↓
GAKKO arayüzü
↓
Qwen
↓
QWEN.md
↓
GAKKO_YUVA
↓
Gerekli kaynak veya MCP aracı
↓
Qwen kararı
↓
Kullanıcı


## 4. Mimari İlke

GAKKO'da karar merkezi Qwen'dir.

GAKKO_YUVA bilgi ve çalışma kaynaklarını sağlar.

Kod_Blok teknik uygulama ve bağlantı görevlerini yürütür.

MCP araçları Qwen'in dosya sistemi ve diğer teknik kaynaklara erişmesini sağlar.

Teknik katmanlar Qwen adına karar vermez.