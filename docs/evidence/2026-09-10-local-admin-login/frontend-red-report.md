# Koşum raporu — 2026-09-10 · Yerel yönetici girişi ön yüz RED doğrulaması

1. Sonuç: Eksik yerel yönetici akışı ve çıkış sonrası eski yanıt yarışı 14 başarısız testle yakalandı — birim 7 başarılı / tarayıcı 0 başarılı / atlanan 1; karar bekleyen: yok.
2. Koşulan: Windows üzerinde native Git Bash ve mevcut `scripts/stack.sh exec -T frontend` sarmalayıcısı; Docker frontend, Vitest 4.1.10, `kt-vibecoding-python-web-v2`.

   | Paket / dosya | Başarılı | Başarısız |
   |---|---:|---:|
   | `src/pages/LoginPage.test.tsx` | 4 | 8 |
   | `src/services/auth.test.ts` | 0 | 3 |
   | `src/contexts/AuthContext.test.tsx` | 3 | 3 |

   Komut: `scripts/stack.sh exec -T frontend npm test -- src/pages/LoginPage.test.tsx src/services/auth.test.ts src/contexts/AuthContext.test.tsx --reporter=default --reporter=json --outputFile.json /tmp/local-admin-red.json`; exit 1. Ham kayıt: [frontend-red.json](frontend-red.json).
3. Maddeler:

   **KUSUR**

   M1 Düğme, options servisi ve context yerel giriş işlevi eksik olduğundan yeni akış testleri başarısızdı; düzeltme ve GREEN kanıtı [frontend-report.md](frontend-report.md).
   M2 Geciken `/me` yanıtı çıkıştan sonra kullanıcıyı geri yüklüyordu; `AuthContext.test.tsx` bu gözlenebilir oturum yarışını yakaladı.

   **TUZAK**

   M3 Bu tarihsel RED çıktısında eksik `loginAsAdmin` nedeniyle React olay hataları da bulunur; başarılı görünen gecikmiş-admin testi son sürümde isteğin başladığını ayrıca doğrular.

   **GÖZLEM**

   M4 Normal parola girişi, options bekleme/başarısızlık durumunda kullanılabilirlik ve geçici `/me` hatasında oturumu koruma beklentileri değiştirilmedi.

   **AÇIK**

   M5 Kalıcı tarayıcı senaryosu bu RED koşusunda çalıştırılmadı; gerçek HTTP/tarayıcı ve tam kalite kapısı ana görev tarafından ayrı doğrulanır.

   **YAN-ETKİ**

   M6 Üç test dosyası ve bu koşumun JSON/rapor kanıtı yazıldı; uygulama hesabı, parola, tenant veya ses verisi değiştirilmedi.
