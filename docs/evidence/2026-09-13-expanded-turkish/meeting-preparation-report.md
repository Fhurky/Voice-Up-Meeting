# Koşum raporu — 2026-09-13 · Kullanılmamış Türkçe görüşme pencereleri ve protokol regresyonları

1. Sonuç: İki sabit pencerede 12 yeni kesit hazırlandı; geçmiş altı WAV ve protokol baytları aynen yeniden üretildi — birim 103 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows yerel Python, sabit `kt-vibecoding-python-web-v2` ve ağ/GPU erişimi olmayan mevcut `voiceup-inference-meeting:local` imajındaki PyAV 18.0.0.

   | Koşum | Gözlenen sonuç |
   | --- | --- |
   | Önce kırmızı: hazırlayıcı + Türkçe yürütücü testleri | 45 mevcut başarılı, yeni davranış için 19 başarısız; başlangıç kaydırma, sabit seçim, kaynak bağlama ve devam sözleşmesi henüz yoktu |
   | İlk yeşil: aynı iki dosya | 64 başarılı, 0 başarısız |
   | Son regresyon: hazırlayıcı + Türkçe yürütücü + mevcut toplantı yürütücüsü | 103 başarılı, 0 başarısız, 0 atlanan; JUnit: `outputs/2026-09-13-expanded-turkish/meeting-regressions.xml` |
   | Ruff lint ve biçim denetimi | Değişen iki Python aracı ve iki test dosyası başarılı |
   | Gerçek CPU hazırlama: `--preset window300` | 6 WAV, her biri 300 saniye, toplam 1.800 saniye; 4.030 boşlukla ayrılmış referans sözcük, sınırı kesen 12 ifade |
   | Gerçek CPU hazırlama: `--preset window600` | 6 WAV, her biri 300 saniye, toplam 1.800 saniye; 4.140 boşlukla ayrılmış referans sözcük, sınırı kesen 12 ifade |
   | Gerçek yürütücü dosya doğrulaması | İki protokol ve 12 WAV bütünlük/biçim/süre/kaynak/zamanlama bağlarıyla kabul edildi |
   | Eski `development` seçiminin ayrı dizinde yeniden üretimi | Önceki `protocol.json` ve altı WAV: 7/7 SHA-256 eşitliği; eski dosyalar üzerine yazılmadı |

   Son test komutu:

   ```text
   .venv/Scripts/python.exe -m pytest tests/test_prepare_turkish_meeting_evaluation.py tests/test_turkish_meeting_evaluation.py tests/test_run_meeting_evaluation.py -q --junitxml=outputs/2026-09-13-expanded-turkish/meeting-regressions.xml
   ```

   Hazırlama komutu, her pencere için ayrı çıktı diziniyle çalıştırıldı:

   ```powershell
   docker run --rm --pull never --network none --entrypoint python --workdir /workspace --mount "type=bind,source=$PWD,target=/workspace" voiceup-inference-meeting:local scripts/prepare-turkish-meeting-evaluation.py --prepare --preset window300 --output outputs/2026-09-13-expanded-turkish/fixtures-300
   docker run --rm --pull never --network none --entrypoint python --workdir /workspace --mount "type=bind,source=$PWD,target=/workspace" voiceup-inference-meeting:local scripts/prepare-turkish-meeting-evaluation.py --prepare --preset window600 --output outputs/2026-09-13-expanded-turkish/fixtures-600
   ```

3. Maddeler:

   **KUSUR**

   M1 Başlangıç dışı seçim eksikti; çözülmüş örnekler parça sınırlarında korunarak atlama, iki kenardan etkinlik kırpma/kaydırma ve yalnız tamamen içerideki metni seçme eklendi. Düzeltme: `prepare-turkish-meeting-evaluation.py`; koruma: `test_offset_reference_*`, `test_pcm_selection_*`.

   M2 Yeni pencerenin eski ses veya farklı kaynak diye etiketlenmesi engellendi; sabit kaynak revision/hashleri, pencere, örnek başlangıcı, kapsam ve zayıf referans politikası doğrulanıyor. Düzeltme: `run-turkish-meeting-evaluation.py`; koruma: `test_new_protocol_*`, `test_new_source_binding_*`, `test_resume_cannot_change_preset_*`.

   **TUZAK**

   M3 Yeni 60 dakika, aynı altı gerçek kişinin aynı altı kaynak görüşmesinden gelir; yeni kişiler veya bağımsız oturumlar değildir. İlk 180 saniye ve iki yeni pencere zaman bakımından ayrıdır.

   M4 `decoded-sample-clock-v1`, `unverified-source-timestamps`, otomatik etkinlik ve doğrulanmamış metin niteliği korunur. Sınırı kesen ses/hipotez durur, ilgili tam ifade referanstan çıkar; metin skoru bu nedenle tanısaldır.

   M5 `observed_audio_seconds`, terminal sonucu gözlenen kayıtların yüklenen ses süresidir; başarısız terminal kaydı da sayılır. Başarılı metne çevirme süresi veya bütün kaydın işlendiği garantisi değildir.

   **GÖZLEM**

   M6 Yeni kaynak protokolleri `voiceup-real-turnturk-window300-v1` ve `voiceup-real-turnturk-window600-v1`; kimlik denklemleri ve altı yeni/altı bilinen görünüm paydası değişmediği için `metrics_protocol=voiceup-real-turnturk-v1` korunur.

   M7 Son kod hashleri: hazırlayıcı `ac9deb52dd551b95b667f7ff94321731caae82dd20bfec9dc3c91735feef8029`; yürütücü `68e34aff9a44861bf88666385d08d8458a12b5ebc7a05d2781f46aa7976308d5`.

   M8 Protokol hashleri: window300 `45c468fff29579b2ff2f0b0388300c7871fa1de7d4b026e0fdac10c52e630240`; window600 `63c2f30133120dd012070d90ea9b36ef9ea8a9550f323b189e79a265bb83a6b7`; geçmiş protokol aynen `483e4810b3cd4559f9f00ce232deb12974e483be280e012f6117324911e7414c`.

   M9 Her iki yeni seçimde kişi başına örtüşmesiz kaynak etkinliği en az 43,3125 / 44,375 saniyedir; modelin temiz konuşma filtresi farklı bir ölçümdür. Hazırlama, model başarısı değildir.

   **AÇIK**

   M10 Bu rapor hazırlama ve otomatik regresyon kanıtıdır; gerçek uygulama/GPU hafıza sonuçları, tam profil ve güvenlik kapıları ana koşumda ayrı kaydedilir. Burada 50 kişi, insan referanslı ayrıştırma veya başka cihaz başarısı iddia edilmez.

   **YAN-ETKİ**

   M11 İki araç ve iki test dosyası güncellendi. Yeni özel kesitler `outputs/2026-09-13-expanded-turkish/fixtures-300`, `fixtures-600`; eski seçimin ayrı doğrulama kopyası `legacy-reproduction` içindedir. Ham ses/metin Git'e eklenmedi; veri/hesap silinmedi, GPU veya veritabanı değiştirilmedi.
