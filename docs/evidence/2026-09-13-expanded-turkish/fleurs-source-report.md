# Koşum raporu — 2026-09-13 · FLEURS Türkçe resmî test bölümünün güvenli hazırlanması

1. Sonuç: 743 özgün test sesi ve referansı hazır, son çevrimdışı tekrar aynı manifesti üretti — birim 36 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows, Python 3.12 hazırlama ortamı; sabit ürün profili `kt-vibecoding-python-web-v2`, üretim yığını ve bağımlılıklar değişmedi.

   | Komut / sınır | Gözlenen sonuç |
   | --- | --- |
   | `.venv/Scripts/python.exe -m pytest tests/test_prepare_fleurs_turkish.py -q` ilk kırmızı koşum | Uygulama dosyası yokken 26 başarısız, 0 başarılı; eksik davranış gözlendi. |
   | Aynı dar test, ilk uygulama | 26 başarılı, 0 başarısız. |
   | İndirme/yönlendirme ve kapsam regresyonları sonrası dar test | 36 başarılı, 0 başarısız; son kanıt `outputs/2026-09-13-expanded-turkish/fleurs-source-tests.xml`. |
   | `.venv/Scripts/python.exe scripts/prepare-fleurs-turkish.py --download` | Çıkış 0; hashli resmî TSV ve 464.259.241 bayt ses arşivi indirildi, 743 ses hazırlandı. |
   | `.venv/Scripts/python.exe scripts/prepare-fleurs-turkish.py` | Çıkış 0; son kaynak koduyla çevrimdışı tam doğrulama/tekrar, manifest hash'i aynı. |
   | `ruff check` ve `ruff format --check`, yeni hazırlayıcı ve testi | Başarılı; iki dosya biçimi geçerli. |

3. Maddeler:

   **KUSUR**

   M1 Özgün WAV, IEEE float32 format 3 kullanıyor; standart `wave` açmıyor. Dönüştürmek yerine RIFF/ses örneği doğrulaması eklendi ve özgün baytlar korundu (`test_float_audio_preserved_and_sample_count_verified`).

   **TUZAK**

   M2 Test TSV'sindeki 743 satırın tamamı `MALE`; 329 farklı `id`, cümle kimliğidir. Kadın sesi, 743 kişi, kararlı kimlik veya toplantı hafızası kapsamı çıkarılamaz.

   M3 FLEURS okuma konuşmasıdır. Kart train konuşmacılarını dev/test'ten ayırır; dosyalarda kişi/oturum kimliği olmadığı için bu ayrım yerel olarak doğrulanamaz, dev/test kişi ayrışması iddia edilmez.

   M4 SHA-256 arşiv için yayıncı LFS kaydıdır; TSV için sabit resmî HTTPS revizyonundan gözlenen bayt hash'idir. `transcription` sütunu referanstır; `raw_transcription` farklıdır.

   **GÖZLEM**

   M5 Bütün 743 WAV için mono 16 kHz float32, RIFF uzunluğu, örnek sayısı, sonlu örnekler, tekil ses hash'i ve TSV eşlemesi doğrulandı; toplam 150.083.520 örnek, 9.380,22 saniye, 3,84–36,84 saniye/klip.

   M6 Çıktı `data/turkish/fleurs-tr-test-v1/manifest.json`; SHA-256 `77fa49973ee399d0378842ef9697697a54a29fb9a5f71a04ea55f6bf818624f8`. Kaynak manifesti SHA-256 `9e57cfefe7f0e8efb3298bb79fd04fc849e94794f684e43415969a6d7e0cdda6`.

   M7 Yol geçişi, sembolik/fiziksel link, bilinmeyen/eksik/tekrar üye, bozuk/kısa/uzun indirme, güvensiz yönlendirme, değiştirilmiş veri ve mevcut çıktı çatışması testlerle reddedildi.

   **AÇIK**

   M8 Bu hazırlama koşumu model çıkarımı yapmadı; kelime hata oranı ve toplam ürün doğruluğu ayrı gerçek model koşumunda ölçülür. 50 Türkçe konuşmacı ve doğal toplantı kabulü bu kaynaktan kanıtlanamaz.

   **YAN-ETKİ**

   M9 Yeni hazırlayıcı, 36 test ve bu toplu rapor eklendi; kaynak ses/TSV ve referans metinleri yalnız Git dışındaki `data/` içinde. Mevcut veri ve manifestler değiştirilmedi; yeni paket/model indirilmedi.

## Sabit kaynaklar ve kullanım

- [Google FLEURS veri kartı](https://huggingface.co/datasets/google/fleurs): CC BY 4.0; FLEURS, Conneau ve diğerleri, 2022.
- [Resmî TensorFlow Türkçe bölüm sayıları](https://www.tensorflow.org/datasets/catalog/xtreme_s#xtreme_sfleurstr_tr): train 2.526, validation 338, test 743.
- [Sabit test arşivi](https://huggingface.co/datasets/google/fleurs/resolve/70bb2e84b976b7e960aa89f1c648e09c59f894dd/data/tr_tr/audio/test.tar.gz): 464.259.241 bayt, SHA-256 `a7db7a681e4460d2922626bf2037ddc1a9146efba27d78bfc9543250eabc3a09`.
- [Sabit test TSV](https://huggingface.co/datasets/google/fleurs/resolve/70bb2e84b976b7e960aa89f1c648e09c59f894dd/data/tr_tr/test.tsv): 447.909 bayt, SHA-256 `52adb452a258976a2428da88fe7ac4d9bce27d4c10f9358ba3acf48a9b59577a`.
- [Resmî tarihsel loader sütun sözleşmesi](https://huggingface.co/datasets/google/fleurs/blob/1712be137a62f4b1a69ce0c4820c0975bc7b6067/fleurs.py): kimlik, dosya, özgün metin, normalize metin, kullanılmayan sütun, örnek sayısı, cinsiyet etiketi.

```powershell
.venv/Scripts/python.exe scripts/prepare-fleurs-turkish.py --download
# Subsequent preparation verifies existing files offline and preserves their bytes.
.venv/Scripts/python.exe scripts/prepare-fleurs-turkish.py
```

Veri manifesti `voiceup-fleurs-tr-test-v1` / `frozen-test` olarak bütün test
bölümünü TSV sırasıyla dondurur. Ham WAV sesler yeniden kodlanmaz; kişi kimliği
üretilmez. İndirilen sıkıştırılmış kaynaklar toplam 464.707.150 bayttır.
