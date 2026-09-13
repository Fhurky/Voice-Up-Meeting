# Koşum raporu — 2026-09-13 · Bağlamsal metin incelemesi arayüzünün dar doğrulaması

1. Sonuç: Dar arayüz testleri, üretilmiş sözleşmeyle typecheck/build ve statik kontroller geçti — birim 53 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows ana makine, mevcut Linux frontend konteyneri, `kt-vibecoding-python-web-v2`; test/lint mevcut `scripts/stack.sh exec -T frontend` üzerinden çalıştı.

   | Komut / dosya | Gözlenen sonuç |
   |---|---|
   | `npm test -- src/services/meetings.test.ts src/components/MeetingResults.test.tsx src/components/MeetingTextReview.test.tsx src/components/MeetingAudioReview.test.tsx src/locales/catalogues.test.ts` | 53/53; çıkış 0 |
   | `MeetingTextReview.test.tsx` | 20 başarılı |
   | `MeetingResults.test.tsx` | 16 başarılı |
   | `services/meetings.test.ts` | 7 başarılı |
   | `MeetingAudioReview.test.tsx` | 9 başarılı |
   | `locales/catalogues.test.ts` | 1 başarılı |
   | `npm run lint` | Çıkış 0 |
   | `npm run build` | OpenAPI'den üretilmiş tiplerle TypeScript kontrolü ve Vite üretim derlemesi başarılı; çıkış 0 |
   | `node --check e2e/speaker-identity/10-contextual-transcript-review.mjs` | Çıkış 0; canlı tarayıcı değildir |

3. Maddeler:

   **KUSUR**
   M1 Eksik bağlamsal inceleme eylemi ve gövdesiz hizmet çağrısı düzeltildi; [ilk kırmızı koşum](frontend-red-report.md) ve yukarıdaki 53 başarılı kontrol kanıt.
   M2 [Ara koşum](frontend-intermediate-report.md) yeni testlerdeki katalog bekleme ve retry etiket varsayımları düzeltildi; uygulama kontrolü zayıflatılmadı.

   **TUZAK**
   M3 Unicode ofsetleri kod noktasıdır; emoji öncesi kayma testi ve yeniden kurulan öneri metni kontrolü bunu korur.
   M4 Panel yeni sayfa/seçim/kullanıcı durumunda iptal edilir; geç cevap ve yeniden açılma testleri önceki öneriyi taşımayı engeller.

   **GÖZLEM**
   M5 Kaynak kimliği/orijinal metin/SHA256 eşitliği, düz HTML metni, izinler, tamamlanmış durum, yerelleştirilmiş hatalar ve 011 ses oynatıcı regresyonları gözlendi.

   **AÇIK**
   M6 Tam profil kapısı ve gerçek tarayıcı/model bu dar rapora dahil değildir; ortak teslimde ayrıca yürütülmelidir.
   M7 Senaryo kaydı gerçek koşum veya model doğruluğu kanıtı değildir; gerçek arayüz incelemesi iki dilde ayrı kaydedilmelidir.

   **YAN-ETKİ**
   M8 FE hizmet/panel/test/katalog ve küçük semantik stil eklendi; e2e10 kaydı ve TR/EN kullanım belgeleri oluşturuldu. Model, veritabanı, ham metin ve ses değişmedi.
