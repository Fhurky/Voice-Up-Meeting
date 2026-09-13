# Koşum raporu — 2026-09-13 · Türkçe toplantı yürütücüsünün veri, devam ve günlük sınırları

1. Sonuç: Dar yürütücü kontrolleri geçti — birim 21 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2` deposu; Windows yerel araştırma Python 3.12. Komut `.venv/Scripts/python.exe -m pytest tests/test_turkish_meeting_evaluation.py -q --tb=short`; ilk kırmızı koşum 8 başarılı / 8 başarısız, ilk yeşil 16 başarılı, işletim sınırları eklenmiş son koşum 21 başarılı. Etkilenen yürütücü ve test dosyasında `ruff check` ile `ruff format --check` geçti.
3. Maddeler:
   **KUSUR**
   M1 DÜZELTİLDİ: Var olmayan dosya yolu yardımcısı gerçek protokolü açmayı engelliyordu; dosya/hash/WAV örnek sayısı ve üst dizin bağlantısı doğrulaması eklendi.
   M2 DÜZELTİLDİ: Yinelenen referans kişi satırları sözleri sözlüğe çevirirken düşürebiliyordu; tam iki ayrı, boyutu sınırlı referans satırı zorunlu oldu.
   M3 DÜZELTİLDİ: Aynı yeni profil iki kişiyle eşlenebiliyordu; profil çakışması belirsiz sonuç olur, doğruluk referans hafızasına eklenmez. Yinelenen API kişi kimlikleri reddedilir.
   M4 DÜZELTİLDİ: Açık devam seçimi, giriş/çıktı/durum ayrılığı, hardlink koruması, eşzamanlı süreç kilidi ve devam durumunun kişi/protokol/sıra doğrulaması eklendi.
   **TUZAK**
   M5 `--resume` mevcut deneyin devamıdır; bağımsız yeni deney değildir. Her başarısız toplantı kendi iki planlı kişi desteğini korur; bütün zincir bitmeden nihai oran üretilmez.
   M6 Bu veri otomatik konuşma etkinliği ve doğrulanmamış metin referanslı tanısal denemedir. Kaynak zamanı eşlemesi insan işaretli konuşmacı hatası veya altın kimlik etiketi sayılamaz.
   **GÖZLEM**
   M7 Başarısız toplantı bütün referans sözlerini silme hatası olarak korur; gizli referans ve hipotez metinleri yalnız özel kontrol noktasındadır. Gerçek dosya günlük testi kişi/kimlik/parola/özel yol yayımlamadı.
   **AÇIK**
   M8 Gerçek GPU/HTTP deneyi ve tam profil kapısı kök görevde ayrı yürütülür. Bu dar koşumdaki imza kısıtlı API test doubles gerçek model başarısı kanıtı değildir.
   **YAN-ETKİ**
   M9 `scripts/run-turkish-meeting-evaluation.py` ve testleri değiştirildi; geçici WAV/JSON ve süreç kilidi dosyaları test dizininde oluşturuldu. Ürün veritabanına veya kullanıcı profillerine erişilmedi.
