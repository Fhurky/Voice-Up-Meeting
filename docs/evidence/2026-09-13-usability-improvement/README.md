# Kullanılabilirlik ve doğruluk incelemesi — 2026-09-13

Mevcut düzey **insan denetimiyle kullanılabilir yerel pilot**. Bu çalışma,
Türkçe parça sınırında sahte sözcük tekrarını düzeltir ve transkript satırından
kaynak sesi dinlemeyi ekler. Elli kişilik kusursuza yakın başarı veya yeni
genel model doğruluğu iddiası taşımaz.

[Kapsamlı plan](../../../plans/USABILITY_AND_ACCURACY.md),
[011 kabul kapsamı](../../../specs/speaker-identity/PRDs/011-meeting-audio-review/PRD.md)
ve [kullanıcı rehberi](../../tr/meeting-audio-review.md).

| Kanıt | Sonuç |
| --- | --- |
| [Tam kalite kapısı](quality-report.md) | 432 backend birim + 255 gerçek PostgreSQL + 158 frontend = 845 başarılı, test atlaması yok |
| [Türkçe sınır düzeltmesi](turkish-stitch-report.md) | Dar 62 test; korunmuş İngilizce kaynakta 28 sınır eşitliği; yeni genel WER iddiası yok |
| [Önizleme backend](audio-preview-backend-report.md) | 145 dar test; WAV/FLAC, sınır/yetki/lifecycle ve hafıza regresyonları |
| [Ön yüz](audio-review-frontend-report.md) | 64 dar test; tek oynatıcı, iptal, dil ve değişmez seçim |
| [Gerçek HTTP](live-preview-http-report.md) | 2 normal hesap, 12 toplantı, 182 beklenen işlem; 36 bölüm ve 12 tekrar kaynakla birebir |
| [Gerçek tarayıcı](browser-review-report.md) | Yeni 300 saniyelik RTX işi; TR/EN geniş/dar 4 oynatma; giriş/çıkış, sayfalama, tek oynatıcı |
| [Belge incelemesi](document-review-report.md) | 80 yerel bağlantı ve 11 kaynak/senaryo yolu doğru |

Dar paketler tam kapının alt kümesidir; sayılar toplanarak büyütülmez.
En yüksek gözlenen işlevsel kanıt L2; genel yayın/güvenlik ve L3 kullanıcı
kabulü açık. Güvenlik kapısı `gitleaks` yokluğunda durdu. Tarayıcı eklentisi
dosya seçimini reddetti; gerçek yükleme API üzerinden yapıldı. Fiziksel
ses çıkışı, native Apple/Spark, çok uzun yük ve 50 kişilik doğal Türkçe
referanslı kalite ayrı açıklar olarak [planda](../../../plans/USABILITY_AND_ACCURACY.md) kayıtlıdır.

Önceki Türkçe/50 kişi ölçümleri korunur; bu çalışma onları yeni sürümde
tekrarlanmış gibi sunmaz. Model/eşik, şema veya bağımlılık değişikliği yoktur.
Commit/push yapılmadı.
