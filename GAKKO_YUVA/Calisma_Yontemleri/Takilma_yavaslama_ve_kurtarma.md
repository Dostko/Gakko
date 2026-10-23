## Takılma, Yavaşlama ve Kurtarma

**Kullan:**

GAKKO, uygulama veya bağlı bir süreç normal çalışmasını sürdüremediğinde bu yöntem kullanılır.

Örnek durumlar:

- GAKKO cevap vermiyor veya işlem beklenenden uzun sürüyor.
- Uygulama, araç, terminal veya çalışan süreç takılıyor.
- CPU, GPU, RAM veya VRAM kullanımında olağan dışı durum görülüyor.
- Bir süreç veya alt süreç uygulamanın kapanmasını engelliyor.
- Aynı hata veya takılma tekrar ediyor.
- Sorunun hangi katmandan kaynaklandığı bilinmiyor.

**Amaç:**

Sorunun GAKKO, model, araç, uygulama, işletim sistemi veya donanım katmanlarından hangisinde oluştuğunu belirlemek.

Önce mevcut durum ve ölçümler incelenir. Sorunun kaynağı belirlendikten sonra yalnız ilgili katmana müdahale edilir.

Amaç sistemi rastgele yeniden başlatmak veya ayar değiştirmek değil, sorunun nedenini bulup sistemi çalışan duruma döndürmektir.