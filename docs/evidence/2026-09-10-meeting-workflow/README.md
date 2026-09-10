# Koşum raporu — 2026-09-10 · Konuşmacılı toplantı dökümü için mevcut durum ve sağlayıcı keşfi.

1. Sonuç: Kullanıcı akışı kabul edilen 002 kapsamına işlendi; özellik henüz uygulanmadı — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: 1 (M4).
2. Koşulan: Yerel kaynak/şema/spec incelemesi, mevcut SSH üzerinden Spark inference paket ve model dizini metaverisi, resmî model kartları ve paket indeksleri; model çıkarımı veya kurulum çalıştırılmadı. Sabit profil `kt-vibecoding-python-web-v2`.

   | İnceleme | Gözlem |
   | --- | --- |
   | Web/API/işçi | Mevcut ürün yalnız tek konuşmacılı WAV/FLAC kayıt ve kimlik eşleştirmesi sunuyor; 50 MiB/120 saniye sınırı. |
   | Araştırma çekirdeği | `src/voiceup/backends.py` içinde Community-1 adaptörü, `pipeline.py` içinde temiz kanıt/kimlik birleştirme var; bunlar web ürününde çevrimdışı kabul edilmiş bir toplantı servisi veya transkript değildir. |
   | Spark metadata | Torch 2.8.0+cu129, TorchAudio 2.8.0, SpeechBrain 1.1.1, Silero 6.2.1. pyannote.audio, TorchCodec, Transformers, openai-whisper ve faster-whisper yok. |
   | Model depoları | Hazırlanmış ürün paketinde ECAPA/Silero var; Community-1 ve Whisper large-v3 yok. `whisper-tiny` isimli eski cache dizini tam/çalışır model kanıtı sayılmadı. |
   | Resmî HF metadata | Community-1 revision `3533c8cf8e369892e6b79ff1bf80f7b0286a54ee`, `gated=auto`, CC-BY-4.0; Whisper large-v3 revision `06f233fe06e710322aca913c1bc4249a0d71fce1`, ungated, kart lisansı Apache-2.0. |
   | ARM64 kaynakları | Pyannote 4.0.7, TorchCodec ≥0.7 ister; Torch 2.8 ile eşleşen 0.7 için incelenen PyPI/resmî CPU/CUDA12.9 indekslerinde Linux aarch64/cp313 wheel bulunamadı. |

   Kaynaklar: [Community-1](https://huggingface.co/pyannote/speaker-diarization-community-1),
   [Whisper large-v3](https://huggingface.co/openai/whisper-large-v3),
   [Pyannote bağımlılıkları](https://raw.githubusercontent.com/pyannote/pyannote-audio/4.0.7/pyproject.toml),
   [TorchCodec uyum tablosu](https://github.com/pytorch/torchcodec#compatibility-with-torch-versions),
   [tarayıcı kayıt standardı](https://www.w3.org/TR/mediastream-recording/).

3. Maddeler:

   **KUSUR** — yok
   **TUZAK**
   M1 Mevcut profilsiz `enroll` eşleşmeden bağımsız profil yaratır; otomatik toplantı hafızası için tenant kilidi altında yeniden eşleme ve tek enrollment bağı gerekir. Mevcut `identify` değiştirilmez.
   M2 WebM mikrofon çıktısına WAV uzantısı vermek çalışmaz; native kayıt ve çevrimdışı decoder birlikte kabul edilmeli. Mikrofon uzak toplantı sesini kendiliğinden yakalamaz.
   **GÖZLEM**
   M3 Dosya/mikrofon → konuşmacılı transkript → güvenilir yeni kişi hafızası [002 PRD](../../../specs/speaker-identity/PRDs/002-long-recording-analysis/PRD.md), plan ve görevlere işlendi; bütün uygulama/test görevleri açıkça bekliyor.
   **AÇIK**
   M4 Model sahibi Community-1 koşullarını kullanıcı hesabında kabul etmeyi ve okuma erişimi ister; kullanıcıdan `.env` içine `HF_TOKEN` eklemesi istendi, erişim henüz doğrulanmadı. Token sohbete istenmedi. ← KARAR
   M5 ARM64 TorchCodec/decoder paketleme, bağımlılık kabulü ve gerçek sağlayıcı çıktı sözleşmesi açık; model erişimi bunların tek başına tamamlanması değildir. Yeni model veya paket kurulmadı.
   M6 Yeni toplantı API/UI/şema/worker, gerçek mikrofon, çok kişili döküm, kalıcı geri dönüş, 1/2/4 saatlik kaynak ve Türkçe kalite testleri henüz çalışmadı; L1/L2 özellik kanıtı yoktur.
   **YAN-ETKİ**
   M7 Yalnız 002 gereksinim/plan/görevleri, domain/yol haritası, 003 sıra açıklaması ve kullanıcı akışı/strateji belgeleri güncellendi. Çalışan uygulama, veri, model, ayar, bağımlılık ve Git yayını değiştirilmedi.

Belge güncellemesinden sonraki [tam kapı raporu](quality-gate-report.md) mevcut
pilotun 136 başarılı testini kaydeder; yeni toplantı özelliğinin çalışma kanıtı değildir.
