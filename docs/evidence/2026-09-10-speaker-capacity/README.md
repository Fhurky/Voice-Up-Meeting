# Koşum raporu — 2026-09-10 · Çalışma alanı başına en fazla 50 konuşmacı profili.

1. Sonuç: 50 aktif profil sınırı tüm etkilenen katmanlarda uygulandı — birim/entegrasyon 317 başarılı / tarayıcı 8 başarılı / atlanan 2 ortam kapısı; karar bekleyen: yok. Canlı kapasite davranışında L2 gözlendi; tam güvenlik kabulü ve temsilî ses verisiyle L3 açık kalır.
2. Koşulan: Sabit `kt-vibecoding-python-web-v2`, Windows Docker Compose uygulaması, ayrı PostgreSQL test veritabanları ve çevrimdışı Linux Python 3.13.14. [Accepted PRD Decision 10](../../../specs/speaker-identity/PRDs/001-local-speaker-pilot/PRD.md) uygulanmıştır.

   | Kapsam | Kanıt |
   | --- | --- |
   | Tam profil kalite kapısı | Backend 96 + frontend 37 = 133 başarılı; sıfır test atlandı. [Kapı raporu](quality-gate-report.md). |
   | Değerlendirme ve ölçüler | 77 koşucu + 94 metrik + 13 eski rapor testi = 184 başarılı. Aynı Windows tekrarları toplama eklenmedi. [Koşucu raporu](evaluator-run-report.md). |
   | Yarış ve iş kuralları | 49→50, 50/51 reddi, aynı anda son yer, yeniden deneme, örnek ekleme/tanıma, silme ve tenant/model kapsamı. [Backend raporu](backend-report.md). |
   | Arayüz | 16 yeni test dahil 37 başarılı; kapasite yüklenme/hata durumu, eski toplamla HTTP reddi, iki dil ve mevcut profile ekleme. [Ön yüz raporu](frontend-capacity-green-report.md). |
   | Canlı uygulama | 8 CUA kabul noktası, 6 gerçek HTTP kontrolü; ayrı sıradan hesap ve sentetik kapasite fikstürü. [Canlı rapor](live-browser-report.md). |
   | Son içerik doğrulaması | 46 yerel rapor bağlantısında eksik 0; özel canlı fikstür kimliği/parolası eşleşmesi 0; JUnit 184/0/0/0 sayımı doğrulandı. [Kaynak hashleri ve kontrol kaydı](source-manifest.json). |

3. Maddeler:

   **KUSUR**
   M1 Aynı anda gelen kayıtlar 50 sınırını aşabiliyordu; girişte ve tenant kilidi altında atomik işçi tamamlamasında yeniden sayım eklendi. Son yeri kaybeden iş `profile_limit` ile tek denemede sonlanır; fazladan profil/örnek yazılmaz (DÜZELTİLDİ).
   M2 Dolu galeride yeni kişi deneyi ana ölçümü kaybettiriyordu; yalnız tam `409/profile_limit` yeni kayıt reddi kalıcı başarısız işlem olarak tutulur, dönüş sorgusu ve son tutarlılık kontrolü devam eder (DÜZELTİLDİ).
   M3 Bağımsız inceleme komut satırı girişinin yeni HTTP adaptörünü kullanmadığını yakaladı; gerçek `main()` girişli 50 kişilik kırmızı/yeşil regresyon eklendi (DÜZELTİLDİ, `test_public_speaker_evaluation.py`).
   **TUZAK**
   M4 Sınır çalışma alanındaki aktif ses profilleridir; giriş hesapları değildir. Tüm model sürümleri sayılır; silinen ve başka tenant profilleri sayılmaz. Mevcut profile örnek ekleme/tanıma devam eder, kuyruktaki işler yer ayırmaz, eski fazla profiller otomatik silinmez.
   M5 Galeri dolduğunda yeni kişi kaydı başarısızdır; bu kapasite sonucu ses kalitesi hatası, başarılı bilinmeyen tespiti veya oluşturulmuş sunucu işi sayılmaz. `job_status_counts` değerlendirme işlemlerini sayar.
   **GÖZLEM**
   M6 Kimlik/bilinmeyen precision, recall, F1 ve VoiceUp Score formülleri/eşikler değişmedi. Bu turda yeni model eğitimi, gerçek ses doğruluk deneyi veya daha yüksek doğruluk sonucu yok; önceki deneyler kendi tarihsel kanıtları olarak kalır.
   M7 Backend/worker/frontend çalışır duruma güncellendi; API `max_profiles: 50` alanı, OpenAPI, frontend tipleri ve iki dilde mesajlar birlikte teslim edildi. Şema, bağımlılık, yeni ayar veya Spark imajı değişikliği gerekmedi.
   **AÇIK**
   M8 Güvenlik kapısı `gitleaks` yokluğunda, kalıcı tarayıcı kapısı kabul edilmiş Playwright paketi yokluğunda çıkış 2 ile durdu. Bu iki eksik geçiş sayılmadı; [tam çıktı ve sınırlar](quality-gate-report.md).
   M9 50 kişinin temsilî Türkçe toplantı kayıtlarında yüksek doğrulukla tanınması hâlâ veri kabulü gerektirir. Sentetik kapasite testi bunu kanıtlamaz; bütün uygulama için tam L1/L3 veya kusursuzluk iddiası yoktur.
   **YAN-ETKİ**
   M10 Ayrı canlı test tenantı ve sentetik fikstürü oluşturuldu; sırlar Git dışındadır. Tam kapının geçici `_test` veritabanı düşürüldü. Bu teslimde stage, commit veya push yapılmadı.
