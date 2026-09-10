# Koşum raporu — 2026-09-10 · Konuşmacı kapasitesi ön yüz otomasyonu ve senaryo doğrulaması.

1. Sonuç: Ön yüz otomasyonu yeşil; bu alt kapsamda L1 gözlendi — birim 37 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Sabit profil `kt-vibecoding-python-web-v2`; yerel Windows Git Bash üzerinden `scripts/stack.sh exec -T frontend` ile çalışan Linux frontend konteyneri. Aşağıdaki npm komutlarının tamamı bu mevcut sarmalayıcıdan çağrıldı.

   | Komut / kapsam | Gözlenen sonuç |
   |---|---|
   | `npm test -- src/pages/SpeakerProfilesPage.test.tsx src/pages/SpeakerJobPage.test.tsx src/components/AudioJobForm.test.tsx src/lib/speakerErrors.test.ts --reporter=dot` | İlk yeşil koşum: 22 başarılı, 0 başarısız, 0 atlanan; çıkış 0. |
   | `npm run typecheck` | Çıkış 0. |
   | `npm test -- src/pages/SpeakerProfilesPage.test.tsx src/components/AudioJobForm.test.tsx --reporter=dot` | Ek sınır denetimi: 19 başarılı, 1 başarısız, 0 atlanan; çıkış 1. Test ortamındaki dosya geçerlilik davranışı nedeniyle gönderim olayı düzeltilip aşağıdaki tam pakette tekrar doğrulandı. |
   | `npm test -- --reporter=dot` | Son tam ön yüz paketi: 10 dosyada 37 başarılı, 0 başarısız, 0 atlanan; çıkış 0. |
   | `npm run lint`, ardından `npm run build` | İkisi de çıkış 0; üretim derlemesi tür denetimini içerir, 97 modül derlendi. |
   | Windows `node --check e2e/speaker-identity/03-profile-capacity.mjs` | Çıkış 0; yalnız sözdizimi kanıtıdır. |
   | Değişen ön yüz ve senaryo yollarında `git diff --check` | Çıkış 0. |

3. Maddeler:

   **KUSUR**
   M1 Kapasite gösterimi ve yeni profil engeli uygulandı; `SpeakerProfilesPage.test.tsx` 49/50/51, sayfalı toplam, yüklenme/hata, silme sonrası yenileme, eski toplamla gelen HTTP reddi ve sınırda örnek eklemeyi korur (DÜZELTİLDİ).
   M2 `profile_limit`, ortak hata eşlemesine ve iki dilde kataloğa eklendi; form ve terminal iş hata gösterimi ham sunucu metni göstermeden doğrulandı (DÜZELTİLDİ, `speakerErrors.test.ts`, `AudioJobForm.test.tsx`, `SpeakerJobPage.test.tsx`).
   **TUZAK**
   M3 Test dosya seçimini `fireEvent.change` ile taklit ettiğinden yerel HTML dosya geçerliliği bir düğme tıklamasının gönderimini durdurdu; koruyucu test mevcut takımın `fireEvent.submit` düzenine alındı ve son pakette geçti.
   M4 `03-profile-capacity.mjs`, ayrı sıradan yazma hesabı, 50 test profili ve son işler sayfasındaki mevcut `failed/profile_limit` işi ister; sağlanan fikstürleri yalnız okur. Bu koşumda çalıştırılmadı.
   **GÖZLEM**
   M5 Son pakette 16 yeni kapasite testi ve 21 önceki test başarılıdır; tekrar koşumları yeni bağımsız test sayısına eklenmedi. Kırmızı kanıt `frontend-capacity-red-report.md` içinde korunur.
   M6 Sınır API yanıtındaki `total`/`max_profiles` ile gösterilir; mevcut profile örnek ekleme kapasite yüklemesinden bağımsız kalır. Sunucu isteği reddettiğinde liste yenilenir; sunucu yetkisi değişmez.
   **AÇIK**
   M7 Gerçek tarayıcı, tam profil kapısı ve güvenlik giriş noktaları bu alt koşumda çalıştırılmadı; kök görev bunların canlı ortam ve toplam teslim kanıtını ayrı kaydeder. Bu rapor L2/L3 veya model doğruluğu artışı iddia etmez.
   **YAN-ETKİ**
   M8 Ön yüz sayfası/formu/hata eşlemesi, Türkçe/İngilizce kataloglar ve koruyucu testler güncellendi; kapasite senaryosu ortak çalıştırıcıya ve `e2e/QUALITY_MANIFEST.md` tablosuna kaydedildi.
   M9 Mevcut npm derlemesi frontend konteynerinin üretim çıktılarını yeniden üretti. Bu alt koşum kullanıcı profili, ses kaydı veya veritabanı fikstürü oluşturmadı/silmedi; önceki kanıt dosyaları değişmedi.
