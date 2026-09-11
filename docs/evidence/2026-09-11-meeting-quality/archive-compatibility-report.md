# Koşum raporu — 2026-09-11 · Kamu veri arşivi hazırlayıcısının Python sürüm uyumu ve ayrılmış Windows adları doğrulandı.

1. Sonuç: Aynı 40 durum iki mevcut Python sürümünde başarılı — birim 40 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan:

   | Ortam ve komut | Gözlenen sonuç |
   |---|---|
   | Windows Python 3.12, `.venv/Scripts/python.exe -m pytest tests/test_public_speaker_dataset.py -k without_new_path_api -q --tb=short` | Düzeltmeden önce 6 başarısız; sağlayıcıdaki `ntpath.isreserved` yokluğunda `AttributeError` |
   | Windows Python 3.12, `.venv/Scripts/python.exe -m pytest tests/test_public_speaker_dataset.py -q --tb=short` | Düzeltmeden sonra 40 başarılı |
   | Windows Python 3.13.14, `app/backend/.venv/Scripts/python.exe -m pytest tests/test_public_speaker_dataset.py -q --tb=short` | Aynı 40 test başarılı; yeni API yokluğu simülasyonunda 13 pathlib kullanım dışı bırakma uyarısı |
   | Değişen hazırlayıcı/test dosyalarında Ruff lint/format | Başarılı |

3. Maddeler:

   **KUSUR**

   M1 Hazırlayıcı yalnız Python 3.13'teki `ntpath.isreserved` API'sini çağırıyordu; mevcut Python 3.12'de normal arşiv bile açılmıyordu. API varsa korunur, yoksa her bileşen `PureWindowsPath.is_reserved` ile denetlenir.

   M2 Yalnız son dosya adını denetlemek `LibriSpeech/NUL.txt/sample.flac` gibi iç bileşenleri kaçırabilir; beş farklı iç cihaz adı gerçek arşiv sınırında reddedildi, normal dosya korunarak açıldı.

   **TUZAK**

   M3 Eksik API simülasyonu yalnız hazırlayıcının `ntpath` bağını değiştirir; yeni pathlib'in kendi standart kütüphane bağı silinmez. 3.13'teki uyarılar bu simülasyondan gelir; gerçek 3.13 yolu yeni API'yi kullanır.

   **GÖZLEM**

   M4 ASCII ad sınırı, geçiş/sürücü yolu reddi, son nokta/boşluk koruması, link/aygıt reddi, boyut sınırları ve mevcut dosya çakışması korundu; tüm hazırlayıcı paketi iki yorumlayıcıda tekrarlandı.

   **AÇIK**

   M5 Python 3.11 yorumlayıcısında ayrı bir koşum yapılmadı; yeni corpus indirilmedi ve model/kimlik doğruluğu ölçülmedi.

   **YAN-ETKİ**

   M6 Yalnız hazırlayıcı, testleri ve Accepted 001 plan/T28 kanıtı değişti. Testler geçici arşiv/dizinlerde çalıştı; model/veri seçimleri, bağımlılık pinleri ve Python 3.13 arka uç çalışma zamanı değişmedi.
