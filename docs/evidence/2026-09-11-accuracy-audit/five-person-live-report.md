# Koşum raporu — 2026-09-11 · Temiz hafızada beş kişi, gerçek servis yeniden başlatması ve altıncı kişinin kaydı

1. Sonuç: Değişmeyen A/B/D/C protokolü yeni sıradan kullanıcıyla gerçek model ve HTTP akışında geçti — birim 0 başarılı / canlı HTTP 4 başarılı / yeniden başlatma 1 başarılı / kaynak-dosya denetimi 3 başarılı / son ses örneği 6 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`; Windows/Python 3.12 istemci, mevcut Docker/Linux FastAPI, PostgreSQL, işçi ve yerel GPU çıkarım servisi kullanıldı. `scripts/run-meeting-evaluation.py` ve `outputs/2026-09-10-meeting-delivery/fixtures/protocol.json` değiştirilmedi. İlk komut `--repeat-complete --stop-after-upload-b`, devam komutu aynı kimlik bilgileri ve durum dosyasıyla `--repeat-complete --resume` kullandı; modele kişi sayısı veya kaynak kimliği verilmedi.

   | Adım | Gözlenen karar | Galeri | Kaynak eşleme sonucu |
   |---|---|---:|---|
   | A | 5 yeni profil; beşine isim verildi | 5 | 5 kişi, başarılı |
   | B yüklenmişken | Henüz işlenmemiş B öncesi beş örnek denetlendi | 5 | 5/5 kaynak, dosya ve model soy bilgisi başarılı |
   | Gerçek yeniden başlatma | `scripts/stack.sh restart backend worker`, çıkış 0; iki `StartedAt` değişti, HTTP 200 | 5 | İlk beş profil, örnek ve fiziksel dosya aynı |
   | B | Aynı isimli ve aynı kimlikli 5 profil tanındı | 5 | 5 kişi, başarılı |
   | D | 5 profil tanındı; kısa konuşan altıncı kişi `profile_pending/insufficient_speech` | 5 | 6 kişi, başarılı |
   | C | 5 profil tanındı; yalnız altıncı kişi yeni kaydedildi | 6 | 6 kişi, başarılı |
   | Son denetim | Altı profilin tamamı ve altı saklanan ses örneği incelendi | 6 | 6/6 kaynak ve fiziksel dosya kontrolü; ilk 5 değişmedi |

   Üç denetim gerçek PostgreSQL `REPEATABLE READ, READ ONLY` transaction'ında toplam 16 profil görünümünü kontrol etti; her saklanan WAV özgün kaynak aralıklarından yeniden oluşturularak fiziksel dosyanın ve kayıtlı model/örnek karmalarının tamamıyla eşleştirildi. Dört toplantının tekrarlanan tamamlama çağrısı da ek iş veya profil oluşturmadı. [Makine özeti](five-person-live-results.json) komut çıkışlarını, zamanları, kaynak/kod/kanıt SHA-256 değerlerini ve altı örneğin ayrı ölçümlerini içerir; özel durum ve günlük dosyaları `outputs/2026-09-11-accuracy-audit/five-person-native-v1/` altında korunur.
3. Maddeler:
   **KUSUR** — yok
   **TUZAK**
   M1 CLI devamı tek başına yeniden başlatma kanıtı sayılmadı: B hâlâ `uploading` durumundayken önce/sonra gerçek veritabanı ve dosya görüntüleri alındı; aradaki mevcut wrapper komutunun çıkışı ve iki servisin başlangıç zamanları ayrı kaydedildi.
   M2 Protokolün metin-kaynak eşlemesi en az %90 baskın kaynak payı ve kayıtlı bölünme eşikleri kullanır; geçmesi sıfır sözcük-atama hatası demek değildir. A/B/D/C için en düşük paylar sırasıyla %91.7183/%90.1224/%95.1195/%97.7707; kişiye atanmayan metin süreleri 6.50/2.92/9.36/16.48 saniyedir.
   **GÖZLEM**
   M3 Altı son örneğin kaynak payları %99.1769–%99.8870, süreleri 21.7432–30.0943 saniyedir; hepsi değişmeyen %99 denetim sınırını geçti. C'de eklenen altıncı örnek 23.0091 saniye ve %99.8870 kaynak payına sahiptir.
   M4 İlk beş profilin vektörleri, isimleri, örnek kayıtları ve fiziksel dosyaları hem yeniden başlatmadan sonra hem B/D/C tamamlandıktan sonra gerçek B-öncesi görüntüyle birebir aynı kaldı; yeni ses örneği veya sessiz profil genişlemesi oluşmadı.
   M5 Bu dar L2 kanıtı [Decision 23 otomatik sözleşmeleri ve sabit yeniden oynatmasının](native-exclusions-report.md) ardından gerçek boş galeri akışını doğrular; dört ses kaydı, etkin eşikler, üretim kaynakları ve model seçimi koşum sırasında değiştirilmedi.
   **AÇIK**
   M6 Birleştirilmiş İngilizce sesli kitap kaynakları, temsil edici Türkçe toplantı veya elli kişilik doğruluk kanıtı değildir. Kaynak karelerinin sahipliği konuşma içi sessizlikleri de kapsar; elle etiketlenmiş ses saflığı, konuşmacı hata oranı, sözcük hata oranı veya kimlik F1 skoru olarak yorumlanamaz.
   M7 Tam kalite kapısı, güvenlik taramaları, tarayıcı, Apple ve Spark donanımı bu koşumda tekrar çalıştırılmadı; ayrı ana teslim kanıtlarına bağlıdır. Kullanıcı kabulü L3 iddiası yoktur.
   **YAN-ETKİ**
   M8 Mevcut seed ve çalışma wrapper'larıyla bir sıradan kullanıcı/tenant, dört yükleme ve altı profil oluşturuldu; backend/worker bir kez yeniden başlatıldı. Üretim kaynağı değiştirilmedi, başarısız durumu silen yeni galeri denemesi yapılmadı; yalnız özel ham kanıtlar ve kimlik/ses/metin/vektör içermeyen bu rapor/özet yazıldı.
