# Koşum raporu — 2026-09-13 · Tam uygulama kalite kapısı ve güvenlik aracı durumu

1. Sonuç: Tam profil kapısı 965 testle geçti; güvenlik kapısı eksik araç nedeniyle çalıştırılamadı — birim 690 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows PowerShell 5 ve Git Bash üzerinden Docker Linux Python 3.13/React arayüzü; profil `kt-vibecoding-python-web-v2`.

   | Komut / kontrol | Gözlenen |
   |---|---|
   | İlk `scripts/quality-gate.sh all` | `backend-static` iki Ruff `SIM905` hatasında durdu; kendisine ait test veritabanını düşürdü |
   | Son `scripts/quality-gate.sh all` | Başarılı; 780 arka uç testi: 505 birim + 275 gerçek PostgreSQL entegrasyonu |
   | Aynı tam kapı, arayüz | Lint, üretim derlemesi, tip kontrolü ve 185 birim testi başarılı |
   | Aynı tam kapı, sözleşmeler | Çevrimdışı OpenAPI ve üretilmiş frontend tipleri güncel |
   | Aynı tam kapı, ortam | 43 ayar/40 Compose anahtarı eşleşti; yalnız benzersiz `_test` veritabanına migration uygulandı, şema kontrol edildi ve test veritabanı düşürüldü |
   | Aynı tam kapı, yönetişim/dağıtım | 93 yönetişim dosyası + 4 etkinleştirilmeyen projeksiyon güncel; normal 46 ve toplantı 47 kaynak, ikişer overlay ile render edildi |
   | `scripts/security-gate.sh` | Çıkış 2: `required offline security tool is unavailable: gitleaks` |

   Birim 690, arka uç 505 ile arayüz 185'in toplamıdır. Gerçek PostgreSQL
   275 ayrıca sayılır; 965 toplamına dahildir. Dar koşumlar yeniden bu toplama
   eklenmez. Test atlaması yoktur; güvenlik tarayıcıları başarı veya test atlaması
   olarak etiketlenmez. Ham kapı kayıtları Git dışı
   `outputs/2026-09-13-contextual-transcript-review/quality-gate*.log` içindedir.

3. Maddeler:

   **KUSUR**
   M1 İki sabit sözcük kümesindeki `.split()` aynı elemanlı sabit listelerle değiştirildi; son Ruff, Black, isort, mypy ve tam kapı başarılı.

   **TUZAK**
   M2 Windows bağlama noktalarının dosya izinleri için kapının mevcut geçici kopya yöntemi kullanıldı; depo dosyalarına `chmod` uygulanmadı.

   **GÖZLEM**
   M3 Kapının her iki koşumu da yalnız kendi oluşturduğu `_test` veritabanını kullandı ve sonunda düşürdü; uygulama veritabanına migration uygulanmadı.

   **AÇIK**
   M4 `gitleaks` bulunmadığı için kapı ilk araç kontrolünde durdu; Semgrep, Trivy ve kabul edilmiş çevrimdışı tarayıcı materyali doğrulanmadı. Tam güvenlik onayı yok.
   M5 Gerçek tarayıcı ve model kanıtları ayrı raporlardadır; bu test sayısı model düzeltme doğruluğu veya kullanıcı kabulü değildir.

   **YAN-ETKİ**
   M6 İki geçici test veritabanı oluşturulup düşürüldü; üretilmiş API sözleşmeleri güncellendi. Sürüm/paket/image kabulü değiştirilmedi.
