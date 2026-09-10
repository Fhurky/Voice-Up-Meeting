# Koşum raporu — 2026-09-10 · Profil kotası kaldırıldıktan sonra ön yüz doğrulaması.

1. Sonuç: Ön yüz otomasyonu yeşil; bu alt kapsamda L1 gözlendi — birim 39 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Sabit `kt-vibecoding-python-web-v2` profili; yerel Windows Git Bash üzerinden mevcut `scripts/stack.sh exec -T frontend` sarmalayıcısıyla çalışan Linux frontend konteyneri.

   | Komut / kapsam | Gözlenen sonuç |
   |---|---|
   | `npm test -- src/pages/SpeakerProfilesPage.test.tsx src/pages/SpeakerJobPage.test.tsx src/components/AudioJobForm.test.tsx src/lib/speakerErrors.test.ts --reporter=dot` | 4 dosyada 27 başarılı, 0 başarısız, 0 atlanan; çıkış 0. |
   | `npm test -- --reporter=dot` | Son tam ön yüz paketi: 10 dosyada 39 başarılı, 0 başarısız, 0 atlanan; çıkış 0. |
   | `npm run lint`, ardından `npm run build` | İkisi de çıkış 0; üretim derlemesindeki tür denetimi geçti, 97 modül derlendi. |
   | Windows `node --check e2e/speaker-identity/03-profile-capacity.mjs` ve değişen ön yüz/senaryo yollarında `git diff --check` | Hata çıktısı yok; senaryo denetimi yalnız sözdizimi kanıtıdır. |
   | Ön yüz kaynaklarında `max_profiles`, `newProfileBlocked`, `onCapacityChange`, `speaker.profiles.capacity` araması | Eşleşme yok; `rg` eşleşme bulunmadığı için çıkış 1 döndürdü. |

3. Maddeler:

   **KUSUR**
   M1 Yeni kayıt formunu profil sayısına veya liste yüklenme/hatasına bağlayan kapasite state'i ve form parametreleri kaldırıldı (DÜZELTİLDİ, `SpeakerProfilesPage.tsx`, `AudioJobForm.tsx`).
   M2 Eski kapasite hata metni geçmiş kuralı anlatacak şekilde iki dilde güncellendi; geçmiş iş sonucu ve hata kodu değişmez (DÜZELTİLDİ, `tr.json`, `en.json`, `SpeakerJobPage.test.tsx`).
   **TUZAK**
   M3 `max_profiles` alanı sözleşmeden kaldırıldığından backend ve ön yüz birlikte güncellenip açık tarayıcı sayfası yenilenmeli; dış istemci sürüm uyumu iddia edilmez.
   M4 `03-profile-capacity.mjs` dosya ve fikstür değişken adları korunur; senaryo artık Decision 11'in kotasız formunu ve tarihsel hatayı doğrular. Çalıştırma için ayrı tenant'ta en az 50 test profili ve son işler sayfasında bir eski `profile_limit` işi gerekir.
   **GÖZLEM**
   M5 Testler 50/51/100/200/201 toplamlarında yeni iş isteğini, sayfalı toplamı, iki dilde yüklenme/hata sırasında form erişimini, silme/yenilemeyi, profil başına 20 örnek sınırını ve salt okunur izinleri korur.
   M6 Hedefli 27 test son 39 testin alt kümesidir; tekrarlar bağımsız test sayısına eklenmedi. Kırmızı kanıt bu dizindeki `frontend-red-report.md` dosyasındadır.
   **AÇIK**
   M7 Gerçek tarayıcı, tam profil kapısı ve güvenlik girişleri kök görev tarafından ayrı kaydedilir; bu alt koşumda çalıştırılmadı. 50/200 kişiyle gerçek tanıma veya doğruluk artışı iddiası yoktur.
   **YAN-ETKİ**
   M8 Kota arayüzü ve kullanılmayan katalog anahtarları kaldırıldı; testler, mevcut tarayıcı senaryosu, senaryo açıklaması ve kalite manifesti güncel karara uyarlandı. Mevcut derleme konteyner üretim çıktılarını yeniden üretti.
   M9 Kullanıcı profili, ses veya iş fikstürü oluşturulmadı/silinmedi; önceki kapasite kanıt dosyaları değiştirilmedi.
