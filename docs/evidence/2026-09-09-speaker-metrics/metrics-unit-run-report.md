# Koşum raporu — 2026-09-09 · Manifest bağlı çevrimdışı konuşmacı ölçüleri

1. Sonuç: `voiceup-open-set-v1` ölçüm ve veri sınırları geçti — birim 105 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows yerel sanal ortam, `kt-vibecoding-python-web-v2`; `.venv/Scripts/python.exe -m pytest tests/test_public_speaker_metrics.py tests/test_public_speaker_report.py -q --junitxml=outputs/speaker-metrics/green.xml` → yeni ölçüler 92, değişmeyen eski rapor testleri 13. [JUnit](metrics-unit-tests.xml), [konsol](metrics-unit-console.txt), [kırmızı/yeşil evreler ve kaynak özetleri](metrics-red-green.json).
   `ruff check` ve `ruff format --check`, `scripts/speaker_metrics.py`, `scripts/report-public-speakers.py`, `tests/test_public_speaker_metrics.py` üzerinde başarılı; sahiplenilen dosyalarda `git diff --check` başarılı.
3. Maddeler:
   **KUSUR**
   M1 Yinelenen işlem, sahte kişi/kaynak bağı, kaydedilmemiş profile atama ve değiştirilmiş sayaç/oranlar yeni protokolde reddedilir; tam sayısal örnekler ve bozuk veri testleriyle korundu (DÜZELTİLDİ, `test_public_speaker_metrics.py`).
   M2 Üreticinin son doğrulaması hata verdiğinde tüm işler terminal olsa bile tamamlanmış skor gösterilmesi engellendi; dokuz üretici durum testi önce başarısız, sonra başarılı oldu (DÜZELTİLDİ).
   **TUZAK**
   M3 Eksik/bekleyen planlı işlem veya tamamlanmamış üretici koşumu bütün aşama oranlarını ve puanlarını `null` bırakır; başarısız kayıtlı kişiler bilinen sınıfın paydasında kalır.
   M4 Altı tanınan kalite hata kodu ayrı sayılır; diğer kodlar `other_or_unclassified` olarak kalır. Ham hata metni yayımlanmaz; belirsiz/hatalı sorgu bilinmeyeni doğru bulma sayılmaz.
   M5 İç içe galeriler ve yeni kişinin geri dönüşü birleştirilmez; 105 test sonraki paketlerde yeniden koşulursa toplam benzersiz test sayısına yeniden eklenmez.
   **GÖZLEM**
   M6 Kimlik micro F1, kişi başına macro F1, bilinmeyen F1 ve harmonik ürün puanı kesin kesirlerle doğrulandı; örnek altı sorguda ürün puanı `1600/31` olur. Eski 13 test ve varsayılan şema 1 yolu korundu.
   M7 İlk kırmızı evrede 56 testin 7'si başarılı, 1'i başarısız ve 48'i eksik modül hatası verdi; sonraki sınır, hata sınıflaması ve üretici kırmızı evreleri ayrı kaydedildi. Son yeşil 105/105'tir.
   **AÇIK**
   M8 Bu paket model çıkarımı, canlı uygulama veya yeni kör deney çalıştırmaz; gerçek raporların yeniden puanlanması, Python 3.13 ve tam profil kapısı ayrı kanıtlardadır. Bu alt görevin kanıt seviyesi L1'dir.
   **YAN-ETKİ**
   M9 Yalnız çevrimdışı raporlayıcı, yeni saf ölçüm modülü, sentetik testler ve bu kanıt dosyaları eklendi/değişti; model, eşik, veritabanı ve eski ölçüm kanıtları değişmedi.
