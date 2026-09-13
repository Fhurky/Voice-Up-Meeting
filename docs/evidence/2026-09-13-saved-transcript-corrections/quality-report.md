# Koşum raporu — 2026-09-13 · Son tam profil kapısı ve yerel çalışma durumu

1. Sonuç: Son tam kalite kapısı 1.084 testle geçti; güvenlik tarayıcısı eksik araç nedeniyle çalışmadı — birim 777 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`; Windows PowerShell/Git Bash üzerinden mevcut Docker Python 3.13, PostgreSQL 17 ve React/Vite yığını.

   | Komut / kapsam | Gözlenen sonuç |
   |---|---|
   | `scripts/quality-gate.sh all` | Çıkış 0; bütün `KT_GATE_STEP` kayıtları başarılı. |
   | Bağımlılık kabulü ve ayar eşleme | 211 koordinat kabul kaydı güncel; 43 typed ayar, 40 Compose anahtarı, 41 örnek atama ve bir Kubernetes Secret referansı doğrulandı. |
   | Arka uç statik | Ruff, Black, isort ve mypy başarılı; 149 Python dosyası biçimi, 93 uygulama dosyası tipi. |
   | Arka uç pytest | 877 başarılı, 0 başarısız, 0 atlanan; 199,63 saniye. JUnit sınıf yollarıyla 570 birim + 307 gerçek PostgreSQL entegrasyonu doğrulandı. |
   | Şema | Kapıya özel benzersiz `_test` veritabanına migration uygulandı; head `8283cb0d9e4b`, yeni yükseltme işlemi yok; sonunda `DROP DATABASE` başarılı. |
   | OpenAPI ve üretilmiş tipler | Çevrimdışı sözleşme ve frontend tip drift kontrolleri başarılı. |
   | Arayüz | ESLint, typecheck ve üretim derlemesi başarılı; 27 test dosyasında 207 başarılı, 0 atlanan. |
   | Yönetişim ve chart | 93 yönetişim dosyası + dört etkin olmayan projeksiyon güncel; normal 46 ve toplantı 47 kaynak, ikişer overlay ile render edildi. |
   | `scripts/security-gate.sh` | Çıkış 2: `required offline security tool is unavailable: gitleaks`. |
   | Son yerel API | Arka uç yeniden başlatıldı; nginx doğrulama/reload başarılı. `GET /api/voiceup/v1/readiness` HTTP 200, `status: ready`. |

   Birim 777, arka uç 570 ile arayüz 207'nin toplamıdır; PostgreSQL 307
   ayrıca sayılır ve 1.084 toplamına dahildir. Dar koşumlar tekrar eklenmez.
   Ham kapı ve güvenlik çıktıları Git dışı yerel
   `outputs/2026-09-13-saved-transcript-corrections/quality-gate.log` ve
   `security-gate.log` dosyalarındadır. Test atlaması yoktur; çalışamayan
   güvenlik tarayıcısı test başarısı veya test atlaması olarak sayılmadı.

3. Maddeler:

   **KUSUR** — yok

   **TUZAK**
   M1 Tam kapı yalnız kendisinin oluşturduğu test veritabanına yazdı; uygulama veritabanındaki eklemeli migration [ayrı backend koşumunda](backend.md) uygulanmıştı.

   **GÖZLEM**
   M2 Kaynak sırası ve Unicode kusurları düzeltildikten sonraki üretim kodu bu son kapıda test edildi; başlatılmış uygulama aynı dosyaları yeniden yükledi.
   M3 Gerçek model, normal kullanıcı HTTP ve TR/EN tarayıcı davranışı ayrı raporlarda gözlendi; otomatik test sayısı dil modeli doğruluğu sayılmaz.

   **AÇIK**
   M4 `gitleaks` olmadığı için güvenlik kapısı ilk araç kontrolünde durdu; Semgrep/Trivy ve kabul edilmiş çevrimdışı materyaller doğrulanmadı. Tam güvenlik taraması geçti denemez.
   M5 Native Apple, Spark ve canlı Kubernetes ortamı bu sürüm için sınanmadı; chart render geçişi bu ortamlarda çalışma kanıtı değildir.

   **YAN-ETKİ**
   M6 Kapıya ait test veritabanı oluşturulup düşürüldü; yerel backend/nginx yenilendi. Sürüm pinleri, bağımlılık/image kabulü, model kurulumu ve ağ erişim izinleri değişmedi.
