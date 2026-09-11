# Koşum raporu — 2026-09-11 · Altı kalıcı örneğin kaynak saflığı ve yeni bir tanıma işinde hafızanın değişmemesi doğrulandı.

1. Sonuç: Kaynak saflığı ve saklanan ses hashleri 6/6 profilde, kontrollü tekrarın öncesi/sonrası değişmezlik 6/6 profilde başarılı; yeni B işinde 5/5 kişi tanındı — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok. Bu dar ses kaynağı/hafıza sınırı gerçek HTTP ve PostgreSQL ile L2 düzeyinde gözlendi.
2. Koşulan:

   | Ortam ve komut | Gözlenen sonuç |
   |---|---|
   | Windows Python → `docker exec -i voiceup-backend-1 python -`, `v8-memory-audit.py`; profil `kt-vibecoding-python-web-v2` | Yalnız belirtilen V8 tenantı ve toplantılarında PostgreSQL `READ ONLY` / `REPEATABLE READ`; A/B/D/C için 22 konuşmacı satırı incelendi |
   | `v8-memory-audit.py --label after-c --baseline .../v8-memory-audit-after-a.json` | A'nın beş ve C'nin bir yeni profili için temiz kaynak aralıklarından WAV yeniden oluşturuldu; saklı recording/sample/meeting-source SHA-256 bağları 6/6 tam eşleşti |
   | `v8-repeat-memory-proof.py`, mevcut `run-meeting-evaluation.py` HTTP yardımcıları ve gerçek yerel model worker'ı | Sıradan izinli kullanıcı, yeni toplantı işi, özgün B kaynak hashinin doğrulanması, iki `complete`, 5 tanınan kişi, toplam 6 profil; süreç çıkışı 0 |
   | Kontrollü tekrarın gerçek DB görüntüleri | Önce `2026-09-11 06:42:20.954987 UTC`, sonra `06:43:35.879954 UTC`: 6 profil ve 6 örneğin tamamı eşit; iki modelin vektör hashleri, kaynak/model/örnek metadata ve ad hashleri değişmedi |
   | Özgün kanıtların korunması | Tamamlanmış V8 state ve frozen protocol SHA-256 tekrar öncesi/sonrası eşit; yeni işlem ayrı state ve iş kimliği kullandı |

   | Yeni profil kaynağı | Saklanan saniye | Kendi kaynağının payı | Başka kişiye ait saniye |
   |---|---:|---:|---:|
   | A · ls-6313 | 26,0781875 | %99,869623 | 0 |
   | A · ls-6455 | 24,76575 | %99,886941 | 0 |
   | A · ls-6123 | 30,0943125 | %99,833856 | 0 |
   | A · ls-5895 | 25,171 | %99,176880 | 0,16725 |
   | A · ls-4570 | 21,7431875 | %99,779241 | 0 |
   | C · ls-700 | 23,0090625 | %99,887001 | 0 |

3. Maddeler:

   **KUSUR**

   M1 İlk denetim sorgusu olmayan `meeting.sha256` sütununu kullandığı için başarısız oldu; yok sayılan denetim betiği gerçek `source_sha256` alanına düzeltildi ve sorgu tekrar çalıştı. Uygulama kodu veya veritabanı değiştirilmedi.

   **TUZAK**

   M2 Tarihsel `after-a` adlı ilk görüntü gerçekte `06:39:03.217286 UTC` anında B/D bitmiş, C sonlandırılırken alındı; B öncesi değişmezlik kanıtı olarak kullanılmadı. Ayrı kontrollü tekrar bu açığı gerçek yükleme öncesi görüntüyle kapattı.

   M3 Kontrollü tekrar aynı B dosyasını kullanır: yeni tanıma işinin hafızayı değiştirmediğini sınar; yeni sözler veya farklı toplantı koşullarıyla ek genelleme kanıtı sayılmaz.

   **GÖZLEM**

   M4 Saflık, saklanan benzersiz frame'lerin doğru frozen kişi aralıklarıyla kesişiminin tüm saklanan frame'lere bölümüdür; yabancı kişiye ait ve hiçbir kaynağa atanmayan süre paydada kaldı. Altı örneğin toplamı 150,8615 saniye, ağırlıklı doğru kaynak payı %99,739372'dir.

   M5 A · ls-5895 içinde 0,16725 saniye yabancı kaynak vardır; D'deki tanınan ls-5895 adayının kaynak payı %96,385575'tir. D adayı yeni örnek olarak yazılmadı; bütün 22 satır ve başarısız saflık örneği [sayısal kanıtta](v8-source-purity-memory-results.json) korunur.

   M6 Sayısal kanıt SHA-256: `f421c8df198ad8a6629f0058e2ab4c1fb40d3c3bdf48fa6c1c1f83e318cc5800`; içerik tüm denetim/HTTP yardımcıları ile önce/sonra görüntülerinin hashlerini içerir. Ham vektör, ses, transkript, parola veya token içermez.

   **AÇIK**

   M7 Referanslar insan etiketli konuşma maskeleri değil, sessizlik de içerebilen dondurulmuş İngilizce kaynak aralıklarıdır; bu deney Türkçe toplantı, 50 kişi, konuşma ayrımı/kelime hata oranı veya kullanıcı kabulü L3 kanıtı değildir.

   **YAN-ETKİ**

   M8 Yetkilendirilmiş ayrı B tekrar işi aynı tenantta oluşturuldu ve kaydı korundu; profil/örnek sayısı değişmedi. Denetim yardımcıları ve ara kanıtlar yalnız yok sayılan `outputs/` altında, bu rapor ve temizlenmiş sayısal sonuç `docs/evidence/` altında eklendi; servis/GPU ayarı, üretim kodu ve kaynak fikstürler değiştirilmedi.
