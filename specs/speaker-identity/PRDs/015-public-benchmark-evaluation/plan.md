# Plan — Kamuya açık kıyaslarla doğruluk ölçümü

1. Open Question 1 ve Decision 1: AMI ses ve referans kaynaklarının lisansını ve sabit
   URL/hash listesini kaydet; `scripts/prepare-ami-evaluation.py` ve manifest testleri.
2. Requirement 2: `speaker-turns` için şema, servis, repository ve router; gerçek
   PostgreSQL ile RBAC/tenant/sayfalama testleri; OpenAPI dışa aktarımı ve tip üretimi.
3. Requirement 3: `scripts/run-ami-evaluation.py`; mevcut `run-meeting-evaluation.py`
   istemci ve checkpoint desenini yeniden kullan; `speaker_metrics.py` kimlik ölçütleri,
   `pyannote-metrics` ile DER/JER.
4. Requirement 4: AMI Mix-Headset ve Array1-01, iki rotasyon; Türkçe FLEURS ve
   MediaSpeech yeniden koşumu; `record-experiment.py` ile `results.md`.
5. Tam profil kalite kapısı ve sabit koşum raporu.
