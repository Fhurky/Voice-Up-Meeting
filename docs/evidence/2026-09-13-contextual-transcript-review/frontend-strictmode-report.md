# Koşum raporu — 2026-09-13 · Geliştirme modunda tek model isteği

1. Sonuç: StrictMode altında yinelenen başlangıç isteği giderildi — birim 45 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows üzerinden mevcut Linux frontend konteyneri; `scripts/stack.sh exec -T frontend` ile aşağıdaki komutlar çalıştı. Profil `kt-vibecoding-python-web-v2`.

   | Komut / dosya | Gözlenen sonuç |
   |---|---|
   | `npm test -- src/components/MeetingTextReview.test.tsx` | Önce 20 başarılı / 1 başarısız; [kırmızı kanıt](frontend-strictmode-red.md) |
   | `npm test -- src/components/MeetingTextReview.test.tsx src/components/MeetingResults.test.tsx src/services/meetings.test.ts` | 45 başarılı; çıkış 0 |
   | `MeetingTextReview.test.tsx` | 22 başarılı; gerçek StrictMode başlangıcı ve kullanıcı retry çağrı sayısı dahil |
   | `MeetingResults.test.tsx` | 16 başarılı |
   | `services/meetings.test.ts` | 7 başarılı |
   | `npm run lint` | Başarılı; çıkış 0 |
   | `npm run build` | TypeScript kontrolü ve üretim derlemesi başarılı; çıkış 0 |

3. Maddeler:

   **KUSUR**
   M1 Effect başlamasındaki POST bir microtask ertelendi; bu sırada iptal edilmiş setup sunucuya istek göndermiyor (`MeetingTextReview.tsx`, StrictMode regresyonu).

   **TUZAK**
   M2 Bu düzeltme sunucuya ulaşmış pahalı bir işi geri almaz; gerçek HTTP bağlantısı sonradan kesilirse backend işleminin kendi süre sınırı geçerlidir.

   **GÖZLEM**
   M3 StrictMode açık kaldı; ilk seçimin tek çağrısı ve açık retry eyleminin tek ek çağrısı gözlendi. Yeni seçim, eski yanıt, kaynak hash'i ve kapanış iptali testleri yeşil.

   **AÇIK**
   M4 Gerçek model/tarayıcı HTTP çağrı sayısı ve ters proxy zaman aşımı ayrı canlı koşumda doğrulanmalı; bu dar suite bunların kanıtı değildir.

   **YAN-ETKİ**
   M5 Yalnız `MeetingTextReview.tsx` ve testi değişti; üretim build çıktısı yeniden üretildi. Önbellek, model, veri veya StrictMode yapılandırması değiştirilmedi.
