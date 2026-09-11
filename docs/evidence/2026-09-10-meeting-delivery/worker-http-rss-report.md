# Koşum raporu — 2026-09-11 · En büyük ses penceresinin özel HTTP aktarımındaki yürütücü belleği

1. Sonuç: 310 saniyelik en büyük kaynak penceresi gerçek HTTP üzerinden kabul edilip ayrıştırıldı — birim 0 başarılı / TCP aktarım 1 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`, yerel Linux backend imajı `sha256:e04840120dcc7386f8e612439fff10d72908db0bfef7e225dafe05168eba1994`; ayrı Python süreçlerinde yürütücü bileşimi ve loopback TCP sağlayıcı fikstürü.

   | Sınır / aşama | Gözlenen değer |
   | --- | --- |
   | Kaynak | 310 saniye, 192 kHz, 8 kanal PCM16; 952.320.044 bayt |
   | Kaynak SHA-256 | `8a50cc2f6020164184a86e99d6786bf069f5c9be6f606194eb031ab551a41840` |
   | Gerçek gönderilen mono PCM16 WAV | 119.040.044 bayt |
   | İstemci ve alıcıda eşleşen SHA-256 | `3d414ad9523907fc29705256011671afa1e127d5585a170ccefe3f0547252763` |
   | Gerçek HTTP yanıtı | 8.208.348 bayt; tipli sözleşmede 256 metin bölümü |
   | Yürütücü modülleri yüklendiğinde | 86.114.304 bayt / 82,12 MiB |
   | Yürütücü oluşturulup hazır yanıtı doğrulandığında | 89.939.968 bayt / 85,77 MiB |
   | Kaynak doğrulandıktan sonra | 96.055.296 bayt / 91,61 MiB |
   | Mono pencere çıkarıldıktan sonra | 213.692.416 bayt / 203,79 MiB |
   | HTTP yanıtı ayrıştırıldıktan sonraki tepe | 234.401.792 bayt / 223,54 MiB |
   | Geçen süre | 8,75 saniye |

3. Maddeler:
   **KUSUR** — yok
   **TUZAK**
   M1 Tepe bellek Linux yeni süreç adres alanının `/proc/self/status` `VmHWM` değeridir; önceki üst süreç kullanımını taşıyabilen `ru_maxrss` kullanılmadı ve sağlayıcı süreci ölçüme dahil edilmedi.
   M2 Bu yol 256 MiB sınırının 32,46 MiB altında kaldı; sonuç bütün işin aynı sınır altında kalacağını veya bütün geçerli 8 MiB JSON şekillerinin aynı belleği kullanacağını kanıtlamaz.
   **GÖZLEM**
   M3 Gerçek `MeetingWorker`/hafıza/adaptör nesneleri oluşturuldu; `MeetingAudioStorage.validate/window`, `HttpMeetingAdapter.ready/analyze`, hizmet ve iş/tenant başlıkları ile gönderilen gövdenin tamamı doğrulandı.
   M4 Ham ölçüm, alıcı gözlemi ve yeniden çalıştırılabilir deney `outputs/2026-09-10-meeting-delivery/worker-http-rss-*` altında korundu; bu bir model doğruluğu veya ses tanıma testi değildir.
   **AÇIK**
   M5 Veri tabanı claim/checkpoint yazımı, iş sonlandırma ve model hesaplaması çalıştırılmadı; ölçüm istenen kaynak okuma ve gerçek özel HTTP sınırına aittir. Tam uygulama bellek tavanı bu ölçümden çıkarılamaz.
   **YAN-ETKİ**
   M6 Önceki geçici kaynak kaldırılmış olduğu için mevcut `silence_source` test yardımcısıyla aynı boyutta seyrek sessizlik kaynağı ayrı `/tmp/voiceup-worker-http-rss-20260911` dizininde üretildi; depo üretim kodu, veri tabanı ve GPU değiştirilmedi.
