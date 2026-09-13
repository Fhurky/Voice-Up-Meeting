# Koşum raporu — 2026-09-13 · Türkçe görüşme kaynaklarının edinimi, hazırlanması ve referans hizalama tanılaması

1. Sonuç: Hazırlayıcı, kaynak bütünlüğü ve altı gerçek görüşmenin ses çıktısı doğrulandı — birim 18 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Sabit profil `kt-vibecoding-python-web-v2`; yerel Windows Python 3.12.10, pytest 8.4.2 ve mevcut `voiceup-inference-meeting:local` imajındaki PyAV 18.0.0 kullanıldı.

   | Komut veya gerçek sınır | Ortam ve gözlenen sonuç |
   | --- | --- |
   | `.venv\Scripts\python.exe -m pytest tests/test_prepare_turkish_meeting_evaluation.py -q` | İlk kırmızı koşumda eksik hazırlayıcı nedeniyle 15 başarısız; uygulama sonrası yeşil. Zaman politikası için ek iki test önce başarısız, ardından geçti. Son dar koşum 18/18 başarılı. |
   | `.venv\Scripts\python.exe -m ruff check scripts/prepare-turkish-meeting-evaluation.py tests/test_prepare_turkish_meeting_evaluation.py` | Son koşum `All checks passed!`. |
   | `.venv\Scripts\python.exe -m ruff format --check scripts/prepare-turkish-meeting-evaluation.py tests/test_prepare_turkish_meeting_evaluation.py` | İlk kontrolde bir dosya biçimlendirme istedi; biçimlendirme sonrası son koşum `2 files already formatted`. |
   | `.venv\Scripts\python.exe scripts/prepare-turkish-meeting-evaluation.py --download` | Resmî HTTPS kaynağından 25 dosya, 244.542.070 bayt; tüm sabit upstream boyut/Git blob SHA-1/LFS SHA-256 değerleri doğrulandı. |
   | `.venv\Scripts\python.exe scripts/prepare-turkish-meeting-evaluation.py --verify` | Yerel manifest ve 25 dosyanın içerik hashleri yeniden doğrulandı; ağ gerekmedi. |
   | `docker run --rm --network none --pull never --entrypoint python --mount 'type=bind,source=<yerel çalışma dizini>,target=/workspace' --workdir /workspace voiceup-inference-meeting:local scripts/prepare-turkish-meeting-evaluation.py --prepare` | Kaynak mutlak konumu gizlilik için yer tutucuyla gösterildi. Ağ kapalı, mevcut imaj ile 6 WAV ve protokol oluştu; yeni paket/model indirilmedi. |
   | Gerçek WAV dosyalarında Python `wave` ve SHA-256 denetimi | 6/6 dosya: 16 kHz, tek kanal, 16 bit PCM, 2.880.000 örnek, 180 saniye; içerik hashleri protokolle aynı. |
   | Aynı çevrimdışı imajda standart girdiden `python -`: `decode_channel`, `load_silero_vad(onnx=False)`, `get_speech_timestamps` | 12 tekil kanalın ilk 180 saniyesi CPU'da; eşik 0,5, sessizlik 300 ms, dolgu 100 ms, asgari konuşma 120 ms; zaman kaydırması/parametre araması yapılmadı. |
   | Yayımlanan etkinlik ile yerel Silero çıktısının 62,5 ms kare merkezinde karşılaştırılması | 34.560 kare: 16.116 doğru pozitif, 17.208 doğru negatif, 1.141 yanlış pozitif, 95 yanlış negatif; uyum %96,4236. [Toplu kanıt](source-alignment.json). |
   | Araştırma bağlantılarının ve önceden edinilmiş birincil kaynak iddialarının salt okunur kontrolü | Araştırmada 41 dış bağlantı (35 benzersiz) geçerli HTTPS biçiminde; 6 yerel hedef mevcut. Bu raporun 7 yerel hedefi de mevcut. Canlı uzak HTTP durumları tekrar ölçülmedi; yeni kaynak taraması yapılmadı. |

3. Maddeler:

   **KUSUR**

   M1 Kaynak WebM damgaları sıçrayıp tekrar ediyor; ilk PyAV denetimi `overlapping_audio_timestamps` ile durdu. DÜZELTİLDİ: kabul edilen [Decision 10](../../../specs/speaker-identity/PRDs/009-turkish-evaluation-ledger/PRD.md) ve [örnek saati regresyonu](../../../tests/test_prepare_turkish_meeting_evaluation.py).

   **TUZAK**

   M2 `decoded-sample-clock-v1` çözülmüş örnek/sessizlik sırasını korur; paket damgalarıyla ses eklenmez veya üst üste yazılmaz. Kaynak hizası `unverified-source-timestamps` olarak kalır.

   M3 Tam kayıt denetiminde bir kanal yayımlanan VAD sonundan 2,046 saniye kısa; diğer 11 kanal 30 ms içinde uyuştu. Bitiş uyumu, kayıt içi hizanın doğrulandığı anlamına gelmez.

   M4 Kesme sınırını aşan beş cümle referans metne alınmadı; bunların konuşması seste/hipotezde kalabilir ve tanılayıcı metin skorunu etkileyebilir.

   **GÖZLEM**

   M5 On iki kanaldaki otomatik referans uyumu %94,4444–98,75 aralığında; %96,4236 ortalama insan, kimlik veya kesin ayrıştırma doğruluğu değildir. [Kaynak niteliği ve yöntem](../../../plans/TURKISH_DATASET_RESEARCH.md).

   M6 Altı gerçek görüşmenin toplam 18 dakikalık seçimi altı kişiyi ve 2.341 boşlukla ayrılmış referans sözcüğü kapsar; 50 kişi başarısı veya model iyileşmesi iddiası yoktur.

   M7 Kaynak manifest SHA-256 `02c9494ad9137d642258f7cc3a4720b4f3821b3fc2368d22699d33e08da6ea4b`; hazırlanan protokol SHA-256 `483e4810b3cd4559f9f00ce232deb12974e483be280e012f6117324911e7414c`.

   **AÇIK**

   M8 Bu hazırlama raporu L1 kanıtıdır; ürün HTTP/model deneyleri ve tam profil kalite kapısı kendi genel raporlarında değerlendirilir. Buradan ürün L2/L3 başarısı çıkarılmaz.

   M9 İnsan denetimli zaman/metin referansı ve yaklaşık 50 kişinin farklı oturumlarda tekrar ettiği Türkçe toplantı kapsamı bu veri paketinde doğrulanmadı.

   **YAN-ETKİ**

   M10 [Hazırlayıcı](../../../scripts/prepare-turkish-meeting-evaluation.py), [18 test](../../../tests/test_prepare_turkish_meeting_evaluation.py), [araştırma](../../../plans/TURKISH_DATASET_RESEARCH.md) ve 009 `Decision 10` eklendi; sabit uygulama teknolojileri değişmedi.

   M11 Ham kaynaklar `data/turkish/real-turnturk/<revision>/`, özel protokol/WAV/hizalama dosyaları `outputs/2026-09-13-turkish-evaluation/` altında; bu konumların Git tarafından yok sayıldığı doğrulandı.

   M12 Çalışan model servisi yeniden başlatılmadı; yeni bağımlılık kurulmadı, kaynak dosyalar ve farklı mevcut çıktıların üzerine yazılmadı.
