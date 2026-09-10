# Koşum raporu — 2026-09-10 · Yerel yönetici girişi ön yüz ve kalıcı senaryo doğrulaması

1. Sonuç: Ön yüz testleri, tip/lint/üretim derlemesi ve senaryo sözdizimi başarılı; bu alt görevde en yüksek kanıt L1 — birim 59 başarılı / tarayıcı 0 başarılı / atlanan 1; karar bekleyen: yok.
2. Koşulan: Windows native Git Bash, mevcut `scripts/stack.sh exec -T frontend` sarmalayıcısı ve Docker frontend; profil `kt-vibecoding-python-web-v2`. Son dar koşum 21 testtir ve 59 testlik toplamın alt kümesidir.

   | Doğrulama | Sonuç / kanıt |
   |---|---|
   | RED, 3 dosya / 21 test | 7 başarılı, 14 başarısız; [RED raporu](frontend-red-report.md) |
   | İlk GREEN, aynı 3 dosya | 21 başarılı, 0 atlanan; [frontend-green.json](frontend-green.json) |
   | Tüm frontend, 12 dosya | 59 başarılı, 0 atlanan; [frontend-full.json](frontend-full.json) |
   | Son imzaları sınırlandırılmış UI/service/context testleri | 12 + 3 + 6 = 21 başarılı; [frontend-final.json](frontend-final.json) |
   | `npm run lint` | exit 0; son test düzenlemesinden sonra tekrar başarılı |
   | `npm run build` | exit 0, tip kontrolü ve Vite 8.2.0 üretim derlemesi başarılı |
   | Son `npm run typecheck` | exit 0 |
   | `node --check e2e/auth/02-local-admin-login.mjs`, harness, auth run-all | Üç komut exit 0; tarayıcı çalıştırılması değildir |
   | `git diff --check -- app/frontend/src e2e` | exit 0 |

   Test komutları `npm test -- --reporter=default --reporter=json --outputFile.json /tmp/local-admin-full.json` ve `npm test -- src/pages/LoginPage.test.tsx src/services/auth.test.ts src/contexts/AuthContext.test.tsx --reporter=default --reporter=json --outputFile.json /tmp/local-admin-final.json` olarak mevcut sarmalayıcıyla çalıştırıldı.
3. Maddeler:

   **KUSUR**

   M1 Yerel giriş ve seçenek akışı eklendi; TR/EN düğme, boş kimlik alanları, options kapalı/hatalı/bekliyor durumları, ortak busy ve 404/503 hataları testlerle korunuyor (DÜZELTİLDİ, `LoginPage.test.tsx`, `auth.test.ts`).
   M2 Çıkış sonrası geciken `/me` veya giriş yanıtı artık saklanan oturumu geri yükleyemiyor; iki yöntem aynı merkezi storage helperını kullanıyor (DÜZELTİLDİ, `AuthContext.test.tsx`).
   M3 İlk üretim derlemesi testte Testing Library için desteklenmeyen `exact` seçeneği nedeniyle `TS2769` verdi; varsayılan tam ad eşleşmesi korunarak seçenek kaldırıldı ve derleme geçti (DÜZELTİLDİ, `LoginPage.test.tsx`).

   **TUZAK**

   M4 Playwright düğme adı eşleşmesi kısmi olabilir; eski normal giriş senaryosu yeni “Sign in as admin” düğmesiyle çakışmaması için `exact: true` kullanır.
   M5 Yeni senaryo yerel geliştirme özelliği açık ve seçilebilir mevcut bir yönetici gerektirir; hesap hazırlamaz. Yenileme varsayılan Türkçe dili yüklediğinden İngilizce akış dili yeniden seçer.
   M6 Ham JSON test raporlarındaki token/parola metinleri yalnız sentetik birim testi değerleridir; gerçek oturum veya süreç sırrı kaydedilmedi.

   **GÖZLEM**

   M7 Mevcut tenant/RBAC, parola girişi, profil/örnek sınırları ve tarihsel hata regresyonları tüm 59 testte korundu; üretilmiş API tipi ana görev tarafından sarmalayıcıyla üretildi, elle değiştirilmedi.

   **AÇIK**

   M8 Kalıcı Playwright senaryosu bu alt görevde çalıştırılmadı; ana görev çalışan uygulamada gerçek tarayıcıyı ve tam `scripts/quality-gate.sh all` kapısını ayrı yürütür. Bu rapor L2 veya Mac ortamı kanıtı ileri sürmez.

   **YAN-ETKİ**

   M9 Auth service/context/storage, giriş sayfası, TR/EN kataloglar ve testler güncellendi; yeni e2e senaryosu mevcut auth çalıştırıcısı/manifest/harness içine kaydedildi.
   M10 Bu kanıtlar ve yerel üretim derleme çıktısı oluştu; paket/lock/dependency authority, uygulama verisi veya sır ayarı bu alt görevde değiştirilmedi.
