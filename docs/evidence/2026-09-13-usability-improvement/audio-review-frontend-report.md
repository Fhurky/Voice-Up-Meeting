# Koşum raporu — 2026-09-13 · Toplantı kaynak sesi inceleme ön yüzü

1. Sonuç: Dar davranış/regresyon paketi, lint ve üretim derlemesi geçti — birim 64 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows → Git Bash → Docker frontend; sabit profil `kt-vibecoding-python-web-v2`. Komut öneki `scripts/stack.sh exec -T frontend`.

   | Koşum | Komut/kapsam | Gözlenen sonuç |
   |---|---|---|
   | İlk kırmızı istemci/oynatıcı | `npm test -- src/lib/apiBlob.test.ts src/components/MeetingAudioReview.test.tsx` | 0 başarılı, 9 başarısız; oynatıcı modülü olmadığı için 1 paket yüklenemedi; çıkış 1 |
   | Sonuç bütünleşmesi kırmızı | `npm test -- src/components/MeetingResults.test.tsx` | 7 başarılı, 2 başarısız; eksik dinleme düğmesi/gerekçe; çıkış 1 |
   | İlk birleşik koşum | İstemci, oynatıcı, sonuç, servis ve katalogdan 6 dosya | 31 başarılı, 4 başarısız; katalog asenkron yükleme bekleyişi ve mevcut `Tekrar dene` etiketi testte düzeltildi |
   | İlk yeşil koşum | Aynı 6 dosya, servis sözleşmesi eklendi | 36 başarılı, çıkış 0; ESLint başarılı |
   | Kapsam/geri sayfalama kırmızı | `MeetingResults.test.tsx` | 8 başarılı, 2 başarısız; geri dönünce eski ses açıldı ve toplantı değişiminde eski metin kaldı |
   | Kapsam düzeltmesi | Aynı 6 dosya | 37 başarılı, çıkış 0 |
   | İlk üretim derlemesi | `npm run build` | Çıkış 1; exporter operation ID'lerini kaldırdığından `operations` sorgu tipi `never` oldu |
   | Üretilmiş sözleşmeye uyum | Yeni sorgu tipi üretilmiş `paths` alanından seçildi, `npm run build` | TypeScript ve Vite başarılı, çıkış 0; üretilmiş dosya elle değiştirilmedi |
   | Son birleşik paket | `npm test -- src/lib/apiBlob.test.ts src/lib/apiClient.test.ts src/components/MeetingAudioReview.test.tsx src/components/MeetingResults.test.tsx src/services/meetings.test.ts src/locales/catalogues.test.ts src/pages/MeetingPage.test.tsx src/components/MeetingUploadForm.test.tsx src/components/MeetingSourceUpload.test.tsx src/components/MeetingMicrophoneRecorder.test.tsx` | 64/64 başarılı, çıkış 0 |
   | Son statik/üretim | `npm run lint`, `npm run build` | İkisi de çıkış 0; TypeScript ve Vite başarılı |
   | Kalıcı senaryo sözdizimi | `node --check e2e/speaker-identity/09-meeting-audio-review.mjs` | Çıkış 0; canlı tarayıcı başarısı değildir |

   Son paket: `apiBlob` 11, `apiClient` 4, `MeetingAudioReview` 9,
   `MeetingResults` 10, toplantı servisi 6, katalog 1, toplantı sayfası 6,
   yükleme formu 6, kaynak yükleme 2 ve mikrofon bileşeni 9 test.
   Ara koşumlar aynı testlerin tekrarlarını içerir; 64'e eklenmez.

3. Maddeler:

   **KUSUR**

   M1 Eksik yetkili binary istemci ve ses inceleme bileşeni eklendi; içerik türü/boyut, stream taşması/iptali, gerçek bearer 401 ve ilgisiz 401 sınırları `apiBlob.test.ts` ile korunuyor.

   M2 Sayfalayıp geri dönünce eski seçim yeniden açılıyordu; sayfa eylemi seçimi temizler. Toplantı/kullanıcı/tenant değişiminde sonuç içeriği yeniden kurulup eski ses ve metin kaldırılır; iki kırmızı regresyon yeşile döndü.

   M3 `reason` bilgisi gösterilmiyordu; bilinen kodlar TR/EN açıklamaya çevrildi, bilinmeyen kod basılmaz. Ad değişiminin kimlik atamasını düzeltmediği açıklaması sonuç testleriyle korunur.

   **TUZAK**

   M4 OpenAPI exporter operation ID'lerini kanonik çıktıya almaz; sorgu tipi `paths[...][get][parameters][query]` üzerinden üretilir. Export/tip üretimini kök çalışma yürüttü.

   M5 Ses elle oynatılır; native denetimlerin varlığı test edildi, otomatik oynatma veya fiziksel hoparlör çıktısı varsayılmadı. Birim testinde WAV indirme ve tarayıcı oynatıcı sınırı simüledir.

   **GÖZLEM**

   M6 Önizleme 30 saniye/11.520.128 baytla sınırlıdır; aynı anda bir Blob, hızlı seçimde eski yanıtı ret, unmount/çıkış/sayfalama temizliği, uzun satır bölümleme ve kaynak sonuna sıkıştırma doğrulandı.

   M7 Mevcut dosya aktarımı, mikrofon bileşeni, ad/sürüm çatışması, profil yazma yetkisi ve TR/EN katalogları son regresyon paketinde korunuyor; yeni model çalıştırılmadı.

   **AÇIK**

   M8 Bu dar rapor L1 otomatik kanıttır; gerçek ters proxy/browser, fiziksel ses, tam profil ve güvenlik kapısı ayrı kök raporunda değerlendirilir. Kayıtlı yeni senaryo burada çalıştırılmadı.

   **YAN-ETKİ**

   M9 Ortak API istemcisi, toplantı servisi/sonuç/oynatıcı, testler, TR/EN katalogları ve küçük ortak stil uzantısı değişti; önceden var olan UI/mikrofon değişiklikleri korundu.

   M10 Kalıcı 09 senaryosu, kalite manifesti/alan koşucusu ve iki dilde ses inceleme rehberi eklendi; bu alt görev veritabanı, kaynak ses, model, şema veya kimlik eşiklerini değiştirmedi.
