# Koşum raporu — 2026-09-11 · Aday checkpoint'ten kalıcı hafıza işlemine kaynak ve sürüm aktarımı doğrulandı.

1. Sonuç: Hafıza ve gerçek worker sınırındaki son birleşik dar paket başarılı — birim 70 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan:

   | Ortam ve komut | Dosya ve sayı |
   |---|---|
   | Linux Python 3.13, gerçek HTTP uygulaması, dosya sistemi ve migrasyon uygulanmış benzersiz `_test` PostgreSQL; `pytest ... -q --tb=short` | `test_meeting_context_memory.py` 21; `test_meeting_candidates.py` 5; `test_meeting_memory.py` 35; `test_meeting_memory_contract.py` 2; `test_meeting_memory_adapter.py` 7 — toplam 70 başarılı, 40,32 saniye |
   | Windows Python 3.13, `mypy app` | 76 kaynak dosyası başarılı |
   | Değişen aday/hafıza dosyaları, Ruff ve Black | Lint ve biçim denetimi başarılı; `git diff --check` başarılı |

3. Maddeler:

   **KUSUR**

   M1 ECAPA'nın reddettiği adayın kaynak hash'i checkpoint'e yazılmıyordu; 8 kHz/44,1 kHz iki gerçek worker testi kırmızı oldu. Yeni aday alanı varlığında kaynak hash'i yazılarak düzeltildi; aynı testler geçti.

   M2 Native izleme vektörü olmayan geçici küme bütün toplantıyı hataya götürüyordu; gerçek worker testi kırmızı oldu. Vektör olmadan yeni aday eklenmez, açık boş aday alanı korunur; test artık toplantının bekleyen kişiyle bitmesini doğruluyor.

   M3 Üç parçada manifest 298 bağlama ulaşıyordu; sınır testi kırmızı oldu. Kaynak sırasındaki ilk 256 bağlam saklanır; 900 saniyelik dosyayla sınır ve özgün aralıklar doğrulandı.

   M4 Eksik veya farklı aday sürümü aynı işlem gibi kabul ediliyordu; iki test kırmızı oldu. `candidate_version` artık sabit işleme sürümüyle eşleşmek zorunda; aksi halde sağlayıcı çağrısı/profil yazımı yok.

   **TUZAK**

   M5 Testlerin vektör ve kalite sonuçları imza/sözleşme kısıtlı fixture'lardır; gerçek veritabanı ve kaynak işlemlerini sınar. Gerçek model saflığı veya konuşmacı doğruluğu sayılmaz.

   M6 Açık boş `candidate_contexts` yeni kalite yoludur; eski ECAPA temiz süresi olsa bile eski kayıt yoluna dönmez. Yalnız bu alanı taşımayan eski checkpoint eski davranışı korur.

   **GÖZLEM**

   M7 Bağlam iki komşu parçadan geldiğinde kaynak ana bölgesine kırpılır, özgün örnek çerçeveleri yinelenmez; aday süre kalıcı doğrulama öncesinde temiz konuşma olarak sayılmaz.

   M8 Önceki [arka uç raporundaki](report.md) dört Mypy hatası giderildi; son 76 kaynak dosyasının tamamı geçti. Eski hafıza paketindeki 35 test de bu birleşik koşumda tekrar geçti.

   **AÇIK**

   M9 Gerçek A/B/D/C model koşumu ve tam profil kalite kapısı ana teslimde ayrıca yürütülür; bu rapor 50 kişi veya kullanıcı kabulü kanıtı değildir.

   **YAN-ETKİ**

   M10 Aday kaynak hash'i, yok izleme davranışı, manifest sınırı ve sürüm doğrulaması eklendi; Decision 13 manifest sınırı güncellendi. Her kırmızı/yeşil koşumun geçici veritabanı kendi sonunda kaldırıldı.
