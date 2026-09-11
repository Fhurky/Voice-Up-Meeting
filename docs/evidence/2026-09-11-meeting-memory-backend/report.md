# Koşum raporu — 2026-09-11 · Toplantı hafızasının kaynak, işlem ve iki model popülasyonu sınırları doğrulandı.

1. Sonuç: Son üç dar doğrulama başarılı; 63 farklı test kapsandı — birim 74 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan:

   | Ortam ve komut kapsamı | Dosyalar | Gözlenen sonuç |
   |---|---|---|
   | Linux Python 3.13, gerçek HTTP uygulaması/dosya sistemi, ayrı geçici PostgreSQL; `pytest ... -q --tb=short` | `tests/integration/test_meeting_context_memory.py`, `test_meeting_memory.py`, `tests/unit/test_meeting_memory_contract.py`, `test_meeting_memory_adapter.py` | 61 başarılı, 36,88 saniye |
   | Aynı yığın, yeni geçici PostgreSQL; `pytest tests/integration/test_meeting_context_memory.py -k population -q --tb=short` | Tenant/model/yaşam döngüsü/kaynak sorgusu, fiziksel referans ve çelişki testleri | 4 başarılı, 15 seçilmeyen; seçilmeyenler önceki koşumdadır |
   | Windows Python 3.13; `pytest tests/unit/test_meeting_memory_contract.py tests/unit/test_meeting_memory_adapter.py -q` | Özel HTTP şeması ve taşıma sınırı | 9 başarılı, 0,38 saniye |
   | `kt-vibecoding-python-web-v2`; değişen dosyalarda Black, Ruff ve Mypy | Dokuz değişen arka uç kaynak dosyası ve yeni testler | Biçim/lint ve tip denetimi başarılı |
   | Yerel ana veritabanı; `scripts/db.sh generate meeting_profile_population`, `apply`, `validate`, `status` | SQLAlchemy otoritesi ve `9cf5f2d22daf` eklemeli migrasyonu | Uygulama başarılı; drift yok, doğru head gözlendi |

3. Maddeler:

   **KUSUR**

   M1 Yeni kalite reddi eski 24 saniyelik kabul edilmiş süreyi görünür bırakıyordu; regresyon 1 başarısız gözlendi, ret yolunda süre/aralık temizliğiyle düzeltildi ve sonraki 61 testte geçti (`test_context_rejection_clears_unaccepted_legacy_clean_count`).

   M2 Yeni port yokken şema testi import hatasıyla kırmızıydı; gerçek tipli port eklendikten sonra iki şema testi geçti. İlk taşıma testi fixture anahtarı 32 byte sınırını karşılamıyordu; fixture düzeltildi, ürün ayarı gevşetilmedi.

   **TUZAK**

   M3 74 başarılı sayısı son üç koşumdaki toplam çalıştırmadır; 63 farklı test içerir. Test vektörleri işlem/sözleşme fixture'ıdır ve ses modeli doğruluğu kanıtı değildir.

   M4 Yeni doğrulama ret/hash/model/aralık hatasında eski kalite yoluna dönmez. Yalnız aday alanı bulunmayan eski checkpoint eski yolla çalışır; tanınan profillerin vektörleri ve örnek sayısı değişmez.

   M5 Toplantı veri aktarımı özgün örnekleme hızındaki tam sayı çerçeveleri kullanır. 8 kHz ve 44,1 kHz dosyalar gerçek saklanan örnek/hash ve kaynak aralıklarıyla doğrulandı; sahte sessizlik konuşma süresi sayılmadı.

   **GÖZLEM**

   M6 Beş yeni profil, daha kısa yeni kayıtta aynı beş kimlik, tam 20 saniyelik altıncı kişi için bekleme ve 24 saniyelik yeterli altıncı kişi için tek yeni profil gerçek veritabanı işlemleriyle geçti.

   M7 Eski 192 boyutlu profil tanıma, ayrı 256/192 sonuçlarının çelişkide karar vermemesi, tekrar PCM ve kapalı otomatik kayıt, bozuk sağlayıcı hash/aralıkları, izin/lease/kanıt değişimi ve tenant dışı fiziksel kaynak referansı sınandı.

   **AÇIK**

   M8 Gerçek A/B/D/C model çalışması, temsil edici Türkçe toplantılar, 50 kişi doğruluğu ve tam profil kalite kapısı bu dar arka uç koşumunun kanıtı değildir; ana teslim doğrulamasında ayrıca raporlanmalıdır.

   M9 İlk tüm arka uç Mypy taramasındaki `meeting_chunks.py` değişken adı çakışması sonradan giderildi; 76 dosyanın geçen son kanıtı [aday koşum raporundadır](candidate-report.md).

   **YAN-ETKİ**

   M10 Yalnız ana backend/worker durdurularak eklemeli yerel şema migrasyonu uygulandı ve aynı konteynerler yeniden başlatıldı; test veritabanlarının tamamı kendi koşumlarının sonunda kaldırıldı.

   M11 Kalıcı profilin mevcut kimliği ve 192 boyutlu alanı korundu; ayrı nullable 256 boyutlu alanlar, kaynak kayıt referansı, kalite portu/adapteri, kaynak doğrulaması, worker bileşimi ve açık işleme sürümü eklendi. Commit/push bu alt görevde yapılmadı.
