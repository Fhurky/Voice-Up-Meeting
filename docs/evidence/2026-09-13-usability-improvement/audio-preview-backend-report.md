# Koşum raporu — 2026-09-13 · Kaynak ses önizlemesinin dosya ve PostgreSQL sınırları

1. Sonuç: Önizleme ve eski toplantı/hafıza regresyonları geçti — birim 58 başarılı / PostgreSQL ve HTTP 87 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`, Windows üzerindeki Git Bash sarmalayıcılarıyla yerel Docker Linux/Python 3.13 ve PostgreSQL 17. İstekler gerçek FastAPI uygulamasına `ASGITransport` üzerinden, imzalı JWT ve gerçek tenant tablolarıyla gönderildi; ağ dinleyicisinde oturum açma veya tarayıcı kanıtı değildir. GPU/model çağrısı yoktur.

   | Koşum | Gözlenen sonuç | Kanıt |
   | --- | --- | --- |
   | İlk kırmızı: yeni iki dosya | 55 başarısız, 1 başarılı; metot/rota henüz yok | JUnit (Git dışı yerel çıktı: `../../../outputs/2026-09-13-usability-improvement/voiceup-preview-red.xml`) |
   | İlk uygulama | 54 başarılı, 2 başarısız; profil vektörünün test karşılaştırmasında NumPy dizi eşitliği hatası | JUnit (Git dışı yerel çıktı: `../../../outputs/2026-09-13-usability-improvement/voiceup-preview-green.xml`) |
   | Düzeltilmiş ilk yeşil | 56/56 başarılı | JUnit (Git dışı yerel çıktı: `../../../outputs/2026-09-13-usability-improvement/voiceup-preview-green-final.xml`) |
   | Ek sınırların kırmızısı | 2 başarısız, 1 başarılı; önceden bağlı üst dizin ve mühürlenmemiş iptal edilmiş kayıt | JUnit (Git dışı yerel çıktı: `../../../outputs/2026-09-13-usability-improvement/voiceup-preview-boundary-red.xml`) |
   | Son birleşik regresyon | 145/145 başarılı, 46,202 saniye; yeni önizleme 37 dosya + 22 PostgreSQL/HTTP testi, eski davranış 86 test | JUnit (Git dışı yerel çıktı: `../../../outputs/2026-09-13-usability-improvement/voiceup-preview-regressions.xml`) |
   | Ruff, Black, isort | Etkilenen 5 dosyada başarılı; kaynak biçimi değiştirilmeden doğrulandı | Aşağıdaki komutlar |
   | mypy | 80 uygulama modülünde başarılı | `mypy app` |
   | Yalıtılmış test veritabanı | Mevcut tüm Alembic geçişleri uygulandı; koşumdan sonra veritabanı düşürüldü, katalog sayısı 0 | `scripts/db.sh apply`, mevcut `scripts/stack.sh` PostgreSQL sarmalayıcısı |

   Kullanılan veritabanı yalnız `voiceup_preview_20260913_e9b61d_test` idi; uygulama veritabanına migration uygulanmadı. Komutlar `MSYS2_ARG_CONV_EXCL='/tmp;/workspace'` ve mevcut `%USERPROFILE%\bin`/Git Bash yollarıyla çalıştırıldı. Beş JUnit çıktısı başlangıçta birleşik `--junitxml=/tmp/...` argümanıyla üretildi; aşağıdaki düzeltilmiş yazım aynı hedefi iki argümanla verir:

   ```text
   scripts/stack.sh exec -T -e VOICEUP_DATABASE_URL=<yalnız bu geçici _test veritabanı> -e RUN_POSTGRES_INTEGRATION=1 backend pytest tests/unit/test_meeting_audio_preview.py tests/integration/test_meeting_audio_preview.py tests/unit/test_meeting_audio.py tests/integration/test_meeting_workflow.py tests/integration/test_meeting_memory.py tests/integration/test_meeting_context_memory.py -q --tb=short --junitxml /tmp/voiceup-preview-regressions.xml
   ```

   Statik kontrol, mevcut kalite kapısının yöntemindeki gibi uygulama/testlerin geçici Linux kopyasında ve Python dosyaları 0644 modundayken yapıldı; kullanıcı çalışma ağacının izinleri değiştirilmedi:

   ```text
   ruff check app/infrastructure/meeting_audio.py app/services/meeting_service.py app/api/meetings/router.py tests/unit/test_meeting_audio_preview.py tests/integration/test_meeting_audio_preview.py
   black --check app/infrastructure/meeting_audio.py app/services/meeting_service.py app/api/meetings/router.py tests/unit/test_meeting_audio_preview.py tests/integration/test_meeting_audio_preview.py
   isort --check-only app/infrastructure/meeting_audio.py app/services/meeting_service.py app/api/meetings/router.py tests/unit/test_meeting_audio_preview.py tests/integration/test_meeting_audio_preview.py
   mypy app
   ```

   Son kaynak SHA-256 değerleri:

   | Dosya | SHA-256 |
   | --- | --- |
   | `app/backend/app/infrastructure/meeting_audio.py` | `4c2bd2cf26c70eab76256cd5e67f05cd025abad07165122d8e04eba4545f7fe9` |
   | `app/backend/app/services/meeting_service.py` | `c0075ddd378d15753aeb7ffd4f81a9ab4c9dc0ab3a397172b9128632c5b3215a` |
   | `app/backend/app/api/meetings/router.py` | `af57a079a6ef6b45aad94c02c292572f5b2d22275279bd22052bc83c09e64674` |
   | `app/backend/tests/unit/test_meeting_audio_preview.py` | `c7782ce1806c1bbae1cb0a03d164115f1811eeef63331ab9108f4461500d5840` |
   | `app/backend/tests/integration/test_meeting_audio_preview.py` | `729473e7620e2523612fedf140f8b257bbadc2ad7feb81bc4c1dba0638a2ae48` |

3. Maddeler:

   **KUSUR**

   M1 Eksik önizleme eklendi: zorunlu sonlu süreler, 30 saniye sınırı, mono PCM16 WAV, 11.520.128 bayt üst sınırı ve saklanmayan yanıt; gerçek dosya/API testleriyle DÜZELTİLDİ.

   M2 Depo kurulmadan önce bağlı üst dizin çözülerek gizlenebiliyordu; önizleme özgün yolu ayrıca koruyup başlangıç/sonda denetler. Mühürlenmeden iptal edilmiş yükleme 409 üretir; ek kırmızı/yeşil testlerle DÜZELTİLDİ.

   M3 İlk yeşil denemesindeki iki hata testin NumPy profil vektörü karşılaştırmasına aitti; vektörler kayıpsız listeye çevrilerek tüm sütunların değişmezliği doğrulandı. Ürün eşiği veya vektörü değiştirilmedi.

   **TUZAK**

   M4 Önizleme tüm kaydı yeniden hashlemez: biçim/boyut/süre/hız/kanal ve açılmış dosya kimliği denetlenir; aynı metadata korunarak istekten önce yapılmış PCM değişimini kesin saptadığı iddia edilmez.

   M5 Git Bash birleşik JUnit yolunu Windows yoluna çevirdi; yalnız bu koşuma ait beş XML doğrulanmış `outputs/` konumuna taşındı. PowerShell stdin sonundaki CR ilk mypy komutunda `app\r` yolu üretti; son yorum satırıyla yeniden çalıştırılan statik kontrol geçti.

   **GÖZLEM**

   M6 Gerçek WAV/FLAC, 8/16/48/192 kHz, 1/2/8 kanal; en çok 65.536 karelik okumalar, 30 saniyelik üst sınır, kırpılmış ses, dosya/üst dizin/hardlink, açılıştan önce silinme ve okurken değiştirme gözlendi. Linux bağlantı testlerinde atlama yoktur.

   M7 Kırpılmış kaynak yalnız dinlemede kabul edilir; eski `window()`/`sample()` retleri, beş kişinin dönüşü/yeni kişi, eşzamanlı kayıt ve tenant/hafıza korumaları geçti. Süresi dolmuş kaynak 410 verirken metin/kişi sonuçları okunur kaldı.

   **AÇIK**

   M8 Bu rapor dar otomatik arka uç kanıtıdır. Tam profil/güvenlik kapısı, üretilmiş sözleşme/tip, gerçek ağ oturumu, tarayıcı ve fiziksel ses çıktısı bu koşumun kapsamında çalıştırılmadı; ana teslimin ayrı kanıtıyla değerlendirilir.

   **YAN-ETKİ**

   M9 Üç arka uç dosyası ve iki test dosyası eklendi/değişti; önceki RIFF bütünlük değişikliği korundu. Yeni kalıcı şema/ayar/model yoktur; yalnız geçici test tenantları, dosyaları ve veritabanı kullanıldı; test veritabanının kaldırılması ayrıca doğrulandı.
