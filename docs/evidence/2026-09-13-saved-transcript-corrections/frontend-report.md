# Koşum raporu — 2026-09-13 · Model seçimi ve kayıtlı metin arayüzünün otomatik doğrulaması

1. Sonuç: Üretilmiş sözleşmeyle arayüz doğrulaması geçti, canlı doğrulama bu koşuma dahil değil — birim 207 başarılı / tarayıcı 0 başarılı / atlanan 2; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`, Windows çalışma alanının Linux frontend konteyneri; komut öneki `scripts/stack.sh exec -T frontend`.

   | Komut / kapsam | Gözlenen sonuç |
   |---|---|
   | `npm test -- src/services/meetings.test.ts src/components/MeetingTextReview.test.tsx src/components/MeetingResults.test.tsx src/components/CorrectedTranscriptText.test.tsx src/components/MeetingAudioReview.test.tsx src/locales/catalogues.test.ts` | 6 dosya, 75 başarılı, çıkış 0 |
   | `npm test` | 27 dosya, 207 başarılı, çıkış 0 |
   | `npm run lint` | ESLint başarılı, çıkış 0 |
   | İlk `npm run build` | TS2769: testlerde `ByRoleOptions` için desteklenmeyen `exact`; çıkış 1 |
   | Düzeltme sonrası `npm run build` | Typecheck ve Vite üretim derlemesi başarılı, çıkış 0 |
   | Düzeltme sonrası `npm test -- src/components/MeetingTextReview.test.tsx src/components/MeetingResults.test.tsx src/components/CorrectedTranscriptText.test.tsx` | 3 dosya, 55 başarılı, çıkış 0 |
   | Windows `node --check`: `10-contextual-transcript-review.mjs`, `11-saved-transcript-corrections.mjs`, `text-review-support.mjs`, `run-all.mjs` | Dört sözdizimi kontrolü başarılı; tarayıcı çalıştırılmadı |
   | `git diff --check` — değişen frontend, rehber, senaryo ve bu kanıt dizini | Boşluk hatası yok, çıkış 0 |

3. Maddeler:

   **KUSUR**
   M1 İlk derlemede test seçicilerine yanlışlıkla Playwright'ın `exact` seçeneği taşınmıştı; Testing Library string adı zaten tam eşler, geçersiz seçenek kaldırıldı ve build/55 test geçti (DÜZELTİLDİ).

   **TUZAK**
   M2 Kaydetme düğmesi yalnız sunucu kanıtıyla görünür; ağ hatasında aynı kanıtla tekrar, süre/sürüm çatışmasında yeni inceleme gerekir. Model değiştirmek eski kanıtı kaldırır.
   M3 Senaryo 11 yalnız açık doğrulama değişkeni ve `e2e-text-correction-` başlıklı silinebilir test toplantısıyla çalışır; gerçek model önerisi gerekir ve `finally` public API ile bu toplantıyı siler.

   **GÖZLEM**
   M4 Kaynak SHA256, Unicode ofsetleri, model/sürüm, StrictMode, eski yanıt iptali, HTML'nin düz metin kalması, anlamsal önerilerin görünürlüğü ve tek kaydetme/tekrar sözleşmesi 75 dar test içinde gözlendi.
   M5 Okuyucunun kayıtlı yeşil sürümü görmesi, özgün görünüm ve yeni bileşen açılışında kayıtlı sürümün geri gelmesi otomatik sınandı; önceki 011 ses oynatma testleri korundu.

   **AÇIK**
   M6 Kalıcı tarayıcı senaryoları 10 ve 11 burada çalıştırılmadı; gerçek model/tarayıcı ve tam profil kapısı kök ajanın ayrı koşumudur. Bu rapor L2 veya model doğruluğu iddiası taşımaz.

   **YAN-ETKİ**
   M7 Arayüz, TR/EN metinleri, hizmet testleri, iki kullanıcı rehberi ve tarayıcı senaryoları güncellendi; bu koşumda model çağrısı, kullanıcı verisi değişikliği veya Git işlemi yapılmadı.
