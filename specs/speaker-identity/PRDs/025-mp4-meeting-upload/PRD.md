# PRD — MP4 toplantı yükleme

Status: Accepted

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [025 — mp4-meeting-upload](../../roadmap.md)
Profil: `kt-vibecoding-python-web-v2`; şema profili `sqlalchemy-alembic`.
Kaynak ve kabul (30 Ekim 2026): Kullanıcı uygulamanın MP4 toplantı kayıtlarıyla uyumlu olmasını açıkça istedi. Yöntem
Decision 1'dedir; kullanıcıya bildirilmiştir.

## Amaç ve önceki durum

Toplantı yükleme yalnız WAV ve FLAC kabul eder. Toplantı kayıtları çoğunlukla MP4 olarak gelir. Hedef: kullanıcının
MP4 seçip başka bir araç kullanmadan toplantıyı işleyebilmesi.

## Kararlar

Decision 1: Ses tarayıcıda çıkarılır. Dosya tarayıcının yerel `decodeAudioData` yeteneğiyle çözülür, 16 kHz tek kanal
PCM16 WAV yapılır ve mevcut 002 hash'li yükleme akışıyla gönderilir. Sunucu, API, şema, worker ve bağımlılık değişmez.
Sunucuda dönüştürme yeni bir bağımlılık kaydı, imaj değişikliği ve yeni iş aşaması gerektirirdi.

Decision 2: Görüntü sunucuya gönderilmez ve saklanmaz; sunucuya yalnız ses gider. Kaynak olarak saklanan dosya bu WAV'dır,
özgün MP4 değildir; ses önizleme ve doğrulama mevcut WAV yolundan çalışır.

Decision 3: `.mp4` ve aynı kapsayıcıyı kullanan `.m4a` kabul edilir. Giriş sınırı 2 GiB, ses sınırı 4 saattir. Ses izi yoksa,
tarayıcı kodeği çözemiyorsa veya bellek yetmezse kullanıcıya açık bir hata gösterilir, toplantı oluşturulmaz.

Decision 4: Sınır: dosya çözülürken tamamı tarayıcı belleğine alınır; çok uzun videolarda bellek yetmeyebilir. Parça parça
çözme, ihtiyaç ölçümle görülürse ayrı PRD olur. Yeni yetenek yalnız dosya yükleme formuna eklenir; profil kaydına eklenmez.

## Gereksinimler

Requirement 1: `lib/mediaAudio.ts`: çözme, kanal ortalama, kırpma ve WAV üretimi; birim testleriyle.

Requirement 2: `MeetingUploadForm` MP4 kabul eder, çözme sırasında durum gösterir ve yeniden denemede dosyayı tekrar çözmez.
Hata metinleri ve yardım metni TR/EN güncellenir.

Requirement 3: Kalıcı tarayıcı senaryosu AAC çözebilen bir tarayıcıyla MP4 yükler; görüntünün gönderilmediğini doğrular.

## Katmanlar

Şema, API, OpenAPI, worker, vektör, gözlemlenebilirlik ve Kubernetes: N/A — yalnız ön yüz ve tarayıcı senaryosu değişir.

## Kabul ölçütleri

- [ ] Birim testleri ve tam kalite kapısı geçer.
- [ ] Gerçek MP4 tarayıcıda yüklenir, toplantı başarıyla işlenir; sunucuya yalnız WAV gider.
- [ ] Kullanıcının 4 konuşmacılı MP4 kaydı işlenir (L3).
