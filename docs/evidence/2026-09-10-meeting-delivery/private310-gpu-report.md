# Koşum raporu — 2026-09-11 · En büyük konuşmalı kaynak penceresinin gerçek özel GPU servisine aktarılması

1. Sonuç: 310 saniyelik konuşmalı kaynak özgün worker ve gerçek özel GPU servisi üzerinden başarıyla işlendi — birim 0 başarılı / gerçek HTTP-GPU 1 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`, Local RTX 4060, çalışan özel sağlayıcı `sha256:09dbebcbdaff48b701260d8e837344aca6c5bb13cde762cf14781dc37bd08110`; yeni worker sürecinde gerçek üretim bileşimi, `MeetingAudioStorage.validate/window` ve `HttpMeetingAdapter.ready/analyze`. Kaynak sabit A'nın 182,0250625 saniyelik konuşmasının 192 kHz/8 kanala dönüştürülüp 310 saniyeye sessizlikle tamamlanmış kaynak testi kopyasıdır.

   | Sınır / ölçüm | Gözlenen değer |
   | --- | --- |
   | Kaynak | 310 saniye, 192 kHz, 8 kanal PCM16; 952.320.044 bayt |
   | Kaynak SHA-256 | `dc10f0b2d540880228f104fe9434cf11e483455c546ca15bb0294db9fc1435fa` |
   | Özgün worker mono PCM16 aktarımı | 119.040.044 bayt; 120 MiB özel sınırının altında |
   | İstek SHA-256 | `0e7f8baf12c7d78d54a19307dd536bdcdd430f08491c92a3f6f51a1c1483ec77` |
   | Gerçek yanıt | HTTP 200; 145.724 bayt; 310 saniye / 16 kHz / `cuda:0` |
   | Gerçek diarization ve ASR çıktısı | 65 ham konuşma aralığı, 13 yerel model etiketi, 21 metin bölümü, 501 sözcük; içerik rapora alınmadı |
   | HTTP aktarımı ve model süresi | 35,192 saniye |
   | Worker tepe VmHWM | 213.241.856 bayt / 203,36 MiB |
   | Sıcak sağlayıcının başlangıç RSS'i | 5.259.857.920 bayt / 4,899 GiB |
   | HTTP sırasında örneklenen sağlayıcı RSS tepesi | 5.872.283.648 bayt / 5,469 GiB |
   | Bütün GPU başlangıç / tepe / son | 773 / 2950 / 936 MiB |
   | Kaynak gözlemi | 100 ms aralıkla 466 sağlayıcı RSS örneği, HTTP sırasında 350 örnek; 440 GPU örneği |

3. Maddeler:
   **KUSUR** — yok
   **TUZAK**
   M1 Sağlayıcı önceden yüklenmiş çalışan süreçtir; 100 ms RSS örnekleri daha kısa geçici artışları kaçırabilir. Kaydedilen tarihsel VmHWM yalnız bu isteğe ait değildir; soğuk başlangıç tepesi iddiası yapılmaz.
   M2 GPU ölçüsü bütün ekran kartını, masaüstü kullanımını ve mevcut altyapıyı kapsar; model dışındaki bellek çıkarılmadı. Worker ölçüsü yeni adres alanının VmHWM değeridir.
   M3 Kaynak yalnız sınır/kaynak testi için dönüştürülmüştür. Yerel model etiketleri kişi sayısı değildir; 13 etiket yeni kişi tanıma başarısı veya başarısızlığı sayılmaz ve özgün A/B/D/C doğruluk kanıtı yerine geçmez.
   **GÖZLEM**
   M4 Tam istek özgün kaynağın 310 saniyesini mono PCM16 olarak taşıdı; özel servis bunu 16 kHz'e çözüp yerel Community/Whisper modellerinde işledi. Tipli yanıt model kimlikleri ve güncel `community-vbx-fa015-v1` tarifiyle doğrulandı.
   M5 Tam worker/hafıza/adaptör nesneleri oluşturuldu; yalnız özel analiz çağrısı yapıldı. Veritabanı claim/checkpoint, toplantı oluşturma, profil ekleme veya hafıza yazımı yapılmadı; servisler yeniden başlatılmadı.
   M6 Kaynak hash'i ve program hash'leri çağrıdan önce donduruldu; tek istek tekrar veya ayar değişikliği olmadan geçti. Tam kayıtlar ignore kapsamındaki `outputs/2026-09-10-meeting-delivery/private310-resource/` altında; bu rapor ham metin, vektör veya erişim sırrı içermez.
   **AÇIK**
   M7 Bu koşum 310 saniyelik en büyük aktarım/model penceresini sınar; bütün toplantının veritabanı yazma belleğini, çoklu eşzamanlı işleri, soğuk model başlangıcını veya native Spark hedefini kanıtlamaz.
   **YAN-ETKİ**
   M8 Yalnız ignore kapsamındaki kaynak/ölçüm dosyaları ve backend geçici test kopyası oluşturuldu; mevcut bağımlılıklar kullanıldı. Model, kaynak sürümü, uygulama verisi veya kabul edilmiş politika değiştirilmedi.
