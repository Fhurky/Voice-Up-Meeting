# Koşum raporu — 2026-09-11 · Sabitlenen doğruluk değişikliklerinin tam profil kapısı

1. Sonuç: Tam profil kapısı geçti — birim/entegrasyon 595 başarılı / ön yüz 89 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`, Windows/Git Bash ve yerel Linux/Python 3.13/PostgreSQL 17; `scripts/quality-gate.sh all` → gerçek çıkış kodu 0. Kaynaklar Decision 19–24 son uygulamasıdır; ham kayıt `outputs/2026-09-11-accuracy-audit/full-gate-activated.log` ve `.exit.txt`.

   | Kapsam | Gözlenen kanıt |
   |---|---|
   | Backend | 595/595 pytest, 199,57 saniye; canlı PostgreSQL entegrasyonu açık |
   | Statikler | Ruff/Black/isort; Mypy 80 kaynak; başarılı |
   | Veritabanı | Ayrı `_test` veritabanı, migrasyon uygulama/istenen durum/geçmiş/drift; başarılı; sonunda kaldırıldı |
   | Sözleşmeler | Çevrimdışı OpenAPI ve üretilmiş ön yüz tiplerinin drift kontrolü; başarılı |
   | Ön yüz | Lint, üretim derlemesi, 20 dosyada 89/89 Vitest; başarılı |
   | Yapılandırma ve yönetişim | Ayar eşlemesi, bağımlılık kabulü ve üretilmiş yönetişim drift kontrolü; başarılı |
   | Dağıtım | İki fikstür ortamında 46 standart ve 47 toplantı kaynağı render denetimi; başarılı |

3. Maddeler:
   **KUSUR** — yok
   **TUZAK**
   M1 İlk son-kapı denemesi uygulamanın eşzamanlı backend yeniden başlatması nedeniyle pytest sırasında 137 koduyla kesildi; geçici veritabanı kaldırıldı. `full-gate-final.log` korunur; uygulama açıldıktan sonraki bütün kapı yeniden çalıştırıldı.
   M2 Yerel süreç PATH'i mevcut `C:/Users/furko/bin` Helm ve Git dizinlerini içerir; `MSYS2_ARG_CONV_EXCL=/tmp;/workspace` kullanılır. Kalıcı sistem ayarı veya araç sürümü değiştirilmedi.
   **GÖZLEM**
   M3 Otomasyonun gerçek `KT_GATE_SCOPE`, `KT_GATE_STEP`, `KT_GATE_TESTS` kayıtları ham logda korunur; bu rapor onların yerine geçmez. Başarılı dar testler bu toplama yeniden eklenmedi.
   **AÇIK**
   M4 Güvenlik taramasının bağımsız araç eksiği [güvenlik raporunda](security-report.md) açıktır; tam profil kapısının geçmesi güvenlik veya gerçek model doğruluğu kabulü değildir.
   **YAN-ETKİ**
   M5 Teste ait iki geçici veritabanı ayrı ayrı oluşturulup kaldırıldı. Ana uygulama veritabanına kapı tarafından migrasyon uygulanmadı; ham kayıtlar ignore edilen dizine yazıldı.
