# Tasks — Mikrofon kaydından toplantı analizi

Kaynak: [Accepted PRD](PRD.md), [plan](plan.md).
Sabit profil: `kt-vibecoding-python-web-v2`.

- [x] T01 Önceki açık mikrofon isteğini 002 dosya tesliminden ayrı Accepted yeteneğe taşı; çıktı PRD/plan/tasks ve çift yönlü roadmap bağlantısı, kanıt kullanıcı kaynak seçimi kaydıdır.
- [x] T02a Yeni açık kullanıcı isteğiyle 007'yi etkinleştir ve WebM hedefini yerleşik PCM16/OPFS/WAV kararıyla değiştir; çıktı PRD Decisions 2–7, plan ve güncel roadmap satırı, kanıt 11 Eylül kullanıcı kayıt isteği ve mevcut 002 WAV sözleşmesidir.
- [ ] T02b Gerçek tarayıcı ses hızı/OPFS desteği ile mevcut WAV decoder uyumunu doğrula; çıktı cihaz/kapsayıcı kaynaklı kanıt, yeni bağımlılık veya API/şema değişikliğinin bulunmadığını gösteren incelemedir.
- [x] T03 Sınırlı üretici/disk kuyruğu ve mikrofon yaşam döngüsünü geliştir; çıktı işleme modülü ve OPFS kaydı, kanıt 16 MiB toplam sınır, 2 GiB/4 saatte kayıpsız durdurup analiz, kota hatası, son blok, başlık/örnek sayısı, iptal, cihaz kesilmesi ve geç izin temizliği testleridir. PCM/adaptör 26 otomatik test başarılı; fiziksel dört saatlik koşum iddiası yoktur.
- [x] T04a Ortak toplantı seçeneklerini koruyan TR/EN kayıt kontrollerini 008 görünümüne bağla; çıktı kayıt/durdur/iptal/cihaz/izin/hata arayüzü, kanıt sıradan/salt okunur yetki ve erişilebilirlik testleridir. Bileşenler 15 otomatik test, tarayıcıda 11 sınırlı arayüz gözlemiyle doğrulandı; fiziksel kayıt T02b/T05a altında açıktır.
- [ ] T04b Mühürlü WAV dosyasını değişmeyen 002 aktarımına bağla; çıktı kaynak ömrü/iptal/temizlik bütünleşmesi, kanıt gerçek HTTP/disk, RIFF uzunluk/parça/dolgu/RF64 regresyonları, hashli tekrar ve kontrat drift kontrolleridir. Eksik kayıt analiz edilmez.
- [ ] T05a Gerçek mikrofon kayıt→durdur→WAV→metin/hafıza senaryosunu paylaşılan harness ile kaydet ve manifestte kaydet; kanıt gerçek parola girişi, TR/EN sıradan kullanıcı, son ses, uygun model sonucu ve test kaynağı temizliğidir.
- [x] T05b Tam profil/güvenlik/tarayıcı kapılarını çalıştır ve kullanım/kanıt belgesini tamamla; kanıt komut/çıktı/sayı içeren sabit koşum raporudur. Tam profil kapısı 605+133=738 testle geçti; güvenlik aracı ve kabul edilmiş tarayıcı paketi eksikleri başarısız komutlarıyla kaydedildi. Bunlar ve L3 kabulü başarılı sayılmadı.

11 Eylül yeni kullanıcı talimatıyla uygulama artık etkin kapsamdır; işaretlenmemiş
görevler tamamlandı sayılmaz. 002'nin geçmiş dosya/kimlik kanıtı bu yeni mikrofon
yakalama veya gerçek cihaz başarısının yerine geçmez.

11 Eylül teslim kanıtı: [birleşik koşum raporu](../../../../docs/evidence/2026-09-11-microphone-recording/README.md).
T02b ve T05a için gerçek mikrofon izni istendi, yanıt gelmedi. T04b'nin dosya
ömrü, aynı hash/anahtarla aktarımı, RIFF gerçek disk testleri ve kontrat kapıları
geçti; tarayıcı OPFS dosyasının gerçek HTTP aktarımı henüz gözlenmediğinden bu
görev açık bırakıldı. Mikrofon senaryosu kaydedildi; paketli yürütücünün ve
fiziksel konuşmadan metin/hafıza kabulünün başarılı olduğu iddia edilmez.
