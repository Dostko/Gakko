# GAKKO — Proje Ağacı ve Mimari

Bu belge GAKKO'nun güncel fiziksel yapısını ve ana parçaların görevlerini gösterir.

Ağaç yalnız mimari açıdan anlamlı dosya ve klasörleri içerir.
Geçici dosyalar, önbellekler ve model iç dosyaları gösterilmez.

## 1. Güncel Proje Ağacı

D:\Gakko
│
├── .qwen
│   ├── QWEN.md
│   └── skills
│       ├── kod-inceleme
│       │   └── SKILL.md
│       └── sistematik-hata-ayiklama
│           └── SKILL.md
│
├── GAKKO_YUVA
│   │
│   ├── Bilgi
│   │   ├── Ana_sistem.md
│   │   ├── dosya_formatlari.md
│   │   ├── Guncel_Durum.md
│   │   ├── Proje_Agaci_ve_Mimari.md
│   │   ├── Yapilacaklar.md
│   │   └── Yol_Haritasi.md
│   │
│   ├── Calisma_Yontemleri
│   │   ├── git_checkpoint_al.md
│   │   ├── Internet_arastirma.md
│   │   ├── projeler.md
│   │   ├── sohbet_gecmisi.md
│   │   └── Takilma_yavaslama_ve_kurtarma.md
│   │
│   ├── Hafiza
│   │   ├── Yakin_Gecmis_Fihristi.md
│   │   └── Yakin_Gecmis
│   │
│   ├── Kayitlar
│   │   └── gakko_kurulus_gunu.md
│   │
│   ├── Prensipler
│   │   ├── arac_kullanimi_prensipleri.md
│   │   ├── Belirsizlik_ve_halusinasyon_prensipleri.md
│   │   ├── Hafiza_ve_kaynak_prensipleri.md
│   │   └── Karar_ve_kaynak_secimi_prensipleri.md
│   │
│   └── Talimatlar
│       ├── Bilgi_Fihristi.md
│       ├── Calisma_Yontemleri_Fihristi.md
│       ├── GAKKO.md
│       ├── Hafiza_Fihristi.md
│       ├── Kayitlar_Fihristi.md
│       └── Prensipler_Fihristi.md
│
├── Kod_Blok
│   ├── gakko_gui.pyw
│   ├── main.py
│   │
│   └── Kod_Atolyesi_Sohbet
│       ├── gakko_sohbet_penceresi.pyw
│       ├── index.html
│       │
│       ├── css
│       │   └── style.css
│       │
│       ├── js
│       │   └── app.js
│       │
│       └── Sohbet_Bilesenleri
│           ├── internet_giris.py
│           ├── proje_dosya_yardimcilari.py
│           ├── qwen_oturumu.py
│           ├── sohbet_gecmisi.py
│           ├── sohbet_koprusu.py
│           │
│           └── Qwen_oturum
│               ├── qwen_araclari.py
│               ├── qwen_ayarlar.py
│               ├── qwen_dosya_ekleri.py
│               ├── qwen_model.py
│               └── __init__.py
│
└── yapay_zeka_modeli
    ├── Modelfile
    └── Qwen3.8-27B-UD-IQ4_XS.gguf


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