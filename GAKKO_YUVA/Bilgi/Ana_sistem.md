# GAKKO — ANA SİSTEM

## 1. GAKKO'nun Amacı

GAKKO, yerel yapay zekâ modeli Qwen merkezli çalışan bir yapay zekâ ve proje çalışma ortamıdır.

Temel amaç; anlama, yorumlama, kaynak seçimi, araç kullanımı ve karar verme görevlerini yapay zekâya bırakırken teknik katmanları mümkün olduğunca sade tutmaktır.

Ana ilkeler:

- GAKKO'nun ana karar merkezi Qwen'dir.
- Teknik katmanlar Qwen adına karar vermez.
- Qwen ile kaynaklar arasına mümkün olan en az teknik katman konulur.
- Kod yalnızca bağlantı, araç erişimi, kullanıcı arayüzü ve çalıştırma gibi teknik görevleri yerine getirir.


## 2. Yapay Zekâ Modelleri

### Ana Model

**gakko-qwen38-64k-gpu:latest**

- GAKKO'nun ana yapay zekâ modelidir.
- Qwen 3.8 27B tabanlıdır.
- 64K bağlam ile çalışır.
- Anlama, düşünme, karar verme, araç seçme ve cevap üretme görevlerini yürütür.
- GAKKO'nun ana karar merkezidir.

### Yardımcı Görsel Model

**qwen3-vl:8b**

- Görsel ve ekran görüntülerinin analizinde kullanılır.
- Görsellerdeki yazıların ve görsel içeriğin anlaşılmasına yardımcı olur.
- Yardımcı görsel analiz üretir.
- Nihai değerlendirme, karar ve cevap ana Qwen modeli tarafından yapılır.


## 3. Model Çalıştırma Altyapısı

### Ollama

GAKKO'nun yerel yapay zekâ modellerini çalıştıran servistir.

- Ana Qwen modeli Ollama üzerinden çalışır.
- Yardımcı görsel model Ollama üzerinden çalışır.
- Model ile bilgisayar donanımı arasındaki çalışma altyapısını sağlar.
- Ana model 64K bağlam profiliyle kullanılmaktadır.


## 4. GAKKO Uygulaması

GAKKO, kullanıcı ile Qwen arasındaki ana uygulamadır.

Başlıca görevleri:

- Kullanıcı mesajlarını Qwen'e ulaştırmak.
- Qwen cevaplarını kullanıcıya göstermek.
- Sohbet arayüzünü sağlamak.
- Sohbet geçmişini sunmak.
- Aktif proje çalışma alanını sunmak.
- Dosya ve araç erişimleri için gerekli teknik bağlantıyı sağlamak.
- Görsel ve diğer desteklenen içerikleri gerekli modellere ulaştırmak.

GAKKO uygulaması:

- Qwen adına karar vermez.
- Kaynak seçmez.
- Kaynak içeriğini kendi başına yorumlamaz.
- Hangi dosyanın gerekli olduğuna karar vermez.
- Hangi aracın kullanılacağını belirlemez.


## 5. GAKKO_YUVA

GAKKO_YUVA, Qwen'in kalıcı çalışma ve kaynak merkezidir.

Ana kaynak alanları:

- Talimatlar
- Prensipler
- Calisma_Yontemleri
- Bilgi
- Hafiza
- Kayitlar
- Projeler

Qwen ihtiyaç duyduğu kaynağı kendisi seçer, okur, yorumlar ve karar verir.

### QWEN.md

`QWEN.md`, istisna_ilk_talimat.md → Pusula.md 'nin ana başlangıç noktasıdır.

Qwen buradan ana kaynak haritası olan:

`GAKKO_YUVA/Talimatlar/GAKKO.md`

dosyasına ulaşır.

### GAKKO.md

`GAKKO.md`, ana kaynak haritasıdır.

Göreve göre Qwen'in:

- doğrudan cevap vermesine,
- ilgili fihriste gitmesine,
- aktif proje üzerinde çalışmasına,
- gerekli Bilgi kaynağını kullanmasına,
- gerekli Hafiza kaynağını kullanmasına,
- gerekli Prensip veya Calisma_Yontemi kaynağına ulaşmasına

yön verir.

Kaynak seçimi ve karar Qwen'e aittir.


## 6. Projeler

GAKKO aktif projeler üzerinde çalışabilir.

Aktif proje kökü Qwen'in araç erişimine açılır.

Qwen gerektiğinde:

- proje yapısını inceleyebilir,
- dosya içeriklerinde arama yapabilir,
- gerekli dosyaları okuyabilir,
- kullanıcı onayı kapsamındaki değişiklikleri gerçekleştirebilir.

Aktif proje kökü ve görev için gerekli dosya bilgisi zaten biliniyorsa Qwen doğrudan aktif proje üzerinde çalışabilir.

Gereksiz proje keşfi ve kaynak dolaşması yapılmaması hedeflenir.


## 7. MCP Dosya ve Araç Erişimi

GAKKO'nun dosya ve proje erişimi MCP tabanlıdır.

Temel yapı:

Qwen  
↓  
MCP istemci katmanı  
↓  
MCP araçları  
↓  
Dosya sistemi

### Filesystem MCP

Dosya ve klasör işlemlerini sağlar.

Başlıca görevleri:

- dosya okuma,
- dosya oluşturma ve düzenleme,
- klasör işlemleri,
- dosya bilgisi alma,
- izin verilen dosya sistemi alanlarına erişim.

Eski `read_file` aracı Qwen'e sunulmaz.

Eski `search_files` aracı aktif içerik arama aracı olarak kullanılmaz.

### Ripgrep

Dosya içeriklerinde hızlı metin araması için kullanılır.

- Dosyanın tamamını modele taşımadan içerikte arama yapabilir.
- Eşleşen satırları bulabilir.
- Büyük kod ve metin dosyalarında gereksiz bağlam kullanımını azaltır.

Arama aracını kullanıp kullanmamaya Qwen karar verir.


## 8. Teknik Katmanın Sorumluluğu

Teknik bağlantı katmanı:

- MCP bağlantısını kurar.
- Araçları Qwen'e sunar.
- Qwen'in istediği aracı teknik olarak çalıştırır.
- Araç sonucunu tekrar Qwen'e taşır.

Teknik katman:

- dosya seçmez,
- fihrist seçmez,
- kaynakların anlamını yorumlamaz,
- Qwen adına karar vermez.

Araç sonucunun yorumlanması ve sonraki adıma karar verilmesi Qwen'e aittir.


## 9. Temel Çalışma Akışı

Kullanıcı  
↓  
GAKKO  
↓  
Ana Qwen modeli  
↓  
QWEN.md  
↓  
istisna_ilk_talimat.md
↓
Pusula.md
↓  
Görev için gerekli kaynak veya araç  
↓  
Qwen değerlendirmesi ve kararı  
↓  
Gerekirse MCP araç kullanımı  
↓  
Araç sonucu Qwen'e döner  
↓  
Qwen nihai cevabı üretir  
↓  
GAKKO  
↓  
Kullanıcı

Kaynak, proje veya araç gerektirmeyen basit sohbetlerde Qwen doğrudan cevap verebilir.


## 10. Ana Mimari İlkesi

GAKKO'nun merkezinde Qwen bulunur.

- GAKKO_YUVA, Qwen'in düzenli ve kalıcı kaynak merkezidir.
- MCP, Qwen'in dosya sistemi ve araçlarla teknik bağlantısını sağlar.
- Ollama yapay zekâ modellerini çalıştırır.
- GAKKO kullanıcı ile sistem arasındaki uygulama katmanıdır.

**Karar veren katman Qwen'dir.**

# GAKKO — Proje Ağacı ve Mimari

Bu belge GAKKO'nun güncel fiziksel yapısını ve ana parçaların görevlerini gösterir.

Ağaç yalnız mimari açıdan anlamlı dosya ve klasörleri içerir.
Geçici dosyalar, önbellekler ve model iç dosyaları gösterilmez.

## 1. Güncel Proje Ağacı


D:\Gakko
├── ├── .qwen
│   └── QWEN.md
├── GAKKO_YUVA
│   ├── Bilgi
│   │   ├── Ana_sistem.md
│   │   └── dosya_formatlari.md
│   ├── Calisma_Yontemleri
│   │   ├── git_checkpoint_al.md
│   │   ├── Internet_arastirma.md
│   │   ├── projeler.md
│   │   ├── sohbet_gecmisi.md
│   │   └── Takilma_yavaslama_ve_kurtarma.md
│   ├── Hafiza
│   │   ├── Yakin_Gecmis
│   │   │   └── ...
│   │   └── Yakin_Gecmis_Fihristi.md
│   ├── Kayitlar
│   │   ├── 2026-09-14-kayitlar-paneli-calisti.md
│   │   └── gakko_kurulus_gunu.md
│   ├── Prensipler
│   │   ├── Arac_kullanimi_prensipleri.md
│   │   ├── Belirsizlik_ve_halusinasyon_prensipleri.md
│   │   ├── Hafiza_ve_kaynak_prensipleri.md
│   │   └── Karar_ve_kaynak_secimi_prensipleri.md
│   └── Talimatlar  
        └── istisna_ilk_talimat.md
│       └── Pusula.md
├── Gorseller
├── Kod_Blok
│   ├── Kod_Atolyesi_Sohbet
│   │   ├── css
│   │   │   ├── style_bolumler
│   │   │   │   ├── dosya_menu.css
│   │   │   │   ├── gecmis_sohbet.css
│   │   │   │   ├── kayitlar.css
│   │   │   │   ├── menu_ayarlari.css
│   │   │   │   ├── sohbet_alani.css
│   │   │   │   └── sol_panel.css
│   │   │   └── style.css
│   │   ├── js
│   │   │   ├── app_bolumler
│   │   │   │   ├── app.js
│   │   │   │   ├── dosya_koprusu_app.js
│   │   │   │   ├── dosya_menu_app.js
│   │   │   │   ├── gorsel_app.js
│   │   │   │   ├── kayitlar.js
│   │   │   │   ├── pratik_yollar.js
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
│   │   │   │   ├── kayitlar_koprusu.py
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
│   │   └── ...
│   ├── manifests
│   │   └── registry.ollama.ai
│   │       └── library
│   │           └── qwen3-vl
│   │               └── 8b
│   ├── Modelfile
│   └── Qwen3.8-27B-UD-IQ4_XS.gguf
├── .gitignore
└── Modelfile_64K_gpu


## 2. Ana Mimari

### .qwen

Qwen'in istisna_ilk_talimat.md → Pusula.md çalışma ortamına giriş noktası ve yardımcı becerilerinin bulunduğu alandır.

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
istisna_ilk_talimat.md
↓ 
Pusula.md
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

ana model → gakko-gemma4-64k
görsel/OCR → qwen3-vl:8b
Qwen3.8 → artık ana model değil, gerekirse ayrı ağır/kod modeli
eski Qwen-merkezli ifadeler temizlenecek
GAKKO_YUVA ve çalışma akışı bugünkü gerçek mimariye göre yazılacak