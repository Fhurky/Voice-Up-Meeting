# Koşum raporu — 2026-09-11 · Bir saatlik ses gerçek işçi üzerinden tamamlandı ve kalıcı hafıza değişmedi.

1. Sonuç: Gerçek uygulama işi 1/1, kalıcı kaynak parçası 12/12, değişmeyen profil 6/6 ve değişmeyen örnek 6/6 başarılı — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok. İlk gözlem betiği kesildi; aynı işin salt okunur devam gözlemi ve son DB denetimi tamamlandı. Bu dar uzun kayıt/işçi/hafıza akışı L2 düzeyinde gözlendi.
2. Koşulan:

   | Ortam ve komut | Gözlenen sonuç |
   |---|---|
   | Windows `outputs/long3600-worker/run.py`; profil `kt-vibecoding-python-web-v2` | Frozen B kaynağı en fazla 65536 frame bloklarla tekrarlandı; 38 ses bölümü, aralarında 37 × 0,25 saniye ek sessizlik, son bölüm 89,6273125 saniyeye kırpıldı |
   | Bağımsız streaming frame karşılaştırması | Kaynak B ve ek sıfır frame'lerle byte eşliği; tam 57600000 frame, 3600 saniye, mono 16 kHz PCM16, 115200044 byte |
   | Gerçek public HTTP, sıradan izinli V8 kullanıcısı, `auto_enroll=true`, `language=en`, konuşmacı sayı ipucu yok | 2,203 saniye yükleme; iki `complete` aynı işi korudu. Tek yeni iş kimliği `cad11eeb-19c1-4f94-a299-c8fb28244761` |
   | Yerel gerçek CUDA işçisi, mevcut Community-1/Whisper/ECAPA modeli; ardından `resume-observation.py` ile yalnız aynı işin okunması | 12/12 parça, 3600 saniye, 5 konuşmacının tamamı `recognized`, toplam galeri 6; uygulama hata kodu yok |
   | Başlangıçtan başarı gözlemine duvar süresi | 600,178 saniye; yükleme ve gözlem kesintisini içerir. Ses süresine oranı yaklaşık 0,1667; 1200 saniyelik gözlem sınırı aşılmadı |
   | Gerçek worker PID 1 `/proc/1/status`, 45 RSS gözlemi | Başlangıç 92,387 MiB, son 95,672 MiB, örneklenmiş tepe 122,902 MiB. Süreç ömrü `VmHWM` başta/sonda 134,059 MiB; işlem başlangıcı ve üç servis konteyner kimliği değişmedi |
   | `audit-final.py`, gerçek PostgreSQL `READ ONLY` / `REPEATABLE READ` | Tam 12 kalıcı core, her biri 300 saniye; kaynak 0–3600 arasında boşluk/yinelenme yok, en büyük context 310 saniye; checkpoint 1 ve son `committed_until=3600` doğrulandı |
   | Kaynak/model ve hafıza denetimi | 12 provider kaydında aynı model kimliği, `community-vbx-fa015-v1` ve `cuda:0`; kaynak SHA eşit. Altı profil ve altı örneğin model, kaynak, vektör ve ad hashleri yükleme öncesi/sonrası aynı |
   | Çıktı ve özgün kayıtların korunması | 1280 transkript parçası, 52366 karakter; yalnız sayı ve hash kaydedildi. Frozen B, özgün protocol/V8 state ve ilk başarısız gözlem dosyaları değişmedi |

3. Maddeler:

   **KUSUR**

   M1 İlk gözlem betiği 9/12 parça sonrasında `bounded_worker_observation_failed` ile kapandı; istisna tipi yakalanmadığından sebebi bilinmiyor. Gerçek iş sonraki bağımsız kontrolde 10/12 ilerlemişti; dosyalar korunup aynı iş salt okunur izlenerek başarı doğrulandı.

   M2 İlk son-denetim sorgusu provider alanlarını checkpoint'in üst düzeyinde aradı ve `None` dönüşümünde durdu; yalnız yok sayılan denetim sorgusu gerçek `result.provider` yoluna düzeltildi. Son sorgu 12/12 core/model kontrolünü geçti; üretim kodu değiştirilmedi.

   **TUZAK**

   M3 Düzenli gözlem `07:04:51–07:07:24 UTC` aralığında kesildi; ilk ve devam betiğinin geçen-süre başlangıçları farklıdır. RSS örneklemesi kesintili ve yaklaşık 10 saniyeliktir; 122,902 MiB gerçek anlık tepe olarak yorumlanamaz.

   M4 Aynı süreç ömrünün 134,059 MiB `VmHWM` değeri başta/sonda eşittir; bu tüm süreç geçmişinin sınırıdır ve yalnız bu işe ait kesin zirve değildir. 600,178 saniye de izole model gecikmesi değil, gözlem kesintisini içeren toplam üst sınırdır.

   **GÖZLEM**

   M5 Ses SHA-256: `3577740b457b26b208463897fe52336c5b5ae1ebace86f0539ab4e48bd7a2724`; [sayısal kanıt](long3600-worker-results.json) SHA-256: `941d196088d435b8e662cdec27ce0cb04421d6b30e0e9bcdf62252dfa87e973a`. İlk hata, iki gözlem, tüm kaynak core'ları, model kimlikleri ve önce/sonra hashleri birlikte korunur.

   M6 Devam gözleminde yeni upload/complete isteği veya uygulama yeniden başlatması yapılmadı; eşikler ve model ayarları değiştirilmedi. İlk gözlem betiğinin kesilmesi uygulamanın iş sahipliğini veya ilerlemesini kesmedi.

   **AÇIK**

   M7 Kaynak aynı İngilizce kaydın tekrarıdır; bu koşum bağımsız doğruluk, Türkçe toplantı, 50 kişi, bütün 1/2/4 saatlik kaynaklar veya konuşma/kelime hata oranı kanıtı değildir. Amaç gerçek 3600 saniyelik yüklemenin sınırlı parçalarla tamamlanması ve hafızanın değişmemesidir.

   **YAN-ETKİ**

   M8 Yetkilendirilmiş bir uzun toplantı işi aynı V8 tenantında oluşturulup saklandı; profil/örnek sayısı değişmedi. Fixture ve yardımcılar yalnız yok sayılan `outputs/long3600-worker/` altında; rapor ve temizlenmiş JSON bu kanıt dizinine eklendi. Kaynak/model/servis yapılandırması değiştirilmedi.
