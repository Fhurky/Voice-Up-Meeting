# Koşum raporu — 2026-09-13 · Türkçe ASR değerlendirme aracının kaynak ve dosya koruması

1. Sonuç: Dar koruma testleri ve mevcut 80 kliplik manifest doğrulaması geçti — birim 19 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2` deposu, Windows yerel araştırma Python 3.12. `.venv/Scripts/python.exe -m pytest tests/test_turkish_asr_dataset.py -q --tb=short`: kırmızı 5 başarılı / 11 başarısız, ilk yeşil 16 başarılı, süreç kilidi ve kaynak sürümü kontrolleriyle son koşum 19 başarılı. Etkilenen iki dosyada `ruff check` ve `ruff format --check` geçti; gerçek manifestte 80 farklı kimlik ve 80 farklı ses hash'i doğrulandı.
3. Maddeler:
   **KUSUR**
   M1 DÜZELTİLDİ: Sesin tamamı okunmadan önce süre sınırı uygulanmıyordu; FLAC başlığı denetlenip en fazla 60 saniye + bir örnek okunur. Gerçek kısa FLAC testinde önceki `float32` örnekleri birebir korundu.
   M2 DÜZELTİLDİ: Manifestte boyut/tekrarlı JSON alanı ve kalibrasyon-test çakışması koruması eksikti; tam manifest, klip kimliği/ses hash'i ayrılığı ve mevcut sabit seçim sırası kontrol edilir.
   M3 DÜZELTİLDİ: Sabit geçici dosya adı başka dosyayı ezebilirdi; mevcut atomik/fsync yardımcısı ve benzersiz geçici dosya kullanılır. İki çıktı kilitlenir; kaynak/model/günlük hedef çakışmaları ve hardlink reddedilir.
   M4 DÜZELTİLDİ: Yürütücü hash'i iş sonunda okunuyordu; kaynak ve manifest hash'leri artık model işi başlamadan dondurulur. Sonradan dosya değişimi çalışan deneyi yeni kaynakmış gibi etiketlemez.
   **TUZAK**
   M5 Arşiv SHA-256 `c3f8aeebe085553d9fa0baf2fed25613b3d80f07b4d6665e88e0610250fc5b3c`, resmî HTTPS kaynağından gözlenen seçili dosya sürümüdür; yayımlayıcının ilan ettiği checksum diye sunulmaz. Hazırlama eski/yeni indirmede bu sürümü zorunlu kılar.
   M6 Mevcut 40/40 seçimi ve çıkarım/skorlama aynı kaldı. `--count` artırılırsa aynı seçim algoritmasında rol sınırı değişir; mevcut manifest değiştirilmez, önceki test verisi yeni kalibrasyon gibi gizlenmez.
   **GÖZLEM**
   M7 Önceden tamamlanan Türkçe ve otomatik dil kalibrasyonları eski yürütücü SHA-256 `9e97320bb42f2adc3b680ea802c171c9a45c0bea7ca5d13393aaf50dbfba8a89` ile donduruldu. İki toplu çıktı 40/40 klip ve aynı 182/1140 sözcük hatasını taşıyor; bu koruma değişikliği nedeniyle model yeniden çalıştırılmadı.
   M8 Mevcut manifest SHA-256 `b7776df4f4744fa364ac358a541b3db056ff8d1d1f9863c00481c713e3ee172e`; bu inceleme ayırılmış kliplerin metnini model ayarı seçmek için kullanmadı.
   **AÇIK**
   M9 Ayırılmış gerçek GPU deneyi, günlük ekleme sorununun giderilmesi ve tam profil kapısı kök görevde izlenir; bu rapor yeni akustik başarı veya ürün transkripti doğruluğu iddiası değildir.
   **YAN-ETKİ**
   M10 `scripts/evaluate-turkish-asr.py` ve dar test dosyası değiştirildi. Sentetik kısa/uzun FLAC, JSON ve kilit dosyaları yalnız testin geçici dizininde üretildi; gerçek veri, eski model çıktıları ve model ağırlıkları değiştirilmedi.
