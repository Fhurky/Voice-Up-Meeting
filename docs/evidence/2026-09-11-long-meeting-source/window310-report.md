# Koşum raporu — 2026-09-11 · 300 saniyelik toplantı pencereleri, kaynak belleği ve eski checkpoint devamı.

1. Sonuç: Yeni kaynak sınırları ve eski toplantıların devamı doğrulandı — birim 44 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok. Dosya/gerçek HTTP/PostgreSQL davranışı L2; model doğruluğu bu koşumda ölçülmedi.
2. Koşulan: `kt-vibecoding-python-web-v2`; yerel Linux x86_64 Python 3.13, PostgreSQL 17 ve Windows Python 3.13. [Ölçümler ve kaynak hashleri](window310-results.json).

   | Kontrol / komut | Gözlenen sonuç |
   | --- | --- |
   | `pytest -q tests/unit/test_meeting_audio.py tests/unit/test_meeting_window_limits.py` — RED | 5 başarısız, 18 başarılı; 300 ana pencere, 310 saniye dosya ve tipli/HTTP sınır kabulü mevcut değildi. |
   | Aynı iki dosya — ilk GREEN | 23 başarılı. |
   | Worker/tracking + aynı unit dosyaları — ilk PostgreSQL koşumu | 5 başarısız, 32 başarılı; gerçek DB check'i hâlâ 70 saniye olduğu için büyük chunk yazılamadı. |
   | Eski pencere saf fonksiyonu ve gerçek legacy-checkpoint testi — ayrı RED | İki ayrı regresyon başarısız; eski politika parametresi ve oluşturma metadatası eksikti. |
   | `pytest -q tests/integration/test_meeting_worker.py tests/integration/test_meeting_tracking.py tests/unit/test_meeting_audio.py tests/unit/test_meeting_window_limits.py` — yeni migration/metadata | 39 başarılı, 20,89 saniye; eski ve yeni pencere, devam/iptal/fence, sözcük sınırı, kaynak yuvarlama ve hafıza örneği sınırı. |
   | `pytest -q tests/integration/test_long_meeting_sources.py -k 'not maximum_rate'` | 4 başarılı, 48,20 saniye; 1/2/4 saat ve dört saatten bir PCM örneği fazla kaynak reddi. |
   | `pytest -q tests/integration/test_long_meeting_sources.py -k maximum_rate` | 1 başarılı, 12,44 saniye; 310 saniye/192 kHz/8 kanal kaynak, 256 MiB assertion değişmedi. |
   | `scripts/db.sh generate meeting_window_bounds`, ardından `apply`, `validate`, `status` | `755327e73d5c` yerel DB'ye uygulandı, yeni head ve drift kontrolü geçti; eski migration değiştirilmedi. |
   | Black/isort/ruff — değişen 11 backend/test kaynağı; mypy — dört bağımsız kaynak | Başarılı. Worker transitif kontrolünde eşzamanlı değişen `meeting_chunks.py` kaynaklı 4 tür hatası ana ajana bildirildi; bu alt koşumda düzeltilmedi. |

   | Gerçek sessiz WAV | Kaynak byte | Pencere | En uzun pencere | Okuyucu tepe bellek | HTTP sunucusu tepe bellek | Yeniden başlatılarak onaylanan aktarım parçası |
   | --- | ---: | ---: | ---: | ---: | ---: | ---: |
   | 1 saat | 115.200.044 | 12 | 310 sn | 56,34 MiB | 117,03 MiB | 28 |
   | 2 saat | 230.400.044 | 24 | 310 sn | 55,93 MiB | 117,69 MiB | 55 |
   | 4 saat | 460.800.044 | 48 | 310 sn | 56,27 MiB | 117,43 MiB | 110 |

3. Maddeler:

   **KUSUR**
   M1 `meeting_chunk` DB check'i 70 saniyede kaldığı için 310 saniyelik kaynak yazılamıyordu; additive migration yalnız check sınırını genişletti, mevcut veri ve 0–239 indeksleri korundu.
   M2 Güncellemeden önceki checkpoint'i yeni 300 saniye ayarıyla yorumlamak kaynak atlanmasına yol açabilirdi; oluşturma anındaki ayar kaydedildi, alanı olmayan eski toplantılar 60 saniyelik kaynak sahipliğini korur.
   **TUZAK**
   M3 Named-check autogenerator ifade farkını üretmedi; boş üretilen revision uygulamadan önce incelenip açık `drop_constraint/create_check_constraint` ile tamamlandı. Daraltan downgrade veri incelemesi olmadan çalışmaz.
   M4 Windows'ta varsayılan `bash` Docker bulunmayan WSL'e gitti; Git Bash kullanıldı. MSYS yol dönüşümü test çıktılarını yanlış klasöre taşıdı; yalnız oluşturulan kanıt dosyaları doğrulanıp Git dışı outputs'a taşındı, sonraki çağrılarda argüman önekleri dışlandı.
   **GÖZLEM**
   M5 952.320.044 byte, 310 saniye/192 kHz/8 kanal kaynakta worker modülü + dosya/örnek çıkarma tepe belleği 213,39 MiB; mono analiz 119.040.044 byte, hafıza örneği 60 saniye/23.040.044 byte kaldı.
   M6 Uzun kaynakların her penceresindeki tüm ses örnekleri okundu; 4 MiB aktarım, iki gerçek HTTP süreç kimliği, hash/ACK, idempotent tekrar ve kaldığı yerden devam gözlendi. GPU/model çağrısı sıfırdı.
   **AÇIK**
   M7 213,39 MiB ölçümü HTTP/model çıkarımını kapsamaz; bütün worker için 256 MiB yeterliliği, 310 saniyelik gerçek GPU çıkarımı ve konuşmacı doğruluğu ana teslimde ayrı doğrulanmalıdır.
   M8 Tam profil kapısı, Spark ARM64, Apple ve temsilî Türkçe/50 kişi kabulü bu alt koşumun kanıtı değildir; eski [70 saniyelik ölçümler](README.md) tarihsel kanıt olarak korunur.
   **YAN-ETKİ**
   M9 Kaynak/taşıma/tip sınırları, toplantı politika metadatası, migration, testler, plan/görev ve dokümanlar güncellendi; geçici test DB'leri ve test sesleri temizlendi. Gerçek uygulama sesleri/profilleri silinmedi.
