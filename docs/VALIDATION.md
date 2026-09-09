# İlk sürüm doğrulama kaydı

8 Eylül 2026; Windows, Python 3.12.10. Bu belge yazılım doğrulamasını, gerçek model
çıkarım kontrolünü ve henüz yapılmamış toplantı doğruluğu ölçümünü ayırır.

## Doğrulananlar

- `uv run --no-sync pytest`: **208 test geçti**.
- `uv run --no-sync ruff check src tests scripts`: geçti.
- `uv run --no-sync ruff format --check src tests scripts`: geçti.
- `uv build`: kaynak dağıtımı ve wheel üretildi.
- `voiceup demo`: yeniden açılan SQLite hafızasında ilk beş kimlik korundu; altıncı
  kimlik eklendi. Vektörler sentetik; akustik doğruluk sonucu değildir.
- `voiceup evaluate`: örnek karar dosyasından sorgu bazlı metrik raporu üretildi.
- `uv sync --extra diarization`: opsiyonel bağımlılıklar kuruldu; pyannote 4.0.7
  `Pipeline` içe aktarması, normal örtüşmeli `Annotation` arayüzü ve gerçek pyannote
  `Audio` sınıfının bellekten `waveform` girişi kontrol edildi.
- Gerçek 2.87 saniyelik dosyayla CLI enrollment denemesi, yetersiz temiz süre nedeniyle
  beklenen biçimde reddedildi; kişi profili oluşturulmadı.

## Gerçek model denemesi

```powershell
uv run --no-sync python scripts/smoke_models.py --download-samples --output outputs/real-model-smoke.json
```

Resmî SpeechBrain `v1.1.1` deposunun üç kısa örneği indirildi ve kaynak dosya hashleri
doğrulandı. Gerçek Silero VAD ve sabit revision'daki ECAPA modeli CPU'da çalıştırıldı;
her örnek için sonlu, normalize, 192 boyutlu embedding çıkarıldı. Geçici SQLite
veritabanı kapatılıp tekrar açıldığında kimlikler ve karar değişmedi.

| Kontrol | Gözlenen sonuç |
| --- | --- |
| Aynı konuşmacı, iki farklı kısa dosya | Kosinüs benzerliği yaklaşık **0.7295** |
| Farklı konuşmacı dosyasıyla karşılaştırma | Kosinüs benzerliği yaklaşık **0.0060** |
| Varsayılan `0.75` kabul eşiğiyle aynı kişi sorgusu | **`ambiguous`**; eşik altında kaldı |
| Veritabanı yeniden açılması | Aynı kişiler, aynı skorlar, aynı karar |

Bu sonuç modelin ses özelliklerini çıkardığını ve kayıt mekanizmasının çalıştığını
gösterir. **Başarılı bir kimlik kabulü veya onlarca kişide doğruluk kanıtı değildir.**
Tek kısa örneği geçirmek için varsayılan eşik değiştirilmedi. Model ve karar eşikleri,
ayrı geliştirme ve kör test kayıtlarıyla seçilecek.

Örnekler yaklaşık 2–3 saniyedir; bu teknik kontrol doğrudan Registry'ye kayıt yaparak
uygulamanın en az 10 saniyelik enrollment kapısını bilinçli atlar. Üretim akışının veri
kalitesini doğrulamaz. Hashler, örnek kaynak adresleri, VAD aralıkları, paket sürümleri
ve ham kararlar `outputs/real-model-smoke.json` içindedir. Bu yerel çıktı ve sesler Git'e
alınmaz; kontrol betiği yeniden üretim içindir.

## Açık kalanlar

- Türkçe ve farklı mikrofon/oturum kayıtlarında 5/10/20/50 kişilik doğruluk ölçümü.
- Community-1'in model erişimi tamamlanarak gerçek karışık kayıtta çalıştırılması;
  adaptör testleri model çıkarımının yerine geçmez.
- Otomatik diarization DER ve kalıcı kimlikte süre ağırlıklı hata ölçümü.
- CUDA kurulumu, GPU performansı ve canlı işleme gecikmesi.
- Üretim veri yönetimi, profil düzeltme geçmişi ve toplantı platformu entegrasyonu.

Windows'ta pyannote içe aktarılırken TorchCodec/FFmpeg DLL uyarısı gözlendi. Bu adaptör
dosyayı SoundFile ile önceden okuyup `waveform`/`sample_rate` olarak verir; pyannote'un
önerdiği bellekten giriş yolunu kullanır. Dahili dosya çözücüsü çalışıyor kabul edilmez.
Bellekten ses giriş kontrolünün çıktısı `outputs/diarization-environment.json` içindedir.

Model araştırması [MODEL_RESEARCH.md](MODEL_RESEARCH.md), deney protokolü
[EVALUATION_PLAN.md](EVALUATION_PLAN.md) içindedir.
