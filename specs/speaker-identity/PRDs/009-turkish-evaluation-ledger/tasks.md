# Tasks — Türkçe değerlendirme ve deney günlüğü

Kaynak: [Accepted PRD](PRD.md), [plan](plan.md).
Sabit profil: `kt-vibecoding-python-web-v2`.

- [x] T01 Kullanıcı isteğini ve mevcut ölçüm sınırlarını kaydet; çıktı PRD/plan/roadmap, kanıt 13 Eylül isteği ve mevcut 001/002 ölçüm kodudur.
- [x] T02 Günlük ve standart komut bağlantısını geliştir; `results.md` 13 geçmiş + 5 yeni deney içerir; son 35 günlük testi ve ilgili komut regresyonları geçti.
- [x] T03 Eski skorları koruyarak sürümlü Türkçe metin ölçümünü ekle; `turkish-words-v1`, gerçek CLI/dosya ve geçmiş davranış dahil 53 ilgili test geçti.
- [x] T04 Kaynaklı veri taraması ve doğrulanmış Türkçe hazırlamayı tamamla; araştırma/kullanım belgeleri, 25 sabit Real-TurnTurk dosyası/6 WAV ve 80 farklı MediaSpeech klibi hazır; 18 hazırlama + 19 ASR sınır testi geçti.
- [x] T05 Gerçek yerel Türkçe taban çizgisini ve gerekçeli adayları ölç; 3 ASR koşumu ve yeni boş galerilerde 2 gerçek altışar görüşmeli HTTP koşumu günlüğe yazıldı. Sayısı bilinen adayda dönüş 3/6→5/6, mikro F1 %66,67→%90,91; ayrılmış ASR WER %16,10. Zayıf toplantı referansı ve 50 kişi kanıtı açık kaldı.
- [x] T06 Dar/tam/güvenlik kontrollerini çalıştır ve kanıtı kaydet; son dar 389, tam profilde 605 backend + 133 frontend test geçti. Güvenlik kapısı çıkış 2 (`gitleaks` eksik) açıkça kaydedildi; tarama geçişi iddia edilmedi.

Kanıt: [13 Eylül koşum raporu](../../../../docs/evidence/2026-09-13-turkish-evaluation/README.md).
Gerekli geliştirme/değerlendirme çıktıları tamamlandı; eksik güvenlik taraması,
insan doğrulanmış geniş Türkçe toplantı verisi, 50 kişi ve Spark/Apple canlı
kanıtı bu raporun açık maddeleridir. Bu deneyde L3 sahip kabulü yoktur.
