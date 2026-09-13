# Plan — Türkçe değerlendirme ve deney günlüğü

Kaynak: [Accepted PRD](PRD.md). Sabit profil: `kt-vibecoding-python-web-v2`.

1. Requirement 1–2 / Decisions 2–4: Mevcut kimlik ve metin sonuçlarını incele;
   `scripts/` ortak atomik günlük modülünü ve standart skor komutlarına bağlantıyı
   geliştir. Kök `results.md` ve toplu makine kanıtları izin verilen alanlarla
   yazılsın; geçmiş deney aktarımı tekrarlanabilir ve kaynak bağlı olsun.
2. Requirement 4 / Decision 5: `src/voiceup/meeting_metrics.py` ve metin skor
   komutuna açık Türkçe normalizasyon seçeneği ekle; eski varsayılanı ve
   tarihsel JSON sözleşmesini koru. `tests/` altında dil ve gerçek CLI/dosya
   regresyonlarını kırmızı/yeşil doğrula.
3. Requirement 3 / Decisions 6–7: Resmî veri kartı/makale/indirme bilgileriyle
   `plans/TURKISH_DATASET_RESEARCH.md` raporunu yaz. Seçilen veri için sabit
   revision, hash, güvenli yol ve sınırlı indirme/çözme içeren hazırlama aracı
   kullan veya mevcut `scripts/` kalıbını genişlet; ham veri Git dışında kalsın.
4. Requirement 4 / Decisions 4, 7–8: Yerel çalışma ortamını normal wrapper ile
   aç; Türkçe gerçek ses taban çizgisini dondurulmuş seçimle çalıştır. Referans
   kalitesine göre ASR veya kişi/hafıza skorlarını ayrı kaydet. Bir model adayı
   denenirse aynı değerlendirme şartlarında önce/sonra ve reddedilen sonuçları
   da günlüğe ekle; desteklenmeyen doğruluk iddiasından kaçın.
   Decision 9 araçları `prepare-turkish-meeting-evaluation.py`,
   `run-turkish-meeting-evaluation.py` ve `evaluate-turkish-asr.py` olur;
   kaynak/özel durumlar `data/` ve `outputs/`, yayımlanabilir toplu kanıtlar
   `docs/evidence/2026-09-13-turkish-evaluation/` altında tutulur.
5. API/şema/UI/dağıtım katmanları N/A gerekçeleri PRD'dedir. Dar Python
   testleri, `scripts/quality-gate.sh all` ve güvenlik aracı kontrolünü çalıştır;
   sabit koşum raporu, kullanım rehberi, roadmap ve görev kanıtını güncelle.
