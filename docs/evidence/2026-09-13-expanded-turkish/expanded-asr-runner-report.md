# Koşum raporu — 2026-09-13 · Geniş Türkçe ASR hazırlığı ve kesintiden devam sınırları

1. Sonuç: Sabit `kt-vibecoding-python-web-v2` profilinde değerlendirme hazırlığı ve
   gerçek dosya regresyonları başarılı — birim 46 başarılı / tarayıcı 0 başarılı /
   atlanan 2; karar bekleyen: yok. Windows'ta yetki nedeniyle atlanan iki sembolik
   bağ sınırı aynı Linux imajında gerçek dosyalarla ayrıca başarılıdır.
   Windows paketi toplam 48 testten oluşur; Linux doğrulaması ayrıca iki sınırdır.
   Bu rapor model doğruluğu veya canlı GPU başarısı
   iddiası taşımaz; gerçek çıkarım sonuçları ayrı deneylerdir.
2. Koşulan: Windows, yerel Python 3.12; üretim backend profili Python 3.13 olarak
   korunmuştur. Yeni bağımlılık/model indirilmemiştir.

   | Koşum | Gözlenen sonuç |
   | --- | --- |
   | `pytest tests/test_expanded_turkish_asr.py -q`, ilk RED | Yeni değerlendirici bulunmadığından 17 kurulum hatası. |
   | İlk uygulama ve test düzeltmesi | İlk çalışmada 11 başarılı / 6 taklit kurulum hatası; özgün imzalarla yeniden taklit oluşturulduktan sonra 17 başarılı. |
   | İlk yeni + eski değerlendirici regresyonu | 36 başarılı. |
   | Kesinti dosyası, süre ve gerçek günlük RED/GREEN | 18 başarılı / 3 kusur; geçici dosya devamı, süre bağı ve test CLI arama yolu düzeltildikten sonra 21 başarılı. |
   | Tamamlanmış rapor kaynak/model yeniden etiketleme RED | 22 başarılı / 3 kusur; kaynak/model/protokol alanlarının tümü güncel bağla doğrulanacak biçimde düzeltildi. |
   | Kaynak kilidi sonrası yeni + eski değerlendirici regresyonu | 25 yeni + 19 eski = 44 başarılı, 0 hata/atlanan; kesin kaynak manifesti kilidi eklendikten sonra aynı 44 test yeniden başarılı. |
   | Model çalışma hatası CLI RED/GREEN ve son birleşik koşum | Yeni CLI sınırı için 25 başarılı / 1 kusur; düzeltme sonrasında 26 yeni + 19 eski = 45 başarılı, 0 hata/atlanan. |
   | Büyük veri ön kontrolü RED/GREEN | Yanlış model dizininin geç kontrolü için 26 başarılı / 1 kusur / 2 Windows yetki atlaması; düzeltme sonrası 27 yeni + 19 eski = 46 başarılı / 2 atlanan. |
   | Gerçek Linux sembolik bağ sınırları | Dosya ve üst klasör sembolik bağı olmak üzere iki gerçek dosya sınırı reddedildi; ikisi de başarılı. |
   | Windows bind mount üzerinde yol kontrolü | Eski 5 klip 0,459 saniye; yeni 5 klip 0,121 saniye; yeni 2.433 klibin tamamı 17,204 saniye. Önceki tam geçiş ana koşumda yaklaşık altı dakika gözlendi. |
   | Ruff kontrolü ve biçim doğrulaması | İki Python dosyası başarılı. |
   | MediaSpeech arşivi salt okunur incelemesi | 2.513 eşli klip; 16 kHz mono; bozuk başlık, yinelenen ses hash'i ve eksik metin eşliği 0. |
   | `evaluate-expanded-turkish-asr.py prepare-mediaspeech --root data/turkish/mediaspeech-expanded-v1` | 2.433 klip / 34.852,1 saniye hazır; önceki 80 kimlik ve ses hash'i dışlandı. |
   | Kesin manifestleri yeni değerlendiriciyle okuma | MediaSpeech 2.433, FLEURS 743; iki sabit manifest hash'i başarılı. |

   Tekrar çalıştırma komutu (son JUnit dosyası ortak kanıt dizinine taşındı):

   ```powershell
   .venv/Scripts/python.exe -m pytest tests/test_expanded_turkish_asr.py tests/test_turkish_asr_dataset.py -q --junitxml=outputs/2026-09-13-expanded-turkish/expanded-asr-performance-tests.xml
   ```

3. Maddeler:

   **KUSUR**

   M1 Kesintiye uğrayan değerlendirmede önceki sağlam klipler yeniden hesaplanıyordu; ayrı atomik klip dosyaları ve açık `--resume` ile çözüldü (`test_interrupted_resume_skips_exact_durable_clips`).

   M2 Kesinti sonrası kalan geçici atomik dosya devamı engelliyordu; yalnız kesin geçici dosya biçimi korunarak yok sayılır (`test_recovery_preserves_stale_atomic_temporary_file`).

   M3 Özel checkpoint süresi ve tamamlanmış raporun kaynak/model alanları tekrar etiketlenebiliyordu; gerçek ses süresi ve bütün rapor bağları doğrulanır (`test_checkpoint_duration_is_bound_to_actual_audio`, `test_completed_report_cannot_relabel_cached_inference`).

   M4 Modelin `RuntimeError` hatası CLI'de özel hata/iz bilgisi yazabiliyordu; gerçek alt süreç testi, temiz hata mesajını ve 0/N eksik rapor/günlük kaydını doğrular (`test_cli_model_runtime_error_is_sanitized_and_records_incomplete`).

   M5 Büyük kaynak listesindeki tekrarlanan `resolve`/`samefile` çağrıları ön kontrolü dakikalara uzatıyordu; her geçişte tekil yol/dosya kimliği kümeleri kullanılır. Yanlış model dizini kilitlerden önce reddedilir; içerik hash'i ve tam ses çözme kontrolleri korunur.

   **TUZAK**

   M6 Eski 40/40 manifesti büyütülmez; yeni protokol eski 80 dosya kimliğini ve ses hash'ini dışlar. Aynı arşiv ikinci bağımsız veri kaynağı sayılmaz.

   M7 Devam, kaynak manifesti/model manifesti/model dizini/çıkarım ve ölçüm kodu/deney kimliği/günlük yolu bağı değişince reddedilir; tamamlanmış rapor yeniden yazılmaz.

   M8 Klipler tek tek dayanıklı kaydedilir, toplu özel rapor her 100 klipte ve bitişte yazılır; sert kesintide tamamlanan klip dosyaları kalır. Tamamlanmayan deney WER'i boş ve planlı kapsam görünürdür.

   M9 Başlangıç ve devam sırasında tüm ses/metin hashleri ve ses başlıkları doğrulanır; yalnız kaynak dosyalarının yerini değiştirmeden çıktı dosyasına `--resume` eklemek yeterlidir. Ön kontrol ve çıkarım ilerlemeleri ayrı etiketlenir.

   **GÖZLEM**

   M10 Sabit kaynak manifestleri: MediaSpeech `e5439bc09b057af136bac6d85be1a511eea646c6f942fe519f06a7d0db3929ef`, FLEURS `77fa49973ee399d0378842ef9697697a54a29fb9a5f71a04ea55f6bf818624f8`.

   M11 Toplam WER aynı Türkçe normalizasyonla kliplerin kelime hatalarının toplam referans kelimelerine bölünmesidir; kaynak başına raporlanır. Performans düzeltmesinden sonra dondurulan değerlendirici SHA-256: `c6df5fa1c158db423df324f50900bd495a9ddef6ab54b7dbd606d259e5821310`.

   M12 Ön kontrolde durdurulan [ilk](mediaspeech-preflight-incomplete.json) ve [ikinci](mediaspeech-full-preflight-incomplete.json) kurulum denemeleri 0/2.433 kapsam ve boş WER ile korundu; çıkış 137, model hesaplaması başlamadı. İlk komuttaki model dizini de geçersizdi.

   **AÇIK**

   M13 Bu iki kaynak kalıcı kişi/oturum etiketi taşımadığından kişi F1'i, toplantı ayırma veya 50 kişi başarısı bu koşumdan çıkarılmaz. Tam profil ve güvenlik kapısı ana teslim raporunda ayrıca izlenir.

   **YAN-ETKİ**

   M14 Yeni değerlendirici/test dosyaları ve yok sayılan `data/turkish/mediaspeech-expanded-v1` altında 2.433 çift ses/metin dosyası oluşturuldu; eski arşiv/80 klip/manifest değiştirilmedi ve arşiv kopyalanmadı.

   M15 Testler geçici dizinlerde ses/checkpoint/günlük dosyası üretir; kök `results.md` veya gerçek GPU bu araç regresyonları sırasında kullanılmadı. İlk Linux tanı komutu stdin bağlı olmadığından çalışmadı; `-i` ile tekrarlanan komutun ölçümleri kullanıldı.
