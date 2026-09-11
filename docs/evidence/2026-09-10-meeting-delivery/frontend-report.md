# Koşum raporu — 2026-09-11 · Toplantı yükleme ve konuşmacılı metin arayüzü.

1. Sonuç: Ön yüz kalite kapısı ve gerçek yükleme tarayıcı senaryosu geçti — birim 87 başarılı / tarayıcı 1 başarılı / atlanan 1; karar bekleyen: yok. Yükleme/izin yaşam döngüsünde L2; model metni ve hafıza kabulünde henüz L2 yok.
2. Koşulan: `kt-vibecoding-python-web-v2`; Windows Docker Compose, mevcut Node 22.23.2 ön yüz konteyneri ve gerçek üretilmiş OpenAPI tipleri.

   | Komut / aşama | Sonuç |
   | --- | --- |
   | `scripts/stack.sh exec -T frontend sh -lc 'npm test -- src/services/meetings.test.ts src/services/meetingUpload.test.ts'` | Önce iki eksik modül nedeniyle iki paket yükleme hatası; uygulama sonrası 10/10 başarılı. |
   | Yeni yerelleştirme/form/sonuç testleri | İlk aşamada iki eksik bileşen ve bir eksik yerelleştirme davranışı; uygulama sonrası 7/7 başarılı. |
   | Kaynak yaşam döngüsü, toplantı sayfası ve sınır testleri | 10/10 başarılı. |
   | `scripts/quality-gate.sh frontend` | İlk koşum 86/86; ad çakışması regresyonundan sonraki son koşumda yapılandırma, bağımlılık kabulü, lint, tip, üretim derlemesi, 20 dosyada 87 test ve üretilmiş tip drift kontrolü başarılı; çıkış 0. |
   | `npm test -- src/components/MeetingResults.test.tsx` | Ad çakışmasında yenileme için önce 3 başarılı / 1 başarısız; düzeltmeden sonra 4/4 başarılı. |
   | İki yeni e2e dosyası için mevcut Node 22 ile `node --input-type=module --check` | İki sözdizimi kontrolü başarılı; tarayıcı yürütümü değildir. |
   | `scripts/e2e.sh speaker-identity` | Çıkış 1: `KT_SCAFFOLD_OFFLINE_BUNDLE must point to an admitted, platform-matched bundle`. |
   | CUA tarayıcı keşfi | Envanter `browsers: []`, `apps: []`; `getBrowser` sonucu `No browser is available`. |
   | Sabit sürümlü yerel Node ile `node e2e/speaker-identity/04-meeting-upload.mjs` | Windows Node 22.23.2, Playwright 1.62.1, Chromium Headless Shell rev1234; gerçek 8081 uygulaması ve PostgreSQL ile 1/1 başarılı, çıkış 0. |

3. Maddeler:

   **KUSUR**
   M1 OpenAPI dışa aktarıcı iş alanı olan `title` özelliğini siliyordu; ana ajan kaynağı iki regresyon testiyle düzeltti ve sözleşmeleri yeniden üretti. Üretilmiş ön yüz dosyası elle yamalanmadı.
   M2 İlk UI geçişinde form ve ad alanı aynı erişilebilir adı taşıyordu; form adı ayrıldı. React effect/ref lint bulguları olay tabanlı yükleme durumları ve yaşam döngüsü temizliğiyle giderildi.
   M3 Ad çakışması sonrasında eski sürümlü düzenleyici açık kalıyordu; mevcut sonucu yenileyip yeniden düzenleme eklendi. `MeetingResults.test.tsx` güncel sürümün gönderildiğini korur.
   **TUZAK**
   M4 Kaynak dosya yalnız React bağlamında File referansı olarak taşınır; sayfa yenilendiğinde dosya yeniden seçilir. Kaydedilmiş parçalar SHA-256 ile karşılaştırılır; yüklenmemiş son bölümün önceki dosyayla aynı olduğu kanıtlanmaz.
   M5 İlk canlı koşum eski Vite rota modülüne ulaştı; yalnız ön yüz yeniden başlatıldı. Sonraki koşumda bozuk WAV başlığı olan fixture için gerçek `unsupported_audio` yanıtı gözlendi; senaryonun yanlış `invalid_audio` beklentisi düzeltildi.
   M6 Genel e2e wrapper hâlâ kabul edilmiş platform eşleşen offline bundle ister. Geçen alternatif koşum, resmi SHA/SRI ile doğrulanan sabit Node/npm dosyaları ve Playwright'ın kendi tarayıcı indirmesiyle açıkça yetkilendirilmiş yerel hazırlıktır; admitted bundle kanıtı olarak sunulmaz.
   **GÖZLEM**
   M7 Birim testleri 4 MiB sınırlı okuma, onaylanmış byte ilerlemesi, yanlış kaynak/onay reddi, iptal, Strict Mode, idempotent oluşturma, sayı girdileri, izinler, ad sürümü, düz metin, sayfalama ve iki dili kapsar; model doğruluğu ölçmez.
   M8 Canlı tarayıcı iki dilde normal writer/reader girişi, sayı doğrulama, yükleme, hashli devam, yanlış kaynak reddi, yenileme, iptal/silme ve gerçek 403/404 kontrolünü geçti; yanıt veya model çıktısı taklit edilmedi.
   **AÇIK**
   M9 Kayıtlı `05-meeting-memory.mjs` gerçek model/worker hazır olmasını bekliyor; konuşmacılı metin, elle ad verme ve 5→5→5→6 hafıza tarayıcı kabulü açık kalır. İnsan erişilebilirlik kabulü ve 50 kişilik doğal Türkçe toplantı doğruluğu ölçülmedi.
   M10 Tam `scripts/quality-gate.sh all` ve güvenlik taramaları bu ön yüz koşumunda çalıştırılmadı; bütünleşik teslimin ayrı kanıtıdır.
   **YAN-ETKİ**
   M11 Yükleme/listeler/sonuçlar/isim düzenleme, yerelleştirme, yönlendirme, gezinme, testler ve iki kayıtlı senaryo eklendi; paket veya tarayıcı pini değiştirilmedi.
   M12 Yerel veritabanında yalnız toplantı testi için iki yeni tenant ve üç sıradan hesap oluşturuldu. Geçen senaryo kendi toplantılarını public API ile sildi; mevcut kişi profilleri değiştirilmedi. Kimlik bilgileri Git dışında tutulur.
   M13 Sabit tarayıcı araçları, hazırlık hash/SRI kanıtı, `frontend-tests.json` ve `04-meeting-upload-browser.txt`, Git dışı `outputs/2026-09-10-meeting-delivery/` dizinine yazıldı; eski sürümler kullanılmadı.
