# Prensipler Fihristi

Bu fihrist, GAKKO'nun karşılaştığı duruma göre
hangi prensip dosyasına başvurması gerektiğini gösterir.

Fihristin görevi prensiplerin içeriğini tekrar etmek değil,
doğru prensip kaynağına yönlendirmektir.

---

## Belirsizlik ve Halüsinasyon

**Dosya:**
`../belirsizlik_ve_halusinasyon_prensipleri.md`

**Kullan:**
- Bilgi eksikse.
- Bilginin doğruluğundan emin olunamıyorsa.
- Teknik bir metrik veya ölçüm yorumlanacaksa.
- Kaynaklar birbiriyle çelişiyorsa.
- Bilinen bilgi ile çıkarım veya tahmin birbirine karışabilecekse.
- Projeler, Bellek, Bilgi veya Internet kaynaklarından hangisine başvurulacağı belirsizse.
- Riskli veya geri dönüşü zor bir işlem öncesinde doğrulama gerekiyorsa.
- Daha önce yapılan bir yorumun veya kararın hatalı olabileceği fark edilirse.

**Amaç:**
Tahmin ederek boşluk doldurmak yerine doğru kaynağı seçmek,
kanıtı değerlendirmek ve yeterli doğruluk sağlandıktan sonra karar vermek.

---

## Takılma, Yavaşlama ve Kurtarma

**Dosya:**
`../takilma_yavaslama_kurtarma_prensipleri.md`

**Kullan:**
- GAKKO cevap vermiyor veya beklenenden uzun sürüyorsa.
- Uygulama, Tool, terminal veya process takılmış görünüyorsa.
- Performans düşüşünün nedeni belirsizse.
- CPU, GPU, RAM, VRAM veya başka teknik ölçümler yorumlanacaksa.
- Worker veya child process kapanmayı engelliyorsa.
- Aynı hata veya takılma tekrar ediyorsa.
- Sistem güvenli biçimde kurtarılmalıysa.

**Amaç:**
Sorunun hangi katmanda oluştuğunu belirlemek,
kanıt toplamak, kök nedeni bulmak ve en küçük güvenli müdahaleyle sistemi tekrar kararlı hale getirmek.

---

## Bellek ve Kaynak

**Dosya:**
`../bellek_ve_kaynak_prensipleri.md`

**Kullan:**
- Geçmiş bir karar, tercih veya çalışma bilgisi gerekiyorsa.
- Projeye ait kaynakların hangisinin okunacağı seçilecekse.
- Bellek, Bilgi, Projeler / Kaynak veya Talimatlar arasında ayrım yapılacaksa.
- Kalıcı bilgi ile geçici çalışma bilgisi birbirine karışabilecekse.
- Çok sayıda kaynak arasından yalnız gerekli olanların seçilmesi gerekiyorsa.

**Amaç:**
Bellek ile kaynakları birbirine karıştırmadan kullanmak,
yalnız görev için gerekli bilgileri seçmek ve gereksiz bilgi yükünü önlemek.

---

## Karar ve Kaynak Seçimi

**Dosya:**
`../karar_ve_kaynak_secimi_prensipleri.md`

**Kullan:**
- Bir görev için hangi bilgi kaynağının kullanılacağı belirlenecekse.
- Talimatlar, Calisma_Yontemleri, Bellek, Bilgi, Projeler / Kaynak veya Internet arasında seçim yapılacaksa.
- Gereksiz dosya veya kaynak taraması önlenmek isteniyorsa.
- Bir kaynağın yeterli olup olmadığına karar verilecekse.
- Bir sonraki kaynağa geçilip geçilmeyeceği belirlenecekse.

**Amaç:**
Fihrist ve kaynak haritasını kullanarak doğru kaynağa ulaşmak,
yalnız gerekli bilgiyi almak ve yeterli bilgi bulunduğunda aramayı durdurmak.

---

## Internet Araştırma

**Dosya:**
`../internet_arastirma_prensipleri.md`

**Kullan:**
- Aranan bilgi yerel kaynaklarda bulunamıyorsa.
- Mevcut bilgi eski veya yetersizse.
- Görev güncel veya dış dünyaya bağlı bilgi gerektiriyorsa.
- Internetten doğru ve güvenilir kaynak seçilmesi gerekiyorsa.
- Bulunan bilginin güncelliği veya doğruluğu kontrol edilecekse.

**Amaç:**
Aranan bilgiye odaklanmak, doğru kaynağa ulaşmak ve bilgi bulunduğunda aramayı sonlandırmak.

---

## Sonraki Fihrist

- Bu fihristte uygun prensip bulunamadiysa `PRENSIPLER_FIHRISTI_02.md` dosyasina gec.