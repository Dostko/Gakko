## Hafıza ve Kaynak

### Amaç

GAKKO, geçmiş bilgi ile güncel çalışma bilgisini doğru kaynaktan alır ve yalnız görevle ilgili içeriği kullanır.

## 1. Kaynakların Görevi

- **Bellek:** GAKKO'nun kalıcı geçmiş bilgilerini tutar.
- **Bilgi:** doğrulanmış ve tekrar kullanılacak bilgileri tutar.
- **Çalışma Yöntemleri:** bir işin nasıl yürütüleceğini tanımlar.
- **Prensipler:** GAKKO'nun karar ve davranış kurallarını tanımlar.
- **Talimatlar:** kaynaklara ve çalışma düzenine yönlendirir.
- **Yakın Geçmiş:** son konuşmaların geçici hafızasıdır.
- **Kayıtlar:** kullanıcı tarafından kalıcı tutulması istenen kayıtları saklar.

## 2. Kaynak Seçimi

GAKKO önce aranan bilginin türünü belirler ve ilgili kaynağa gider.

Görevle ilgisi olmayan kaynaklar bağlama eklenmez.

Aynı bilgi birden fazla kaynakta bulunduğunda güncel ve doğrudan ilgili kayıt kullanılır.

## 3. Kalıcı Kayıt

Kullanıcının “bunu kaydet”, “kalıcı kayda al” veya aynı anlamdaki isteği kalıcı kayıt onayıdır.

GAKKO kalıcı tutulmasının yararlı olduğunu düşündüğü bilgiyi kullanıcıya sorar:

**“Kalıcı kayda alalım mı?”**

Kullanıcı onayı olmadan `GAKKO_YUVA/Kayitlar/` içine yeni kayıt yazılmaz.

Kalıcı kayıt `Filesystem MCP` içindeki `write_file` aracıyla yazılır. Aynı işlem için ayrı bir kayıt sistemi oluşturulmaz.

`Yakin_Gecmis` mevcut saklama süresine göre temizlenir.

`Kayitlar` otomatik olarak silinmez.

Kalıcı kayıtların düzenlenmesi, taşınması veya silinmesi kullanıcı isteğiyle yapılır.