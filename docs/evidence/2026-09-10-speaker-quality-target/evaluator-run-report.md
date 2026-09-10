# Koşum raporu — 2026-09-10 · Profil kotası olmadan büyük değerlendirme manifestleri

1. Sonuç: Sabit profilin Python 3.13.14 ortamında odaklı otomatik kanıt L1 seviyesinde başarılı — birim 234 başarılı / tarayıcı 0 başarılı / atlanan 1; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`; Linux koşumunda ağ kapalı, kaynaklar salt okunur ve geçici dosyalar ayrılmıştı. Son Windows Python 3.12.10 tekrarı yalnız bu sürümle uyumlu koşucu/ölçüm/raporlayıcı paketlerini içerir; tekrarlar toplama eklenmez.

   | Son paket | Başarılı / başarısız / atlanan | Kanıt |
   | --- | --- | --- |
   | Koşucu → `tests/test_public_speaker_evaluation.py` | 90 / 0 / 0 | [Linux JUnit](evaluator-native-final.xml), [ham çıktı](evaluator-native-final.txt) |
   | Manifest bağlı ölçüler → `tests/test_public_speaker_metrics.py` | 98 / 0 / 0 | Aynı Linux JUnit. |
   | Mevcut raporlayıcı → `tests/test_public_speaker_report.py` | 13 / 0 / 0 | Aynı Linux JUnit; üretim kaynağı değişmedi. |
   | Arşiv/veri planlayıcısı → `tests/test_public_speaker_dataset.py` | 33 / 0 / 1 | Aynı Linux JUnit; yalnız Windows junction testi atlandı. |
   | Windows son koşucu/ölçüm/raporlayıcı tekrarı | 201 / 0 / 0 | [JUnit](evaluator-windows-final.xml), [ham çıktı](evaluator-windows-final.txt) |

   | Geliştirme koşumu | Başarılı / başarısız / atlanan | Kanıt |
   | --- | --- | --- |
   | Galeri/bütçe/201. profil kırmızısı | 4 / 9 / 0 | [JUnit](evaluator-red.xml), [çıktı](evaluator-red.txt); 203 test seçilmedi. |
   | İlk odaklı yeşil | 13 / 0 / 0 | [JUnit](evaluator-green.xml), [çıktı](evaluator-green.txt); 203 test seçilmedi. |
   | İlk Windows dört paket | 222 / 7 / 0 | [JUnit](evaluator-windows.xml), [çıktı](evaluator-windows.txt); yedi eski arşiv testi Python 3.12 ortamında başarısız. |
   | İlk Linux dört paket | 228 / 0 / 1 | [JUnit](evaluator-native.xml), [çıktı](evaluator-native.txt) |
   | Bilinmeyen kişi bildirimi kırmızısı | 0 / 7 / 0 | [JUnit](evaluator-declaration-red.xml), [çıktı](evaluator-declaration-red.txt); 83 test seçilmedi. |

   Son yerel komut: `.venv/Scripts/python.exe -m pytest tests/test_public_speaker_evaluation.py tests/test_public_speaker_metrics.py tests/test_public_speaker_report.py --junitxml=docs/evidence/2026-09-10-speaker-quality-target/evaluator-windows-final.xml`.
   [Linux komutu](evaluator-native-command.txt), [dokuz kaynak hashı](evaluator-source-manifest.json), [son lint](evaluator-lint-final.txt) ve [son biçim denetimi](evaluator-format-final.txt) saklandı. Beş değişen kaynak/test dosyası lint ve biçim denetimini geçti.

3. Maddeler:

   **KUSUR**
   M1 Koşucudaki 50 kişilik ve ölçümlerdeki 100 kişilik sınır, kabul edilen büyük deneyleri engelliyordu; kişi rolü başına 200 girdilik işlem bütçesine hizalandı (DÜZELTİLDİ, 51/100/200 ve girdi korunumu testleri).
   M2 Sabit 200 profil sayfalama kontrolü, 200 kişilik galeriye dönüş kişisinin kaydını engelliyordu; denetim planlı kayıt sayısından türetildi (DÜZELTİLDİ, gerçek HTTP ile 201. profil ve üç sayfa testi).
   M3 `unknown_order` bildirimi sorgu kayıtlarıyla doğrulanmıyordu; tip, tekillik, büyüklük ve kişi kümesi eşitliği eklendi. Altı gerçek `main()` testi HTTP/durum dosyasından önce reddi doğrular (DÜZELTİLDİ).

   **TUZAK**
   M4 Kişi rolü başına 200, toplam 1.500 kayıt ve 20.000 planlı işlem sınırları değerlendirme girdisinin kaynak bütçeleridir; uygulamanın profil kotası veya doğruluk garantisi değildir. İç içe galerilerin işleri bütçeye birlikte katılır.
   M5 İlk Windows koşumundaki yedi arşiv testi `AttributeError: module 'ntpath' has no attribute 'isreserved'` ile başarısızdır; bu işlev sabit profilin Python 3.13 sürümünde vardır. Hazırlayıcı kaynağı değiştirilmedi, hata kanıtı korunur.

   **GÖZLEM**
   M6 Gerçek yerel HTTP fikstüründe 51 kişilik ana galeri ve dönüş kişisi 52 profil/207 işlemi tamamladı; 200 profilli diğer fikstürde 201. profil ve dönüş sorgusu başarılıydı. Bunlar model doğruluğu ölçümü değildir.
   M7 Hazırlayıcının zaten mevcut `plan_split` işlevi 200 bilinen/1 bilinmeyen kişiden 807 kayıt planladı. Eski kapasite hatalarının okunması, eski raporlar ve precision/recall/F1 formülleri korunur.

   **AÇIK**
   M8 Linux'ta `test_windows_junction_cannot_redirect_output` işletim sistemi nedeniyle atlandı; aynı test ilk Windows koşumunda geçti. Bu atlama Linux sonucu içinde görünür bırakıldı.
   M9 Tam profil kapısı, gerçek uygulama tarayıcısı, dağıtım ve model doğruluk kabulü ana görevin kanıtıdır; bu odaklı rapor onları tamamlanmış saymaz.

   **YAN-ETKİ**
   M10 İki değerlendirme/ölçüm kaynağı ve üç test dosyası değişti; testler geçici dizinlerde küçük sentetik sesler, HTTP fikstürü ve durum dosyaları oluşturdu. Yeni model/veri indirilmedi; önceki kanıt dizinleri ve kalıcı uygulama verisi değiştirilmedi.
