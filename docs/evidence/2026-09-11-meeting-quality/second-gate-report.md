# Koşum raporu — 2026-09-11 · Tam profil kapısının ikinci denemesi tarihsel pencere sınırı testinde durdu.

1. Sonuç: İkinci tam kapı bir tarihsel ret beklentisinde başarısız — birim 469 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan:

   | Ortam ve komut | Gözlenen sonuç |
   |---|---|
   | Windows Git Bash → Linux Python 3.13/PostgreSQL 17, `scripts/quality-gate.sh all`, profil `kt-vibecoding-python-web-v2` | Yapılandırma/bağımlılık/eşleme, geçici veritabanı, migrasyon ve backend Ruff/Black/isort/Mypy başarılı; Mypy 77 dosya |
   | `backend-tests`, gerçek migrasyonlu PostgreSQL ve `pytest -q --junitxml=/tmp/kt-gate-pytest.xml` | 470 test: 469 başarılı, 1 başarısız, 0 atlanan; 151,45 saniye |
   | Kapı temizliği | `database-test-drop` başarılı |
   | Windows Python 3.13, değişen repository testinde Ruff/Black/isort | Dar statik kontroller başarılı; yeni sınır testinin çalıştırılması son kapıda bekleniyor |

3. Maddeler:

   **KUSUR**

   M1 `test_meeting_child_bounds_and_embedding_provenance[chunk-changes2]` hâlâ `context_end=71` için ret bekliyordu; Accepted Decision 14 sınırı 310'a çıkardığı için bu değer geçerli. Ret girdisi 311'e güncellendi; tam 310 kabulü için gerçek DB testi eklendi.

   **TUZAK**

   M2 Üretim sınırı veya migrasyon değiştirilmedi; eski test yeni kabul edilmiş sözleşmeye taşındı. Eklenen kabul/ret testleri geçmeden bu düzeltme için yeşil kanıt çıkarılamaz.

   M3 Yeni readiness tarif regresyonu bu koşum başladıktan sonra tamamlandı. Son kapı, arka uç dosyaları ve kaynak sınırı ayarları sabitlendikten sonra yeniden çalıştırılacaktır.

   **GÖZLEM**

   M4 Ham çıktı [ikinci denemede](../../../outputs/2026-09-11-meeting-quality-090437/full-gate-latest.txt) korunur; backend-test sayıları doğrudan gerçek `KT_GATE_TESTS` kaydından alınmıştır.

   **AÇIK**

   M5 İstenen şema durumu, OpenAPI, ön yüz lint/derleme/test/tipleri, yönetişim ve chart aşamaları backend testi hatası nedeniyle çalışmadı; tam kapı henüz geçmedi.

   M6 Ayrı güvenlik kapısı `gitleaks` çevrimdışı aracı bulunmadığından çıkış 2 ile durmuştur; [ham güvenlik çıktısı](../../../outputs/2026-09-10-meeting-delivery/security-gate-latest.txt) korunur. Bu koşum güvenlik geçişi sayılmaz.

   **YAN-ETKİ**

   M7 Benzersiz geçici veritabanı kapı sonunda kaldırıldı; ana uygulama veritabanı değiştirilmedi. Repository sınır fixture'ı güncellendi, bir sınır kabul testi eklendi ve önceki kanıtları koruyan yeni çıktı dizini açıldı.
