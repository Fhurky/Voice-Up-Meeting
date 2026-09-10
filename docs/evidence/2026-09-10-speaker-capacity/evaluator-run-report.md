# Koşum raporu — 2026-09-10 · Elli profil kapasiteli değerlendirme ve raporlama sınırları

1. Sonuç: Odaklı otomatik kanıt L1 seviyesinde başarılı — birim 184 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`; son doğrulama ağ erişimi kapalı, kaynakları salt okunur bağlanmış Linux Python 3.13.14 ortamında çalıştı. Windows Python 3.12.10 aynı 184 testi tekrarladı; bu tekrar toplam sayıya eklenmedi.

   | Paket | Son başarılı sayı | Kanıt |
   | --- | ---: | --- |
   | Gerçek yerel HTTP fikstürlü değerlendirme koşucusu → `tests/test_public_speaker_evaluation.py` | 77 | [Linux JUnit](evaluator-native.xml), [ham çıktı](evaluator-native.txt) |
   | Manifest bağlı ölçüler → `tests/test_public_speaker_metrics.py` | 94 | Aynı Linux JUnit; 51 kişilik tarihsel rapor uyumu dahil. |
   | Mevcut anonim raporlayıcı → `tests/test_public_speaker_report.py` | 13 | Aynı Linux JUnit; raporlayıcı kaynağı değişmedi. |
   | Windows son tekrar | 184 | [JUnit](evaluator-cli-green.xml), [ham çıktı](evaluator-cli-green.txt) |

   | Geliştirme koşumu | Başarılı / başarısız / atlanan | Kanıt |
   | --- | --- | --- |
   | İlk kırmızı: galeri, kapasite kaydı, devam ve hata adı | 14 / 4 / 0 | [JUnit](evaluator-red.xml), [çıktı](evaluator-red.txt); 151 test seçilmedi. |
   | İlk yeşil | 182 / 0 / 0 | [JUnit](evaluator-green.xml), [çıktı](evaluator-green.txt) |
   | Geçersiz JSON sabiti kırmızısı | 9 / 1 / 0 | [JUnit](evaluator-json-red.xml), [çıktı](evaluator-json-red.txt); 66 test seçilmedi. |
   | JSON düzeltmesi sonrası ara yeşil | 183 / 0 / 0 | [JUnit](evaluator-final.xml), [çıktı](evaluator-final.txt); komut satırı bağlantı regresyonu henüz eklenmemişti. |
   | Elli profille gerçek `main()` kırmızısı | 0 / 1 / 0 | [JUnit](evaluator-cli-red.xml), [çıktı](evaluator-cli-red.txt); 76 test seçilmedi. |

   Son paket komutu: `python -m pytest -p no:cacheprovider tests/test_public_speaker_evaluation.py tests/test_public_speaker_metrics.py tests/test_public_speaker_report.py --junitxml=/evidence/evaluator-native.xml`.
   [Çalıştırılan Docker komutu](evaluator-native-command.txt), [Python sürümü](evaluator-native-environment.txt), [kaynak hashları](evaluator-source-manifest.json), [dört dosyanın lint sonucu](evaluator-lint-final.txt) ve [biçim sonucu](evaluator-format-final.txt) saklandı.

3. Maddeler:

   **KUSUR**
   M1 `main()` eski HTTP istemcisini geçirerek kapasite işleyicisini atlıyordu; `EvaluationApi` bağlantısı düzeltildi. Koruma: `test_cli_full_fifty_gallery_records_capacity_and_preserves_complete_scores` (DÜZELTİLDİ).
   M2 Yeni 51 kişilik galeri kabul ediliyor ve 50 profil sonrası yeni kişi reddi bütün koşumu durduruyordu; sınır ve iş kimliği olmayan kalıcı başarısız işlem kaydı eklendi (DÜZELTİLDİ, koşucu sınır/devam testleri).
   M3 JSON standardında geçersiz `NaN` hata gövdesi kabul edilebiliyordu; yinelenen alan, bozuk/aşırı büyük gövde ve geçersiz sabit reddi doğrulandı (DÜZELTİLDİ, `test_noncapacity_or_malformed_conflict_stays_fail_closed`).
   M4 `profile_limit` anonim ölçümde adını kaybediyordu; güvenli ad listesine eklendi, kalite dışı sayımı korundu. Var olan yerel lambda lint uyarısı da aynı hesaplı `def` ile giderildi (DÜZELTİLDİ).

   **TUZAK**
   M5 203 planlı işlemde 202 gerçek fikstür işi ve bir başvuru reddi vardır; reddedilen işlemde `attempt_count=0`, `result=null`, `timing=null` ve iş kimliği yoktur. Eski `job_status_counts` alanı kayıtlı işlem durumlarını sayar.
   M6 Fikstürdeki 100/100 ana galeri skoru yalnız hesap ve bağlantı testidir; model çıkarımı, yeni ses deneyi veya ürün doğruluk başarısı değildir. Devam koşumu kayıt isteğini yinelemez.

   **GÖZLEM**
   M7 Yeni canlı galeri sınırı 50'dir; manifestteki 51 kimlik veya bilinmeyen sorgular kesilmez. Tarihsel 51 kişilik rapor salt okunur ölçüm aracıyla hâlâ hesaplanır; eski kanıtlar bu çalışmada değiştirilmedi.

   **AÇIK**
   M8 Tam profil kapısı, gerçek ürün tarayıcısı ve yerel dağıtım doğrulaması ana görevde yürütülür; bu odaklı rapor onların sonucunu veya gerçek model kalite kabulünü iddia etmez.

   **YAN-ETKİ**
   M9 Testler geçici dizinlerde anonim ses başlıkları, yerel HTTP sunucusu ve durum dosyaları oluşturdu; Docker koşumunda ağ kapalıydı. Yeni kanıt dosyaları yalnız bu dizine yazıldı; kalıcı uygulama verisi değişmedi.
