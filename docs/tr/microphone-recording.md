# Uygulama içinde ses kaydetme

`Toplantılar` ekranından mikrofonla kayıt alabilir ve dosya seçmeden konuşmacılı
metin hazırlatabilirsiniz. Analiz için toplantı modellerinin çalışıyor olması
gerekir; kaydı almak tek başına model hazırlamaz.

1. `Kayıt kaynağı` bölümünde **Mikrofonla kaydet** seçeneğine geçin.
2. Toplantıya bir ad verin ve konuşma dilini seçin. İsterseniz katılımcı üst
   sınırını, kesin konuşan kişi sayısını ve yeni kişileri hafızaya kaydetme
   seçeneğini ayarlayın. Kalıcı hafıza seçeneği profil yazma yetkisi gerektirir.
3. `Mikrofon` listesinden giriş cihazını seçip **Kaydı başlat** düğmesine basın.
   Tarayıcı istediğinde mikrofon iznini verin. Süre ve ses seviyesi kaydı izler.
4. Bitirdiğinizde **Durdur ve analiz et** düğmesine basın. Son ses tamamlanır,
   kayıt aktarılır ve ardından toplantı sonucu açılır. Mikrofon aktarım boyunca
   açık tutulmaz; metin ve konuşmacılar analiz ilerledikçe görünür.

Yalnız seçilen mikrofonun duyduğu ses kaydedilir. Bilgisayar sesi, kulaklıktan
gelen uzak katılımcılar veya Teams ses akışı otomatik yakalanmaz. Bir odada
birden çok kişi varsa mikrofonun hepsini yeterince temiz duyması gerekir.
Kayıt sırasında canlı metin gösterilmez.

**Kaydı iptal et** mevcut geçici kaydı bırakır ve mikrofonu kapatır. Kaydı
yeniden başlatmanız gerekir. Aktarım bağlantı hatası verirse sayfayı açık tutup
**Analizi yeniden dene** seçeneğini kullanın; aynı tamamlanmış ses tekrar
okunur. Sayfayı yenilemek veya kapatmak bu geçici kaydı geri getirmez.

Uzun kayıt tarayıcının geçici disk alanına yazılır; tamamı bellekte birikmez.
Tek kaydın sınırı **4 saat veya 2 GiB** değerlerinden önce ulaşılana kadardır;
disk alanı veya tarayıcı kotası daha erken sınır koyabilir. Bilinen 4 saat/2 GiB
sınırına gelindiğinde kayıt otomatik durur, sınır bildirimi gösterilir ve o ana
kadar eksiksiz kaydedilen ses analize gönderilir. Mikrofon kesilirse, disk kotası
dolarsa veya ses güvenle yazılamazsa eksik kayıt analize gönderilmez. Kayıt ve
aktarım bitene kadar sayfayı açık ve bilgisayarı uyanık tutun.

Geçici disk kopyası normal tamamlanma ve iptalde temizlenir. Sayfadan çıkışta
temizlik denenir; tarayıcı bu işlemi bitirmeden kapanırsa veya bilgisayar
zorla kapandığında bir geçici kopya diskte kalabilir;
uygulama bu kopmuş kaydı otomatik kurtarmaz veya analize göndermez. Aktarım
tamamlandıktan sonra sunucudaki kayıt ve kalıcı kişi profilleri mevcut saklama
kurallarını izler; tarayıcı geçicisinin temizlenmesi onları silmez.

Mikrofon kaydı desteklenen tarayıcıda güvenli bağlantı gerektirir: aynı
bilgisayarda `localhost`/`127.0.0.1` veya HTTPS kullanın. Düz HTTP ile başka bir
bilgisayarın ağ adresini açmak mikrofon erişimini engelleyebilir. İzin reddinde
tarayıcının site ayarlarından mikrofonu açın; cihaz yokluğunda giriş bağlantısını
ve başka uygulamaların mikrofon kullanımını kontrol edin. Tarayıcı gerekli ses
ve disk özelliklerini desteklemiyorsa açıklama gösterilir; **Dosya yükle**
yolu kullanılabilir. Her tarayıcı ve cihazda çalıştığı varsayılmaz.

Kısa konuşmalar metinde korunur. Yeni kişinin hafızaya girmesi için aynı kişiye
ait temiz konuşmanın toplamı 20 saniyeyi aşmalı, kalite/tutarlılık ve bilinmeyen
kişi kontrolleri geçmelidir. Daha uzun kayıt almak tek başına doğru tanıma veya
kalıcı profil garantisi değildir.

Davranışın kaynağı: [Accepted 007 PRD](../../specs/speaker-identity/PRDs/007-microphone-meeting-capture/PRD.md).
Mevcut model ve hafıza akışı: [toplantı rehberi](../MEETING_WORKFLOW.md).
Doğrulanan ortamlar ve açık testler: [mikrofon kanıtı](../evidence/2026-09-11-microphone-recording/README.md).
