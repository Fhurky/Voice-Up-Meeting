# Deney sonuçları

Her deney kendi veri, model, protokol ve paydalarıyla okunmalıdır. Kalibrasyon,
tarihsel regresyon ve ayrılmış test birbirinin yerine geçmez. Ölçülemeyen skor
`—` olarak gösterilir; sıfır değildir. Aynı deneyin devamı ayrı sürüm olarak
korunur; sürümler bağımsız deney veya ek kişi/sorgu sayılmaz.

Kimlik precision/recall/F1 ve VoiceUp Score tanımları
[ölçüm protokolündedir](docs/SPEAKER_METRICS.md). cpWER konuşmacı etiketlerini
en uygun biçimde eşler; kalıcı kişi doğruluğu veya konuşmacı zaman hatası değildir.
İngilizce okuma ve birleştirilmiş kayıtlar doğal Türkçe toplantı başarısı kanıtlamaz.

Günlük [kullanım rehberindeki](docs/EXPERIMENTS.md) standart komutlarla güncellenir.
Elle yazılan açıklamalar korunur; makine kanıt blokları elle değiştirilmez.

[Genişletilmiş Türkçe test raporu](docs/evidence/2026-09-13-expanded-turkish/README.md),
önceki örneklerden ayrı 2.433 MediaSpeech ve 743 FLEURS klibinin kapsamını,
12 yeni toplantı kesitini ve tamamlanan koşumların kaynak bazlı sonuçlarını
bir arada açıklar. Eksik başlangıç girişimleri de kendi durumuyla korunur;
bunlar ek ses, kişi veya tamamlanmış doğruluk deneyi sayılmaz.

**Real-TurnTurk sonuçlarını okurken:** Konuşma etkinliği otomatik etiketlidir;
metin referansı ve zaman damgaları insan doğrulamasıyla teyit edilmemiştir.
Bu kaynaktaki kimlik ve metin skorları zayıf referanslı tanı ölçümüdür; MediaSpeech
insan transkripsiyonlu klip ölçümüyle veya temsilî Türkçe toplantı kabulüyle
eş tutulmaz. Aşağıdaki ilk Real-TurnTurk sürümünde “İlk kayıt kapsamı” diye
görünen %100, koşu sonunda **birikimli 6/6 kayıt** anlamındadır: ilk görünümde
kayıt 4/6 (%66,67), iki kişinin kaydı sonraki görünümde tamamlanmıştır.
Tarihsel görünüm ve makine kanıtı korunur; yeni sürümler bu iki kapsamı ayrı gösterir.

## tr-mediaspeech-dev-tr-20260913 · sürüm 1

2026-09-13 · `MediaSpeech-TR` / `c3f8aeebe085553d9fa0baf2fed25613b3d80f07b4d6665e88e0610250fc5b3c` · tr · **calibration** · `meeting-asr` · **complete**

Klip 40/40; 1140 referans kelime / 1116 çıktı kelimesi.

| Kelime hata oranı (WER) | Hata | Değiştirme | Silme | Ekleme |
|---|---|---|---|---|
| 15.96% | 182 | 82 | 62 | 38 |

Normalizasyon `turkish-words-v1`. Her klibin kelime hataları ayrı hesaplanıp bütün referans kelimelerine bölünür; klipler farklı kişiler sayılmaz. Kimlik precision/recall/F1, VoiceUp Score, konuşmacı zaman hatası ve cpWER ölçülmez.

Modeller: `Systran/faster-whisper-large-v3` @ `edaa852ec7e145841d8ffdb056a99866b5f0a478`.

<!-- voiceup-data-v1 {"aggregate_sha256":"994a6d94b395ac8aa4fd77c14e61132cf79a3a84364936f2b59a685382d79c88","evidence":null,"evidence_sha256":null,"experiment_id":"tr-mediaspeech-dev-tr-20260913","metadata":{"configuration_sha256":"d05950e7f8585944da095d7f51534647f964feb449e3e52a83ae0ddaba2c60ed","dataset":"MediaSpeech-TR","dataset_revision":"c3f8aeebe085553d9fa0baf2fed25613b3d80f07b4d6665e88e0610250fc5b3c","date":"2026-09-13","elapsed_seconds":102.05444516299997,"language":"tr","models":[{"id":"Systran/faster-whisper-large-v3","revision":"edaa852ec7e145841d8ffdb056a99866b5f0a478"}],"pipeline":"meeting-asr","protocol_sha256":"b7776df4f4744fa364ac358a541b3db056ff8d1d1f9863c00481c713e3ee172e","role":"calibration"},"recorded_at_utc":"2026-09-13T10:58:03.174179+00:00","result":{"input_sha256":"b7776df4f4744fa364ac358a541b3db056ff8d1d1f9863c00481c713e3ee172e","kind":"asr_clips","metrics":{"deletions":62,"errors":182,"hypothesis_words":1116,"insertions":38,"normalization":"turkish-words-v1","observed_clips":40,"planned_clips":40,"protocol":"voiceup-mediaspeech-tr-v1","reference_words":1140,"substitutions":82,"wer":0.15964912280701754},"source_sha256":"c3f8aeebe085553d9fa0baf2fed25613b3d80f07b4d6665e88e0610250fc5b3c","status":"complete"},"revision":1,"snapshot_sha256":"0dc2a7a0459e5b20f9d1183868f96e268b92875fef838bd0cf5a82840f099a91"} -->

## history-20260909-ecapa50-calibration · sürüm 1

2026-09-09 · `librispeech` / `8744077635a58ec928f04bc16f6ec0fcc7820241beb7c1866d6d4a704b599097` · en · **calibration** · `speaker-pilot` · **complete**

[Toplu kaynak kanıtı](docs/evidence/2026-09-09-speaker-metrics/calibration-summary.json) · dosya SHA-256 `f69b69606d64436c064f1c478eeacc7ba470c34b13e00766e534938e83031aba`

| Galeri kayıt/plan | Bilinen/yeni sorgu | Precision | Recall | Micro F1 | Macro F1 | Yeni kişi F1 | VoiceUp /100 |
|---|---|---|---|---|---|---|---|
| 40/50 | 150/100 | 100.00% | 74.00% | 85.06% | 76.20% | 84.76% | 80.25 |

Başarısız ilk kayıt ve sorgular planlı paydada tutulur; iç içe galeriler bağımsız tekrar değildir. Metin ve konuşmacı zaman hatası bu deneyde ölçülmez.

Modeller: `speechbrain/spkrec-ecapa-voxceleb` @ `0f99f2d0ebe89ac095bcc5903c4dd8f72b367286`.

<!-- voiceup-data-v1 {"aggregate_sha256":"2fffb4d4ffc011e44160eeeb73117e70a48c60b6ecaa9dddcfbd6260e9861cd0","evidence":"docs/evidence/2026-09-09-speaker-metrics/calibration-summary.json","evidence_sha256":"f69b69606d64436c064f1c478eeacc7ba470c34b13e00766e534938e83031aba","experiment_id":"history-20260909-ecapa50-calibration","metadata":{"dataset":"librispeech","dataset_revision":"8744077635a58ec928f04bc16f6ec0fcc7820241beb7c1866d6d4a704b599097","date":"2026-09-09","language":"en","models":[{"id":"speechbrain/spkrec-ecapa-voxceleb","revision":"0f99f2d0ebe89ac095bcc5903c4dd8f72b367286"}],"pipeline":"speaker-pilot","role":"calibration"},"recorded_at_utc":"2026-09-13T10:59:21.585368+00:00","result":{"kind":"identity","manifest_sha256":"8744077635a58ec928f04bc16f6ec0fcc7820241beb7c1866d6d4a704b599097","metrics":{"manifest_sha256":"8744077635a58ec928f04bc16f6ec0fcc7820241beb7c1866d6d4a704b599097","protocol":"voiceup-open-set-v1","stages":[{"counts":{"known_correct":111,"known_job_failed":18,"known_not_run":0,"known_planned":150,"known_wrong":0,"unknown_false_accepted":0,"unknown_job_failed":7,"unknown_not_run":0,"unknown_planned":100},"decision_coverage":0.884,"enrollment_coverage":0.8,"enrollment_failed":10,"gallery_size_enrolled":40,"gallery_size_planned":50,"identity":{"false_negative":39,"false_positive":0,"macro_f1":0.762,"micro_f1":0.8505747126436781,"precision":1.0,"recall":0.74,"true_positive":111},"rates":{"DIR":0.74,"FPIR_observed_lower_bound":0.0,"FPIR_worst_case_upper_bound":0.07,"known_misidentification":0.0,"unknown_detection_recall":0.89},"support":{"known_probes":150,"known_speakers":50,"unknown_probes":100,"unknown_speakers":20},"unknown":{"f1":0.8476190476190476,"false_negative":11,"false_positive":21,"precision":0.8090909090909091,"recall":0.89,"true_positive":89},"voiceup_score":80.25323945328678}]},"private_source_report_sha256":"03cedc90f6b6c290d431819ce3878acf7eca63b4681dcd1d5b8c367b4147a0f2","status":"complete"},"revision":1,"snapshot_sha256":"63de0fa672ec8f7eb6888cfbb7ee2bd988266c2429711a26d3a742176930b428"} -->

## history-20260909-ecapa50-historical · sürüm 1

2026-09-09 · `librispeech` / `d2913c1b2a0bcb5f552f5a8bd9dc7f7b5872dd4d6b024bc4a0e40a2d6af54a98` · en · **regression** · `speaker-pilot` · **complete**

[Toplu kaynak kanıtı](docs/evidence/2026-09-09-speaker-metrics/historical-summary.json) · dosya SHA-256 `56d80f79d1bab9dc4b7aa9f0ccd20bd9e9f3157ba119b4db393dab8f51e1d8d2`

| Galeri kayıt/plan | Bilinen/yeni sorgu | Precision | Recall | Micro F1 | Macro F1 | Yeni kişi F1 | VoiceUp /100 |
|---|---|---|---|---|---|---|---|
| 29/50 | 150/100 | 100.00% | 52.00% | 68.42% | 54.00% | 71.05% | 61.36 |

Başarısız ilk kayıt ve sorgular planlı paydada tutulur; iç içe galeriler bağımsız tekrar değildir. Metin ve konuşmacı zaman hatası bu deneyde ölçülmez.

Modeller: `speechbrain/spkrec-ecapa-voxceleb` @ `0f99f2d0ebe89ac095bcc5903c4dd8f72b367286`.

<!-- voiceup-data-v1 {"aggregate_sha256":"70ce45e851a748254d6ca5931a51c56f1137967f575c2b1bac4ff30f84d94fd6","evidence":"docs/evidence/2026-09-09-speaker-metrics/historical-summary.json","evidence_sha256":"56d80f79d1bab9dc4b7aa9f0ccd20bd9e9f3157ba119b4db393dab8f51e1d8d2","experiment_id":"history-20260909-ecapa50-historical","metadata":{"dataset":"librispeech","dataset_revision":"d2913c1b2a0bcb5f552f5a8bd9dc7f7b5872dd4d6b024bc4a0e40a2d6af54a98","date":"2026-09-09","language":"en","models":[{"id":"speechbrain/spkrec-ecapa-voxceleb","revision":"0f99f2d0ebe89ac095bcc5903c4dd8f72b367286"}],"pipeline":"speaker-pilot","role":"regression"},"recorded_at_utc":"2026-09-13T10:59:21.599565+00:00","result":{"kind":"identity","manifest_sha256":"d2913c1b2a0bcb5f552f5a8bd9dc7f7b5872dd4d6b024bc4a0e40a2d6af54a98","metrics":{"manifest_sha256":"d2913c1b2a0bcb5f552f5a8bd9dc7f7b5872dd4d6b024bc4a0e40a2d6af54a98","protocol":"voiceup-open-set-v1","stages":[{"counts":{"known_correct":78,"known_job_failed":24,"known_not_run":0,"known_planned":150,"known_wrong":0,"unknown_false_accepted":0,"unknown_job_failed":19,"unknown_not_run":0,"unknown_planned":100},"decision_coverage":0.824,"enrollment_coverage":0.58,"enrollment_failed":21,"gallery_size_enrolled":29,"gallery_size_planned":50,"identity":{"false_negative":72,"false_positive":0,"macro_f1":0.54,"micro_f1":0.6842105263157895,"precision":1.0,"recall":0.52,"true_positive":78},"rates":{"DIR":0.52,"FPIR_observed_lower_bound":0.0,"FPIR_worst_case_upper_bound":0.19,"known_misidentification":0.0,"unknown_detection_recall":0.81},"support":{"known_probes":150,"known_speakers":50,"unknown_probes":100,"unknown_speakers":20},"unknown":{"f1":0.7105263157894737,"false_negative":19,"false_positive":47,"precision":0.6328125,"recall":0.81,"true_positive":81},"voiceup_score":61.36363636363636}]},"private_source_report_sha256":"224e0338bf67b743b25d8d5e7677138683fc17a7de44efb96e0164aa305e16c3","status":"complete"},"revision":1,"snapshot_sha256":"a4a424e474e6ca2d5b61559822f021a9b52857e6a7ae154ec76dbf5197a9c890"} -->

## history-20260909-ecapa50-fresh · sürüm 1

2026-09-09 · `librispeech` / `70b80c92502466517b0cf1b951da91b45ee5c7dd683acd4b1a0bf1c5ba727d7a` · en · **regression** · `speaker-pilot` · **complete**

[Toplu kaynak kanıtı](docs/evidence/2026-09-09-speaker-metrics/fresh-summary.json) · dosya SHA-256 `37c7d6e03bfca68eb64eb6be69c34f606ffa745246135083daca4404e4822fdd`

| Galeri kayıt/plan | Bilinen/yeni sorgu | Precision | Recall | Micro F1 | Macro F1 | Yeni kişi F1 | VoiceUp /100 |
|---|---|---|---|---|---|---|---|
| 40/50 | 150/100 | 100.00% | 77.33% | 87.22% | 78.40% | 87.04% | 82.49 |

Başarısız ilk kayıt ve sorgular planlı paydada tutulur; iç içe galeriler bağımsız tekrar değildir. Metin ve konuşmacı zaman hatası bu deneyde ölçülmez.

Modeller: `speechbrain/spkrec-ecapa-voxceleb` @ `0f99f2d0ebe89ac095bcc5903c4dd8f72b367286`.

<!-- voiceup-data-v1 {"aggregate_sha256":"16c8642a17800980a362d58558619aec7a395fc4aa0f90865debe79df44dffeb","evidence":"docs/evidence/2026-09-09-speaker-metrics/fresh-summary.json","evidence_sha256":"37c7d6e03bfca68eb64eb6be69c34f606ffa745246135083daca4404e4822fdd","experiment_id":"history-20260909-ecapa50-fresh","metadata":{"dataset":"librispeech","dataset_revision":"70b80c92502466517b0cf1b951da91b45ee5c7dd683acd4b1a0bf1c5ba727d7a","date":"2026-09-09","language":"en","models":[{"id":"speechbrain/spkrec-ecapa-voxceleb","revision":"0f99f2d0ebe89ac095bcc5903c4dd8f72b367286"}],"pipeline":"speaker-pilot","role":"regression"},"recorded_at_utc":"2026-09-13T10:59:21.618350+00:00","result":{"kind":"identity","manifest_sha256":"70b80c92502466517b0cf1b951da91b45ee5c7dd683acd4b1a0bf1c5ba727d7a","metrics":{"manifest_sha256":"70b80c92502466517b0cf1b951da91b45ee5c7dd683acd4b1a0bf1c5ba727d7a","protocol":"voiceup-open-set-v1","stages":[{"counts":{"known_correct":116,"known_job_failed":10,"known_not_run":0,"known_planned":150,"known_wrong":0,"unknown_false_accepted":0,"unknown_job_failed":5,"unknown_not_run":0,"unknown_planned":100},"decision_coverage":0.928,"enrollment_coverage":0.8,"enrollment_failed":10,"gallery_size_enrolled":40,"gallery_size_planned":50,"identity":{"false_negative":34,"false_positive":0,"macro_f1":0.784,"micro_f1":0.8721804511278195,"precision":1.0,"recall":0.7733333333333333,"true_positive":116},"rates":{"DIR":0.7733333333333333,"FPIR_observed_lower_bound":0.0,"FPIR_worst_case_upper_bound":0.05,"known_misidentification":0.0,"unknown_detection_recall":0.94},"support":{"known_probes":150,"known_speakers":50,"unknown_probes":100,"unknown_speakers":20},"unknown":{"f1":0.8703703703703703,"false_negative":6,"false_positive":22,"precision":0.8103448275862069,"recall":0.94,"true_positive":94},"voiceup_score":82.49305990865945}]},"private_source_report_sha256":"7b13f98cdc4f8ed34d7ce584415200a2003e5e2736f107d95a2791a967f99c7e","status":"complete"},"revision":1,"snapshot_sha256":"bec745b9c6f12ee3bacc0b8c3965d18e1d5396792bb95fb164c49d4c680cb55c"} -->

## history-20260911-asr-baseline · sürüm 1

2026-09-11 · `librispeech-constructed-abc` / `390e1faafdbc7bcb8607efc9c058883809d649535559a2b1d1932588bc76b3dc` · en · **calibration** · `meeting-asr` · **complete**

[Toplu kaynak kanıtı](docs/evidence/2026-09-11-accuracy-audit/asr-results.json) · dosya SHA-256 `92d7226ba9d7f82e9381a7109aa9f2ec4509338ebc88d3868837e4f6167ddbba`

Normalizasyon: `unicode-words-v1`; 1137 referans kelime / 1108 çıktı kelimesi.

| Ölçü | Hata | Değiştirme | Silme | Ekleme | Oran |
|---|---|---|---|---|---|
| cpwer | 174 | 55 | 74 | 45 | 15.30% |
| assigned_only | 174 | 55 | 74 | 45 | 15.30% |

Atanmamış kelime oranı: 1.90%. Kalıcı kimlik precision/recall/F1 ve VoiceUp Score bu deneyde ölçülmez.

Modeller: `Systran/faster-whisper-large-v3` @ `edaa852ec7e145841d8ffdb056a99866b5f0a478`.

<!-- voiceup-data-v1 {"aggregate_sha256":"aa09626453d19739d478caf6161e1f4be24f07d522d40eeba693105b59f6cf66","evidence":"docs/evidence/2026-09-11-accuracy-audit/asr-results.json","evidence_sha256":"92d7226ba9d7f82e9381a7109aa9f2ec4509338ebc88d3868837e4f6167ddbba","experiment_id":"history-20260911-asr-baseline","metadata":{"dataset":"librispeech-constructed-abc","dataset_revision":"390e1faafdbc7bcb8607efc9c058883809d649535559a2b1d1932588bc76b3dc","date":"2026-09-11","language":"en","models":[{"id":"Systran/faster-whisper-large-v3","revision":"edaa852ec7e145841d8ffdb056a99866b5f0a478"}],"pipeline":"meeting-asr","role":"calibration"},"recorded_at_utc":"2026-09-13T10:59:21.632761+00:00","result":{"kind":"transcript","metrics":{"assigned_only":{"deletions":74,"errors":174,"insertions":45,"rate":0.15303430079155672,"substitutions":55},"counts":{"hypothesis_speakers":null,"hypothesis_words":1108,"reference_speakers":null,"reference_words":1137,"unassigned_words":21},"cpwer":{"deletions":74,"errors":174,"insertions":45,"rate":0.15303430079155672,"substitutions":55},"normalization":"unicode-words-v1","unassigned_word_fraction":0.01895306859205776},"status":"complete"},"revision":1,"snapshot_sha256":"930f465f83f63b3bdab5b9159de95a8c3f959418f2b8a6f5a70f77086b9c8543"} -->

## history-20260911-asr-rejected-fullcoverage-clips-v1 · sürüm 1

2026-09-11 · `librispeech-constructed-abc` / `e3eca156919f7ebe34c190803151c54d452711a4cec145c341fa9570ffb33fe6` · en · **calibration** · `meeting-asr` · **complete**

[Toplu kaynak kanıtı](docs/evidence/2026-09-11-accuracy-audit/asr-results.json) · dosya SHA-256 `92d7226ba9d7f82e9381a7109aa9f2ec4509338ebc88d3868837e4f6167ddbba`

Normalizasyon: `unicode-words-v1`; 1137 referans kelime / 1113 çıktı kelimesi.

| Ölçü | Hata | Değiştirme | Silme | Ekleme | Oran |
|---|---|---|---|---|---|
| cpwer | 169 | 59 | 67 | 43 | 14.86% |
| assigned_only | 169 | 59 | 67 | 43 | 14.86% |

Atanmamış kelime oranı: 1.62%. Kalıcı kimlik precision/recall/F1 ve VoiceUp Score bu deneyde ölçülmez.

Modeller: `Systran/faster-whisper-large-v3` @ `edaa852ec7e145841d8ffdb056a99866b5f0a478`.

<!-- voiceup-data-v1 {"aggregate_sha256":"89f09ee029ef28694c1753d54961422422f5c096025f97088ceeb3481fb217a6","evidence":"docs/evidence/2026-09-11-accuracy-audit/asr-results.json","evidence_sha256":"92d7226ba9d7f82e9381a7109aa9f2ec4509338ebc88d3868837e4f6167ddbba","experiment_id":"history-20260911-asr-rejected-fullcoverage-clips-v1","metadata":{"dataset":"librispeech-constructed-abc","dataset_revision":"e3eca156919f7ebe34c190803151c54d452711a4cec145c341fa9570ffb33fe6","date":"2026-09-11","language":"en","models":[{"id":"Systran/faster-whisper-large-v3","revision":"edaa852ec7e145841d8ffdb056a99866b5f0a478"}],"pipeline":"meeting-asr","role":"calibration"},"recorded_at_utc":"2026-09-13T10:59:21.642288+00:00","result":{"kind":"transcript","metrics":{"assigned_only":{"deletions":67,"errors":169,"insertions":43,"rate":0.148636763412489,"substitutions":59},"counts":{"hypothesis_speakers":null,"hypothesis_words":1113,"reference_speakers":null,"reference_words":1137,"unassigned_words":18},"cpwer":{"deletions":67,"errors":169,"insertions":43,"rate":0.148636763412489,"substitutions":59},"normalization":"unicode-words-v1","unassigned_word_fraction":0.016172506738544475},"status":"complete"},"revision":1,"snapshot_sha256":"b406e35542541886b3ba16c647d793a9f04bef21cbc1df33bf511f78cbbacd28"} -->

## history-20260911-asr-rejected-targeted-native-anomaly-v2 · sürüm 1

2026-09-11 · `librispeech-constructed-abc` / `7f0119487d80bffbbb5359d7cdee1c8c95bc15fc295a09ee27a1a2b8ad14fec9` · en · **calibration** · `meeting-asr` · **complete**

[Toplu kaynak kanıtı](docs/evidence/2026-09-11-accuracy-audit/asr-results.json) · dosya SHA-256 `92d7226ba9d7f82e9381a7109aa9f2ec4509338ebc88d3868837e4f6167ddbba`

Normalizasyon: `unicode-words-v1`; 1137 referans kelime / 1145 çıktı kelimesi.

| Ölçü | Hata | Değiştirme | Silme | Ekleme | Oran |
|---|---|---|---|---|---|
| cpwer | 161 | 57 | 48 | 56 | 14.16% |
| assigned_only | 161 | 57 | 48 | 56 | 14.16% |

Atanmamış kelime oranı: 1.83%. Kalıcı kimlik precision/recall/F1 ve VoiceUp Score bu deneyde ölçülmez.

Modeller: `Systran/faster-whisper-large-v3` @ `edaa852ec7e145841d8ffdb056a99866b5f0a478`.

<!-- voiceup-data-v1 {"aggregate_sha256":"c7bb26a9cb2464d9d779c562a788f21850188c02acc9b1272c57d86a98ca16e2","evidence":"docs/evidence/2026-09-11-accuracy-audit/asr-results.json","evidence_sha256":"92d7226ba9d7f82e9381a7109aa9f2ec4509338ebc88d3868837e4f6167ddbba","experiment_id":"history-20260911-asr-rejected-targeted-native-anomaly-v2","metadata":{"dataset":"librispeech-constructed-abc","dataset_revision":"7f0119487d80bffbbb5359d7cdee1c8c95bc15fc295a09ee27a1a2b8ad14fec9","date":"2026-09-11","language":"en","models":[{"id":"Systran/faster-whisper-large-v3","revision":"edaa852ec7e145841d8ffdb056a99866b5f0a478"}],"pipeline":"meeting-asr","role":"calibration"},"recorded_at_utc":"2026-09-13T10:59:21.651216+00:00","result":{"kind":"transcript","metrics":{"assigned_only":{"deletions":48,"errors":161,"insertions":56,"rate":0.14160070360598065,"substitutions":57},"counts":{"hypothesis_speakers":null,"hypothesis_words":1145,"reference_speakers":null,"reference_words":1137,"unassigned_words":21},"cpwer":{"deletions":48,"errors":161,"insertions":56,"rate":0.14160070360598065,"substitutions":57},"normalization":"unicode-words-v1","unassigned_word_fraction":0.01834061135371179},"status":"complete"},"revision":1,"snapshot_sha256":"be78fc8663972893a4d7effc1b319d1b15f1a94085aefeb6282823f52853838d"} -->

## history-20260911-native50-a-text · sürüm 1

2026-09-11 · `librispeech-constructed-50` / `b76d06a80af7b6238b650f2599f9db3b0408e3e806afd7c0e8e7addd465ccf50` · en · **regression** · `meeting-asr` · **complete**

[Toplu kaynak kanıtı](docs/evidence/2026-09-11-accuracy-audit/capacity50-native-a-memory-results.json) · dosya SHA-256 `e750a1c4e71ffb58dc6e56f89d67da084e3f93ac4d138e3952acf1d515145e86`

Normalizasyon: `unicode-words-v1`; 5724 referans kelime / 5722 çıktı kelimesi.

| Ölçü | Hata | Değiştirme | Silme | Ekleme | Oran |
|---|---|---|---|---|---|
| cpwer | 658 | 206 | 227 | 225 | 11.50% |
| assigned_only | 733 | 141 | 297 | 295 | 12.81% |

Atanmamış kelime oranı: 1.63%. Kalıcı kimlik precision/recall/F1 ve VoiceUp Score bu deneyde ölçülmez.

<!-- voiceup-data-v1 {"aggregate_sha256":"6d5095179b69af6b8ceb370338d516f8c140cb11e8098f21c04c05a6c5040947","evidence":"docs/evidence/2026-09-11-accuracy-audit/capacity50-native-a-memory-results.json","evidence_sha256":"e750a1c4e71ffb58dc6e56f89d67da084e3f93ac4d138e3952acf1d515145e86","experiment_id":"history-20260911-native50-a-text","metadata":{"dataset":"librispeech-constructed-50","dataset_revision":"b76d06a80af7b6238b650f2599f9db3b0408e3e806afd7c0e8e7addd465ccf50","date":"2026-09-11","language":"en","pipeline":"meeting-asr","role":"regression"},"recorded_at_utc":"2026-09-13T10:59:21.663585+00:00","result":{"kind":"transcript","metrics":{"assigned_only":{"deletions":297,"errors":733,"insertions":295,"rate":0.12805730258560447,"substitutions":141},"counts":{"hypothesis_speakers":52,"hypothesis_words":5722,"reference_speakers":50,"reference_words":5724,"unassigned_words":93},"cpwer":{"deletions":227,"errors":658,"insertions":225,"rate":0.11495457721872816,"substitutions":206},"normalization":"unicode-words-v1","unassigned_word_fraction":0.01625305837119888},"status":"complete"},"revision":1,"snapshot_sha256":"11a924a8449070712255e744046a45002e7dd06c9ed09a6231e29fdcfda9ffd8"} -->

## history-20260911-native50-a-memory · sürüm 1

2026-09-11 · `librispeech-constructed-50` / `b76d06a80af7b6238b650f2599f9db3b0408e3e806afd7c0e8e7addd465ccf50` · en · **regression** · `meeting-memory` · **unscored**

[Toplu kaynak kanıtı](docs/evidence/2026-09-11-accuracy-audit/capacity50-native-a-memory-results.json) · dosya SHA-256 `e750a1c4e71ffb58dc6e56f89d67da084e3f93ac4d138e3952acf1d515145e86`

Kimlik precision/recall/F1, VoiceUp Score ve metin hata skoru: **— (ölçülmedi veya deney tamamlanmadı)**.

Gözlenen sayılar: `enrolled_people`=37; `planned_people`=50.

<!-- voiceup-data-v1 {"aggregate_sha256":"a337b4770e305f219176a5639b9ed30ab4bee2b939aa9db80a540e6203e916b4","evidence":"docs/evidence/2026-09-11-accuracy-audit/capacity50-native-a-memory-results.json","evidence_sha256":"e750a1c4e71ffb58dc6e56f89d67da084e3f93ac4d138e3952acf1d515145e86","experiment_id":"history-20260911-native50-a-memory","metadata":{"dataset":"librispeech-constructed-50","dataset_revision":"b76d06a80af7b6238b650f2599f9db3b0408e3e806afd7c0e8e7addd465ccf50","date":"2026-09-11","language":"en","pipeline":"meeting-memory","role":"regression"},"recorded_at_utc":"2026-09-13T10:59:21.673215+00:00","result":{"kind":"observation","metrics":null,"observations":{"enrolled_people":37,"planned_people":50},"status":"unscored"},"revision":1,"snapshot_sha256":"0ed89c8d9d2aa0b6eb42258e54c1fcbde26b360233283be65ec392945a14f9ea"} -->

## history-20260911-native50-b-text · sürüm 1

2026-09-11 · `librispeech-constructed-50` / `b76d06a80af7b6238b650f2599f9db3b0408e3e806afd7c0e8e7addd465ccf50` · en · **regression** · `meeting-asr` · **complete**

[Toplu kaynak kanıtı](docs/evidence/2026-09-11-accuracy-audit/capacity50-native-b-memory-results.json) · dosya SHA-256 `b97d40d06da5d707f62a9ead42648ca8739526236737076776fd836733592519`

Normalizasyon: `unicode-words-v1`; 5716 referans kelime / 5713 çıktı kelimesi.

| Ölçü | Hata | Değiştirme | Silme | Ekleme | Oran |
|---|---|---|---|---|---|
| cpwer | 462 | 91 | 187 | 184 | 8.08% |
| assigned_only | 462 | 91 | 187 | 184 | 8.08% |

Atanmamış kelime oranı: 1.21%. Kalıcı kimlik precision/recall/F1 ve VoiceUp Score bu deneyde ölçülmez.

<!-- voiceup-data-v1 {"aggregate_sha256":"a9c55c441a5656d39b03d78e4d2d6b77efa419c9bb8c4b952d1962e3c9ec7f90","evidence":"docs/evidence/2026-09-11-accuracy-audit/capacity50-native-b-memory-results.json","evidence_sha256":"b97d40d06da5d707f62a9ead42648ca8739526236737076776fd836733592519","experiment_id":"history-20260911-native50-b-text","metadata":{"dataset":"librispeech-constructed-50","dataset_revision":"b76d06a80af7b6238b650f2599f9db3b0408e3e806afd7c0e8e7addd465ccf50","date":"2026-09-11","language":"en","pipeline":"meeting-asr","role":"regression"},"recorded_at_utc":"2026-09-13T10:59:21.685348+00:00","result":{"kind":"transcript","metrics":{"assigned_only":{"deletions":187,"errors":462,"insertions":184,"rate":0.08082575227431771,"substitutions":91},"counts":{"hypothesis_speakers":52,"hypothesis_words":5713,"reference_speakers":50,"reference_words":5716,"unassigned_words":69},"cpwer":{"deletions":187,"errors":462,"insertions":184,"rate":0.08082575227431771,"substitutions":91},"normalization":"unicode-words-v1","unassigned_word_fraction":0.012077717486434448},"status":"complete"},"revision":1,"snapshot_sha256":"8ab7cc6674652644d380c5e63a3f99a85ed13c83ac31a2bcd07a523dc92940f6"} -->

## history-20260911-native50-b-memory · sürüm 1

2026-09-11 · `librispeech-constructed-50` / `b76d06a80af7b6238b650f2599f9db3b0408e3e806afd7c0e8e7addd465ccf50` · en · **regression** · `meeting-memory` · **unscored**

[Toplu kaynak kanıtı](docs/evidence/2026-09-11-accuracy-audit/capacity50-native-b-memory-results.json) · dosya SHA-256 `b97d40d06da5d707f62a9ead42648ca8739526236737076776fd836733592519`

Kimlik precision/recall/F1, VoiceUp Score ve metin hata skoru: **— (ölçülmedi veya deney tamamlanmadı)**.

Gözlenen sayılar: `correct_returns`=35; `enrolled_people`=37; `planned_people`=50.

<!-- voiceup-data-v1 {"aggregate_sha256":"46d69b0b97843984322eedd498e953e2ed6450a13f2322cac26f6d716e5fac49","evidence":"docs/evidence/2026-09-11-accuracy-audit/capacity50-native-b-memory-results.json","evidence_sha256":"b97d40d06da5d707f62a9ead42648ca8739526236737076776fd836733592519","experiment_id":"history-20260911-native50-b-memory","metadata":{"dataset":"librispeech-constructed-50","dataset_revision":"b76d06a80af7b6238b650f2599f9db3b0408e3e806afd7c0e8e7addd465ccf50","date":"2026-09-11","language":"en","pipeline":"meeting-memory","role":"regression"},"recorded_at_utc":"2026-09-13T10:59:21.697980+00:00","result":{"kind":"observation","metrics":null,"observations":{"correct_returns":35,"enrolled_people":37,"planned_people":50},"status":"unscored"},"revision":1,"snapshot_sha256":"ee97652f471d3c5a6ab7c9a1daa586bb162768f28d4e97035938f6de78b90c88"} -->

## history-20260911-native50-c-text · sürüm 1

2026-09-11 · `librispeech-constructed-50` / `b76d06a80af7b6238b650f2599f9db3b0408e3e806afd7c0e8e7addd465ccf50` · en · **regression** · `meeting-asr` · **complete**

[Toplu kaynak kanıtı](docs/evidence/2026-09-11-accuracy-audit/capacity50-native-c-memory-results.json) · dosya SHA-256 `b58b08aff5c0e4b8baec5d93d5f394422bde9a2dd148753ecb732019a43bad23`

Normalizasyon: `unicode-words-v1`; 5741 referans kelime / 5738 çıktı kelimesi.

| Ölçü | Hata | Değiştirme | Silme | Ekleme | Oran |
|---|---|---|---|---|---|
| cpwer | 713 | 194 | 261 | 258 | 12.42% |
| assigned_only | 716 | 145 | 287 | 284 | 12.47% |

Atanmamış kelime oranı: 0.94%. Kalıcı kimlik precision/recall/F1 ve VoiceUp Score bu deneyde ölçülmez.

<!-- voiceup-data-v1 {"aggregate_sha256":"74df011cfda1d137b40faf70d11b25d327d47d2c0844df36d5d99a2df7b6aa65","evidence":"docs/evidence/2026-09-11-accuracy-audit/capacity50-native-c-memory-results.json","evidence_sha256":"b58b08aff5c0e4b8baec5d93d5f394422bde9a2dd148753ecb732019a43bad23","experiment_id":"history-20260911-native50-c-text","metadata":{"dataset":"librispeech-constructed-50","dataset_revision":"b76d06a80af7b6238b650f2599f9db3b0408e3e806afd7c0e8e7addd465ccf50","date":"2026-09-11","language":"en","pipeline":"meeting-asr","role":"regression"},"recorded_at_utc":"2026-09-13T10:59:21.713919+00:00","result":{"kind":"transcript","metrics":{"assigned_only":{"deletions":287,"errors":716,"insertions":284,"rate":0.12471694826685246,"substitutions":145},"counts":{"hypothesis_speakers":52,"hypothesis_words":5738,"reference_speakers":50,"reference_words":5741,"unassigned_words":54},"cpwer":{"deletions":261,"errors":713,"insertions":258,"rate":0.12419439122104163,"substitutions":194},"normalization":"unicode-words-v1","unassigned_word_fraction":0.009410944579993029},"status":"complete"},"revision":1,"snapshot_sha256":"096c867bf38b1e34e0cea5e85176dc0383271f5df8308cbced7d75ac8a01d2dc"} -->

## history-20260911-native50-c-memory · sürüm 1

2026-09-11 · `librispeech-constructed-50` / `b76d06a80af7b6238b650f2599f9db3b0408e3e806afd7c0e8e7addd465ccf50` · en · **regression** · `meeting-memory` · **unscored**

[Toplu kaynak kanıtı](docs/evidence/2026-09-11-accuracy-audit/capacity50-native-c-memory-results.json) · dosya SHA-256 `b58b08aff5c0e4b8baec5d93d5f394422bde9a2dd148753ecb732019a43bad23`

Kimlik precision/recall/F1, VoiceUp Score ve metin hata skoru: **— (ölçülmedi veya deney tamamlanmadı)**.

Gözlenen sayılar: `correct_returns`=35; `enrolled_people`=37; `planned_people`=50.

<!-- voiceup-data-v1 {"aggregate_sha256":"46d69b0b97843984322eedd498e953e2ed6450a13f2322cac26f6d716e5fac49","evidence":"docs/evidence/2026-09-11-accuracy-audit/capacity50-native-c-memory-results.json","evidence_sha256":"b58b08aff5c0e4b8baec5d93d5f394422bde9a2dd148753ecb732019a43bad23","experiment_id":"history-20260911-native50-c-memory","metadata":{"dataset":"librispeech-constructed-50","dataset_revision":"b76d06a80af7b6238b650f2599f9db3b0408e3e806afd7c0e8e7addd465ccf50","date":"2026-09-11","language":"en","pipeline":"meeting-memory","role":"regression"},"recorded_at_utc":"2026-09-13T10:59:21.724012+00:00","result":{"kind":"observation","metrics":null,"observations":{"correct_returns":35,"enrolled_people":37,"planned_people":50},"status":"unscored"},"revision":1,"snapshot_sha256":"507b65552e115c42419b2b8b8f1c257778de5f3085ee237b368bc55ff320f60f"} -->

## history-20260910-turkish-single-speaker-smoke · sürüm 1

2026-09-10 · `local-turkish-sample` / `3c344e99c757b5c2448050821514aaa9571729fdae0984cefdb8e02384e14851` · tr · **smoke** · `meeting-memory` · **unscored**

[Toplu kaynak kanıtı](docs/evidence/2026-09-10-meeting-delivery/turkish-source-results.json) · dosya SHA-256 `ac9a54974735d13d97be6e33d65650670a2f11d3320beb8a9e1d87de28cda4a3`

Kimlik precision/recall/F1, VoiceUp Score ve metin hata skoru: **— (ölçülmedi veya deney tamamlanmadı)**.

Gözlenen sayılar: `observed_speakers`=1; `transcript_segments`=2.

<!-- voiceup-data-v1 {"aggregate_sha256":"0574bc4276fcc4906848e28bdd4a8fa2d873a61350f52f439a39af31786c1d94","evidence":"docs/evidence/2026-09-10-meeting-delivery/turkish-source-results.json","evidence_sha256":"ac9a54974735d13d97be6e33d65650670a2f11d3320beb8a9e1d87de28cda4a3","experiment_id":"history-20260910-turkish-single-speaker-smoke","metadata":{"dataset":"local-turkish-sample","dataset_revision":"3c344e99c757b5c2448050821514aaa9571729fdae0984cefdb8e02384e14851","date":"2026-09-10","language":"tr","pipeline":"meeting-memory","role":"smoke"},"recorded_at_utc":"2026-09-13T10:59:21.737591+00:00","result":{"kind":"observation","metrics":null,"observations":{"observed_speakers":1,"transcript_segments":2},"source_sha256":"3c344e99c757b5c2448050821514aaa9571729fdae0984cefdb8e02384e14851","status":"unscored"},"revision":1,"snapshot_sha256":"e89ddb91c9cb7d4ad52b8f2e1753d1a1985697f5eb8684adf56bbfd623f37266"} -->

## tr-mediaspeech-dev-auto-20260913 · sürüm 1

2026-09-13 · `MediaSpeech-TR` / `c3f8aeebe085553d9fa0baf2fed25613b3d80f07b4d6665e88e0610250fc5b3c` · tr · **calibration** · `meeting-asr` · **complete**

Klip 40/40; 1140 referans kelime / 1116 çıktı kelimesi.

| Kelime hata oranı (WER) | Hata | Değiştirme | Silme | Ekleme |
|---|---|---|---|---|
| 15.96% | 182 | 82 | 62 | 38 |

Normalizasyon `turkish-words-v1`. Her klibin kelime hataları ayrı hesaplanıp bütün referans kelimelerine bölünür; klipler farklı kişiler sayılmaz. Kimlik precision/recall/F1, VoiceUp Score, konuşmacı zaman hatası ve cpWER ölçülmez.

Modeller: `Systran/faster-whisper-large-v3` @ `edaa852ec7e145841d8ffdb056a99866b5f0a478`.

<!-- voiceup-data-v1 {"aggregate_sha256":"994a6d94b395ac8aa4fd77c14e61132cf79a3a84364936f2b59a685382d79c88","evidence":null,"evidence_sha256":null,"experiment_id":"tr-mediaspeech-dev-auto-20260913","metadata":{"configuration_sha256":"3b3b37c3dddaded85362820519fc525f28ebc1c3bb1f128226f0a8ef87e0ee4a","dataset":"MediaSpeech-TR","dataset_revision":"c3f8aeebe085553d9fa0baf2fed25613b3d80f07b4d6665e88e0610250fc5b3c","date":"2026-09-13","elapsed_seconds":117.9291247970001,"language":"tr","models":[{"id":"Systran/faster-whisper-large-v3","revision":"edaa852ec7e145841d8ffdb056a99866b5f0a478"}],"pipeline":"meeting-asr","protocol_sha256":"b7776df4f4744fa364ac358a541b3db056ff8d1d1f9863c00481c713e3ee172e","role":"calibration"},"record_sha256":"5846476abfc092451347fc83a3540948d94d375e80c78c90217e36f7660b3ef9","recorded_at_utc":"2026-09-13T11:02:42.910469+00:00","result":{"input_sha256":"b7776df4f4744fa364ac358a541b3db056ff8d1d1f9863c00481c713e3ee172e","kind":"asr_clips","metrics":{"deletions":62,"errors":182,"hypothesis_words":1116,"insertions":38,"normalization":"turkish-words-v1","observed_clips":40,"planned_clips":40,"protocol":"voiceup-mediaspeech-tr-v1","reference_words":1140,"substitutions":82,"wer":0.15964912280701754},"source_sha256":"c3f8aeebe085553d9fa0baf2fed25613b3d80f07b4d6665e88e0610250fc5b3c","status":"complete"},"revision":1,"snapshot_sha256":"d6b8c7ab342e4eff52b10aebeb30911714bce577bb6030f1051a0e9405edb2eb"} -->

## tr-realturnturk-chain-baseline-20260913 · sürüm 1

2026-09-13 · `Real-TurnTurk` / `db8f20f6eb6b215ec75fb466374fc5cc861b91df` · tr · **calibration** · `meeting-memory` · **complete**

Toplantı 6/6; 6 gerçek kişi; bilinen/yeni kişi görünümleri 6/6.

| Precision | Recall | Micro F1 | Macro F1 | Yeni kişi F1 | VoiceUp /100 |
|---|---|---|---|---|---|
| 100.00% | 50.00% | 66.67% | 50.00% | 66.67% | 57.14 |

İlk kayıt kapsamı: 100.00%; karar kapsamı: 75.00%.

| Toplantı | Referans kelime | cpWER | Atanmamış akış cezasıyla |
|---|---|---|---|
| 1 | 350 | 22.57% | 22.57% |
| 2 | 390 | 29.49% | 29.49% |
| 3 | 411 | 30.17% | 30.17% |
| 4 | 386 | 39.90% | 39.90% |
| 5 | 431 | 25.29% | 25.29% |
| 6 | 373 | 41.02% | 41.02% |

Modeller: `pyannote/speaker-diarization-community-1` @ `3533c8cf8e369892e6b79ff1bf80f7b0286a54ee`; `speechbrain/spkrec-ecapa-voxceleb` @ `0f99f2d0ebe89ac095bcc5903c4dd8f72b367286`; `Systran/faster-whisper-large-v3` @ `edaa852ec7e145841d8ffdb056a99866b5f0a478`.

**Zayıf otomatik referans:** Bu skorlar otomatik kaynak etiketleriyle uyumu ölçer; insan doğrulanmış Türkçe kimlik doğruluğu, bağımsız oturum veya 50 kişi kabulü değildir.

<!-- voiceup-data-v1 {"aggregate_sha256":"d535420104b96f58808b733dc0662bd935832f2ccae1618f2b4021b5533bd6ee","evidence":null,"evidence_sha256":null,"experiment_id":"tr-realturnturk-chain-baseline-20260913","metadata":{"configuration_sha256":"094e254d8f66d68fba887446c141ae9bc443bf6506994a7d39c37415c0a84b90","dataset":"Real-TurnTurk","dataset_revision":"db8f20f6eb6b215ec75fb466374fc5cc861b91df","date":"2026-09-13","language":"tr","models":[{"id":"pyannote/speaker-diarization-community-1","revision":"3533c8cf8e369892e6b79ff1bf80f7b0286a54ee"},{"id":"speechbrain/spkrec-ecapa-voxceleb","revision":"0f99f2d0ebe89ac095bcc5903c4dd8f72b367286"},{"id":"Systran/faster-whisper-large-v3","revision":"edaa852ec7e145841d8ffdb056a99866b5f0a478"}],"pipeline":"meeting-memory","protocol_sha256":"483e4810b3cd4559f9f00ce232deb12974e483be280e012f6117324911e7414c","role":"calibration"},"record_sha256":"7809c8294f79dafe98830a1e6717ed617fa9b89e76c7760395f22b9083ebeb30","recorded_at_utc":"2026-09-13T11:08:22.626662+00:00","result":{"coverage":{"observed_meetings":6,"planned_meetings":6},"kind":"meeting_identity","metrics":{"decision_coverage":0.75,"enrollment_coverage":1.0,"identity":{"false_negative":3,"false_positive":0,"macro_f1":0.5,"micro_f1":0.6666666666666666,"precision":1.0,"recall":0.5,"true_positive":3},"observed_meetings":6,"planned_meetings":6,"protocol":"voiceup-real-turnturk-v1","protocol_sha256":"483e4810b3cd4559f9f00ce232deb12974e483be280e012f6117324911e7414c","support":{"known_probes":6,"known_speakers":4,"observed_probes":12,"planned_probes":12,"unique_speakers":6,"unknown_probes":6},"transcripts":[{"meeting":1,"metrics":{"assigned_only":{"deletions":24,"errors":79,"insertions":21,"rate":0.2257142857142857,"substitutions":34},"counts":{"hypothesis_speakers":2,"hypothesis_words":347,"reference_speakers":2,"reference_words":350,"unassigned_words":1},"cpwer":{"deletions":24,"errors":79,"insertions":21,"rate":0.2257142857142857,"substitutions":34},"normalization":"turkish-words-v1","unassigned_word_fraction":0.002881844380403458},"source_sha256":"a4a1798b16e27f372f3310b09174091b8c3eea0f145ac8f19aef518996d4685f"},{"meeting":2,"metrics":{"assigned_only":{"deletions":45,"errors":115,"insertions":16,"rate":0.2948717948717949,"substitutions":54},"counts":{"hypothesis_speakers":2,"hypothesis_words":361,"reference_speakers":2,"reference_words":390,"unassigned_words":4},"cpwer":{"deletions":45,"errors":115,"insertions":16,"rate":0.2948717948717949,"substitutions":54},"normalization":"turkish-words-v1","unassigned_word_fraction":0.0110803324099723},"source_sha256":"c7f4bd9ac6a4e7078a3d0bc5dce15726e5242441f34e6e44cae696cf91deaa1e"},{"meeting":3,"metrics":{"assigned_only":{"deletions":52,"errors":124,"insertions":27,"rate":0.30170316301703165,"substitutions":45},"counts":{"hypothesis_speakers":3,"hypothesis_words":386,"reference_speakers":2,"reference_words":411,"unassigned_words":1},"cpwer":{"deletions":52,"errors":124,"insertions":27,"rate":0.30170316301703165,"substitutions":45},"normalization":"turkish-words-v1","unassigned_word_fraction":0.0025906735751295338},"source_sha256":"b10023895e5d6fc2aa505ec8b40b7c166810b7200f2638a732eb114d78c85090"},{"meeting":4,"metrics":{"assigned_only":{"deletions":93,"errors":154,"insertions":9,"rate":0.39896373056994816,"substitutions":52},"counts":{"hypothesis_speakers":3,"hypothesis_words":302,"reference_speakers":2,"reference_words":386,"unassigned_words":1},"cpwer":{"deletions":93,"errors":154,"insertions":9,"rate":0.39896373056994816,"substitutions":52},"normalization":"turkish-words-v1","unassigned_word_fraction":0.0033112582781456954},"source_sha256":"3a4077788f1d1b10e935e3a0da0f2bb9cd905ceb35540882007658df9b62e009"},{"meeting":5,"metrics":{"assigned_only":{"deletions":54,"errors":109,"insertions":12,"rate":0.2529002320185615,"substitutions":43},"counts":{"hypothesis_speakers":2,"hypothesis_words":389,"reference_speakers":2,"reference_words":431,"unassigned_words":4},"cpwer":{"deletions":54,"errors":109,"insertions":12,"rate":0.2529002320185615,"substitutions":43},"normalization":"turkish-words-v1","unassigned_word_fraction":0.010282776349614395},"source_sha256":"63954ddf861ea5f663b567283e1a1854fe9f9eea43508aff67ed1c075d09646d"},{"meeting":6,"metrics":{"assigned_only":{"deletions":70,"errors":153,"insertions":45,"rate":0.4101876675603217,"substitutions":38},"counts":{"hypothesis_speakers":3,"hypothesis_words":348,"reference_speakers":2,"reference_words":373,"unassigned_words":4},"cpwer":{"deletions":70,"errors":153,"insertions":45,"rate":0.4101876675603217,"substitutions":38},"normalization":"turkish-words-v1","unassigned_word_fraction":0.011494252873563218},"source_sha256":"ffc1d8d518227aff110bb2bfb8d3650d53429e42a05e0c63f0e3c57314a1549d"}],"unknown":{"f1":0.6666666666666666,"false_negative":2,"false_positive":2,"precision":0.6666666666666666,"recall":0.6666666666666666,"true_positive":4},"voiceup_score":57.14285714285714},"reference_quality":"automatic-activity-unverified-text-diagnostic","status":"complete"},"revision":1,"snapshot_sha256":"e798a5f2ceaf445ddc22ce53cc73a7126caa36f7344c42d9e4573227659e74a2"} -->

## tr-mediaspeech-heldout-tr-20260913 · sürüm 1

2026-09-13 · `MediaSpeech-TR` / `c3f8aeebe085553d9fa0baf2fed25613b3d80f07b4d6665e88e0610250fc5b3c` · tr · **frozen-test** · `meeting-asr` · **complete**

Klip 40/40; 1199 referans kelime / 1183 çıktı kelimesi.

| Kelime hata oranı (WER) | Hata | Değiştirme | Silme | Ekleme |
|---|---|---|---|---|
| 16.10% | 193 | 109 | 50 | 34 |

Normalizasyon `turkish-words-v1`. Her klibin kelime hataları ayrı hesaplanıp bütün referans kelimelerine bölünür; klipler farklı kişiler sayılmaz. Kimlik precision/recall/F1, VoiceUp Score, konuşmacı zaman hatası ve cpWER ölçülmez.

Modeller: `Systran/faster-whisper-large-v3` @ `edaa852ec7e145841d8ffdb056a99866b5f0a478`.

<!-- voiceup-data-v1 {"aggregate_sha256":"f6831ec230b28aa7b620e4d1cf4eb4c21bf9b046a46223c912dd8a7bd681abf1","evidence":null,"evidence_sha256":null,"experiment_id":"tr-mediaspeech-heldout-tr-20260913","metadata":{"configuration_sha256":"2def46f15b58f20ae92eb7aa2c3336ad602a0cd47fde8512d77d54b31901b9b9","dataset":"MediaSpeech-TR","dataset_revision":"c3f8aeebe085553d9fa0baf2fed25613b3d80f07b4d6665e88e0610250fc5b3c","date":"2026-09-13","elapsed_seconds":110.12382389499999,"language":"tr","models":[{"id":"Systran/faster-whisper-large-v3","revision":"edaa852ec7e145841d8ffdb056a99866b5f0a478"}],"pipeline":"meeting-asr","protocol_sha256":"b7776df4f4744fa364ac358a541b3db056ff8d1d1f9863c00481c713e3ee172e","role":"frozen-test"},"record_sha256":"fb6992acadc20bd8be46f5d619d667dc1d150e8ac732e49857da5ab7c749ca2a","recorded_at_utc":"2026-09-13T11:11:41.874777+00:00","result":{"input_sha256":"b7776df4f4744fa364ac358a541b3db056ff8d1d1f9863c00481c713e3ee172e","kind":"asr_clips","metrics":{"deletions":50,"errors":193,"hypothesis_words":1183,"insertions":34,"normalization":"turkish-words-v1","observed_clips":40,"planned_clips":40,"protocol":"voiceup-mediaspeech-tr-v1","reference_words":1199,"substitutions":109,"wer":0.1609674728940784},"source_sha256":"c3f8aeebe085553d9fa0baf2fed25613b3d80f07b4d6665e88e0610250fc5b3c","status":"complete"},"revision":1,"snapshot_sha256":"df99f0b87f3bd06ef485d13af5ab780e2269eceb5a957468de633ab7024dc238"} -->

## tr-realturnturk-count2-20260913 · sürüm 1

2026-09-13 · `Real-TurnTurk` / `db8f20f6eb6b215ec75fb466374fc5cc861b91df` · tr · **calibration** · `meeting-memory` · **complete**

**Zayıf otomatik referans:** Konuşma etkinliği otomatik etiketlidir; metin referansı ve zaman damgaları insan doğrulamasıyla teyit edilmemiştir. Bu tanı skorları insan doğrulanmış Türkçe kimlik/metin doğruluğu, bağımsız oturum veya 50 kişi kabulü değildir.

Konuşmacı sayısı girdisi: her toplantı için 2 (`expected_speakers=2`, `participant_count=2`).

Toplantı 6/6; 6 gerçek kişi; bilinen/yeni kişi görünümleri 6/6.

| Precision | Recall | Micro F1 | Macro F1 | Yeni kişi F1 | VoiceUp /100 |
|---|---|---|---|---|---|
| 100.00% | 83.33% | 90.91% | 75.00% | 83.33% | 78.95 |

Koşu sonunda birikimli kayıt kapsamı: 100.00%; ilk görünümde kayıt kapsamı: 83.33%; karar kapsamı: 91.67%.

| Toplantı | Referans kelime | cpWER | Atanmamış akış cezasıyla |
|---|---|---|---|
| 1 | 350 | 22.57% | 22.57% |
| 2 | 390 | 29.49% | 29.49% |
| 3 | 411 | 24.82% | 24.82% |
| 4 | 386 | 38.08% | 38.08% |
| 5 | 431 | 25.29% | 25.29% |
| 6 | 373 | 26.54% | 26.54% |

Modeller: `pyannote/speaker-diarization-community-1` @ `3533c8cf8e369892e6b79ff1bf80f7b0286a54ee`; `speechbrain/spkrec-ecapa-voxceleb` @ `0f99f2d0ebe89ac095bcc5903c4dd8f72b367286`; `Systran/faster-whisper-large-v3` @ `edaa852ec7e145841d8ffdb056a99866b5f0a478`.

<!-- voiceup-data-v1 {"aggregate_sha256":"44f0973894a999aff3911006f3bcd55505c452ee4f1f9cdd100b1af50ceb9694","evidence":null,"evidence_sha256":null,"experiment_id":"tr-realturnturk-count2-20260913","metadata":{"configuration_sha256":"b39f487da390d111231a8c4f6f3e9e9790b3960aea14ea66335eb8072024441e","dataset":"Real-TurnTurk","dataset_revision":"db8f20f6eb6b215ec75fb466374fc5cc861b91df","date":"2026-09-13","language":"tr","models":[{"id":"pyannote/speaker-diarization-community-1","revision":"3533c8cf8e369892e6b79ff1bf80f7b0286a54ee"},{"id":"speechbrain/spkrec-ecapa-voxceleb","revision":"0f99f2d0ebe89ac095bcc5903c4dd8f72b367286"},{"id":"Systran/faster-whisper-large-v3","revision":"edaa852ec7e145841d8ffdb056a99866b5f0a478"}],"pipeline":"meeting-memory","protocol_sha256":"483e4810b3cd4559f9f00ce232deb12974e483be280e012f6117324911e7414c","role":"calibration"},"record_sha256":"88cd2355003a51284b8cb61ffaa6eabd41128f2a1b4e07988c7f632aea2d3313","recorded_at_utc":"2026-09-13T11:24:00.248679+00:00","result":{"coverage":{"observed_meetings":6,"planned_meetings":6},"kind":"meeting_identity","metrics":{"cumulative_enrollment_coverage":1.0,"decision_coverage":0.9166666666666666,"first_enrollment_coverage":0.8333333333333334,"identity":{"false_negative":1,"false_positive":0,"macro_f1":0.75,"micro_f1":0.9090909090909091,"precision":1.0,"recall":0.8333333333333334,"true_positive":5},"observed_meetings":6,"planned_meetings":6,"protocol":"voiceup-real-turnturk-v1","protocol_sha256":"483e4810b3cd4559f9f00ce232deb12974e483be280e012f6117324911e7414c","support":{"known_probes":6,"known_speakers":4,"observed_probes":12,"planned_probes":12,"unique_speakers":6,"unknown_probes":6},"transcripts":[{"meeting":1,"metrics":{"assigned_only":{"deletions":24,"errors":79,"insertions":21,"rate":0.2257142857142857,"substitutions":34},"counts":{"hypothesis_speakers":2,"hypothesis_words":347,"reference_speakers":2,"reference_words":350,"unassigned_words":1},"cpwer":{"deletions":24,"errors":79,"insertions":21,"rate":0.2257142857142857,"substitutions":34},"normalization":"turkish-words-v1","unassigned_word_fraction":0.002881844380403458},"source_sha256":"a4a1798b16e27f372f3310b09174091b8c3eea0f145ac8f19aef518996d4685f"},{"meeting":2,"metrics":{"assigned_only":{"deletions":45,"errors":115,"insertions":16,"rate":0.2948717948717949,"substitutions":54},"counts":{"hypothesis_speakers":2,"hypothesis_words":361,"reference_speakers":2,"reference_words":390,"unassigned_words":4},"cpwer":{"deletions":45,"errors":115,"insertions":16,"rate":0.2948717948717949,"substitutions":54},"normalization":"turkish-words-v1","unassigned_word_fraction":0.0110803324099723},"source_sha256":"c7f4bd9ac6a4e7078a3d0bc5dce15726e5242441f34e6e44cae696cf91deaa1e"},{"meeting":3,"metrics":{"assigned_only":{"deletions":41,"errors":102,"insertions":16,"rate":0.24817518248175183,"substitutions":45},"counts":{"hypothesis_speakers":2,"hypothesis_words":386,"reference_speakers":2,"reference_words":411,"unassigned_words":1},"cpwer":{"deletions":41,"errors":102,"insertions":16,"rate":0.24817518248175183,"substitutions":45},"normalization":"turkish-words-v1","unassigned_word_fraction":0.0025906735751295338},"source_sha256":"b10023895e5d6fc2aa505ec8b40b7c166810b7200f2638a732eb114d78c85090"},{"meeting":4,"metrics":{"assigned_only":{"deletions":89,"errors":147,"insertions":5,"rate":0.38082901554404147,"substitutions":53},"counts":{"hypothesis_speakers":2,"hypothesis_words":302,"reference_speakers":2,"reference_words":386,"unassigned_words":1},"cpwer":{"deletions":89,"errors":147,"insertions":5,"rate":0.38082901554404147,"substitutions":53},"normalization":"turkish-words-v1","unassigned_word_fraction":0.0033112582781456954},"source_sha256":"3a4077788f1d1b10e935e3a0da0f2bb9cd905ceb35540882007658df9b62e009"},{"meeting":5,"metrics":{"assigned_only":{"deletions":54,"errors":109,"insertions":12,"rate":0.2529002320185615,"substitutions":43},"counts":{"hypothesis_speakers":2,"hypothesis_words":389,"reference_speakers":2,"reference_words":431,"unassigned_words":4},"cpwer":{"deletions":54,"errors":109,"insertions":12,"rate":0.2529002320185615,"substitutions":43},"normalization":"turkish-words-v1","unassigned_word_fraction":0.010282776349614395},"source_sha256":"63954ddf861ea5f663b567283e1a1854fe9f9eea43508aff67ed1c075d09646d"},{"meeting":6,"metrics":{"assigned_only":{"deletions":38,"errors":99,"insertions":13,"rate":0.26541554959785524,"substitutions":48},"counts":{"hypothesis_speakers":2,"hypothesis_words":348,"reference_speakers":2,"reference_words":373,"unassigned_words":3},"cpwer":{"deletions":38,"errors":99,"insertions":13,"rate":0.26541554959785524,"substitutions":48},"normalization":"turkish-words-v1","unassigned_word_fraction":0.008620689655172414},"source_sha256":"ffc1d8d518227aff110bb2bfb8d3650d53429e42a05e0c63f0e3c57314a1549d"}],"unknown":{"f1":0.8333333333333334,"false_negative":1,"false_positive":1,"precision":0.8333333333333334,"recall":0.8333333333333334,"true_positive":5},"voiceup_score":78.94736842105263},"reference_quality":"automatic-activity-unverified-text-diagnostic","status":"complete","use_known_speaker_count":true},"revision":1,"snapshot_sha256":"7fdcc83982ba6f349aa8434cd4bfebd83bc7355d53143338ca471bfb0b227b48"} -->

## tr-realturnturk-window300-20260913 · sürüm 1

2026-09-13 · `Real-TurnTurk` / `db8f20f6eb6b215ec75fb466374fc5cc861b91df` · tr · **frozen-test** · `meeting-memory` · **complete**

**Zayıf otomatik referans:** Konuşma etkinliği otomatik etiketlidir; metin referansı ve zaman damgaları insan doğrulamasıyla teyit edilmemiştir. Bu tanı skorları insan doğrulanmış Türkçe kimlik/metin doğruluğu, bağımsız oturum veya 50 kişi kabulü değildir.

Konuşmacı sayısı girdisi: her toplantı için 2 (`expected_speakers=2`, `participant_count=2`).

Kaynak aralığı: her görüşmede [300,600) saniye; gözlenen/planlı ses 1800/1800 saniye. Aynı altı kişi ve aynı kaynak oturumları; yeni zaman aralığı yeni kişi veya bağımsız oturum değildir.

Toplantı 6/6; 6 gerçek kişi; bilinen/yeni kişi görünümleri 6/6.

| Precision | Recall | Micro F1 | Macro F1 | Yeni kişi F1 | VoiceUp /100 |
|---|---|---|---|---|---|
| 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00 |

Koşu sonunda birikimli kayıt kapsamı: 100.00%; ilk görünümde kayıt kapsamı: 100.00%; karar kapsamı: 100.00%.

| Toplantı | Referans kelime | cpWER | Atanmamış akış cezasıyla |
|---|---|---|---|
| 1 | 681 | 35.54% | 35.54% |
| 2 | 658 | 27.36% | 27.36% |
| 3 | 657 | 28.77% | 28.77% |
| 4 | 678 | 28.61% | 28.61% |
| 5 | 746 | 25.60% | 25.60% |
| 6 | 612 | 34.64% | 34.64% |

Modeller: `pyannote/speaker-diarization-community-1` @ `3533c8cf8e369892e6b79ff1bf80f7b0286a54ee`; `speechbrain/spkrec-ecapa-voxceleb` @ `0f99f2d0ebe89ac095bcc5903c4dd8f72b367286`; `Systran/faster-whisper-large-v3` @ `edaa852ec7e145841d8ffdb056a99866b5f0a478`.

<!-- voiceup-data-v1 {"aggregate_sha256":"a4e802177564afc5bc9233c11d5f3e198813b397fc4baf4f74e35871bac68bbd","evidence":null,"evidence_sha256":null,"experiment_id":"tr-realturnturk-window300-20260913","metadata":{"configuration_sha256":"449505b5d2c7223df11cbe332feffca4bb745e2b269a793ca8ba43762503c9ec","dataset":"Real-TurnTurk","dataset_revision":"db8f20f6eb6b215ec75fb466374fc5cc861b91df","date":"2026-09-13","language":"tr","models":[{"id":"pyannote/speaker-diarization-community-1","revision":"3533c8cf8e369892e6b79ff1bf80f7b0286a54ee"},{"id":"speechbrain/spkrec-ecapa-voxceleb","revision":"0f99f2d0ebe89ac095bcc5903c4dd8f72b367286"},{"id":"Systran/faster-whisper-large-v3","revision":"edaa852ec7e145841d8ffdb056a99866b5f0a478"}],"pipeline":"meeting-memory","protocol_sha256":"45c468fff29579b2ff2f0b0388300c7871fa1de7d4b026e0fdac10c52e630240","role":"frozen-test"},"record_sha256":"082c74a4763d66e894f157037faa77d3566cd3761c9ef1f4c26412dc0dc6f677","recorded_at_utc":"2026-09-13T12:36:44.328193+00:00","result":{"coverage":{"observed_meetings":6,"planned_meetings":6},"kind":"meeting_identity","metrics":{"cumulative_enrollment_coverage":1.0,"decision_coverage":1.0,"first_enrollment_coverage":1.0,"identity":{"false_negative":0,"false_positive":0,"macro_f1":1.0,"micro_f1":1.0,"precision":1.0,"recall":1.0,"true_positive":6},"observed_meetings":6,"planned_meetings":6,"protocol":"voiceup-real-turnturk-v1","protocol_sha256":"45c468fff29579b2ff2f0b0388300c7871fa1de7d4b026e0fdac10c52e630240","support":{"known_probes":6,"known_speakers":4,"observed_probes":12,"planned_probes":12,"unique_speakers":6,"unknown_probes":6},"transcripts":[{"meeting":1,"metrics":{"assigned_only":{"deletions":93,"errors":242,"insertions":33,"rate":0.355359765051395,"substitutions":116},"counts":{"hypothesis_speakers":2,"hypothesis_words":621,"reference_speakers":2,"reference_words":681,"unassigned_words":2},"cpwer":{"deletions":93,"errors":242,"insertions":33,"rate":0.355359765051395,"substitutions":116},"normalization":"turkish-words-v1","unassigned_word_fraction":0.00322061191626409},"source_sha256":"1244b7d58a10e11268aac821717b9a8344391a5683f6110d41cd4936d07e0f84"},{"meeting":2,"metrics":{"assigned_only":{"deletions":72,"errors":180,"insertions":34,"rate":0.2735562310030395,"substitutions":74},"counts":{"hypothesis_speakers":2,"hypothesis_words":620,"reference_speakers":2,"reference_words":658,"unassigned_words":6},"cpwer":{"deletions":72,"errors":180,"insertions":34,"rate":0.2735562310030395,"substitutions":74},"normalization":"turkish-words-v1","unassigned_word_fraction":0.00967741935483871},"source_sha256":"72f5b1095e31972c1af6c6f3d94607b974a5e5834d5c9b8ddfffe73c486b9b87"},{"meeting":3,"metrics":{"assigned_only":{"deletions":92,"errors":189,"insertions":23,"rate":0.2876712328767123,"substitutions":74},"counts":{"hypothesis_speakers":2,"hypothesis_words":588,"reference_speakers":2,"reference_words":657,"unassigned_words":4},"cpwer":{"deletions":92,"errors":189,"insertions":23,"rate":0.2876712328767123,"substitutions":74},"normalization":"turkish-words-v1","unassigned_word_fraction":0.006802721088435374},"source_sha256":"8caaf214d48bc69c98ef005685cb32f851ec30ccc08c54abf57911f6fa5f1d4a"},{"meeting":4,"metrics":{"assigned_only":{"deletions":108,"errors":194,"insertions":17,"rate":0.2861356932153392,"substitutions":69},"counts":{"hypothesis_speakers":2,"hypothesis_words":587,"reference_speakers":2,"reference_words":678,"unassigned_words":5},"cpwer":{"deletions":108,"errors":194,"insertions":17,"rate":0.2861356932153392,"substitutions":69},"normalization":"turkish-words-v1","unassigned_word_fraction":0.008517887563884156},"source_sha256":"c3e76f989d16021dd7d5194864fae075ab5e8c7123f9b76f82e36d6856e5a722"},{"meeting":5,"metrics":{"assigned_only":{"deletions":76,"errors":191,"insertions":30,"rate":0.25603217158176944,"substitutions":85},"counts":{"hypothesis_speakers":2,"hypothesis_words":700,"reference_speakers":2,"reference_words":746,"unassigned_words":1},"cpwer":{"deletions":76,"errors":191,"insertions":30,"rate":0.25603217158176944,"substitutions":85},"normalization":"turkish-words-v1","unassigned_word_fraction":0.0014285714285714286},"source_sha256":"c38438b3f8f396217d38c6225c06b9d29cee10989740fc6884b4aa43e8e91ec4"},{"meeting":6,"metrics":{"assigned_only":{"deletions":89,"errors":212,"insertions":29,"rate":0.3464052287581699,"substitutions":94},"counts":{"hypothesis_speakers":2,"hypothesis_words":552,"reference_speakers":2,"reference_words":612,"unassigned_words":5},"cpwer":{"deletions":89,"errors":212,"insertions":29,"rate":0.3464052287581699,"substitutions":94},"normalization":"turkish-words-v1","unassigned_word_fraction":0.009057971014492754},"source_sha256":"c9407a134ded222a24df47e8a026035d740ca231b64654677fd6daf9aa8fd490"}],"unknown":{"f1":1.0,"false_negative":0,"false_positive":0,"precision":1.0,"recall":1.0,"true_positive":6},"voiceup_score":100.0},"observed_audio_seconds":1800,"planned_audio_seconds":1800,"reference_quality":"automatic-activity-unverified-text-diagnostic","selection":{"duration_seconds":300,"start_seconds":300},"source_protocol_id":"voiceup-real-turnturk-window300-v1","source_sessions":6,"status":"complete","use_known_speaker_count":true},"revision":1,"snapshot_sha256":"9603cde5a51f6a45bbec9188ec50f435eda78b4a3b5a4068f62cde10fe7866c8"} -->

## tr-realturnturk-window600-20260913 · sürüm 1

2026-09-13 · `Real-TurnTurk` / `db8f20f6eb6b215ec75fb466374fc5cc861b91df` · tr · **frozen-test** · `meeting-memory` · **complete**

**Zayıf otomatik referans:** Konuşma etkinliği otomatik etiketlidir; metin referansı ve zaman damgaları insan doğrulamasıyla teyit edilmemiştir. Bu tanı skorları insan doğrulanmış Türkçe kimlik/metin doğruluğu, bağımsız oturum veya 50 kişi kabulü değildir.

Konuşmacı sayısı girdisi: her toplantı için 2 (`expected_speakers=2`, `participant_count=2`).

Kaynak aralığı: her görüşmede [600,900) saniye; gözlenen/planlı ses 1800/1800 saniye. Aynı altı kişi ve aynı kaynak oturumları; yeni zaman aralığı yeni kişi veya bağımsız oturum değildir.

Toplantı 6/6; 6 gerçek kişi; bilinen/yeni kişi görünümleri 6/6.

| Precision | Recall | Micro F1 | Macro F1 | Yeni kişi F1 | VoiceUp /100 |
|---|---|---|---|---|---|
| 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00 |

Koşu sonunda birikimli kayıt kapsamı: 100.00%; ilk görünümde kayıt kapsamı: 100.00%; karar kapsamı: 100.00%.

| Toplantı | Referans kelime | cpWER | Atanmamış akış cezasıyla |
|---|---|---|---|
| 1 | 720 | 37.92% | 37.92% |
| 2 | 642 | 32.09% | 32.09% |
| 3 | 707 | 28.15% | 28.15% |
| 4 | 679 | 27.39% | 27.39% |
| 5 | 759 | 26.48% | 26.48% |
| 6 | 636 | 30.82% | 30.82% |

Modeller: `pyannote/speaker-diarization-community-1` @ `3533c8cf8e369892e6b79ff1bf80f7b0286a54ee`; `speechbrain/spkrec-ecapa-voxceleb` @ `0f99f2d0ebe89ac095bcc5903c4dd8f72b367286`; `Systran/faster-whisper-large-v3` @ `edaa852ec7e145841d8ffdb056a99866b5f0a478`.

<!-- voiceup-data-v1 {"aggregate_sha256":"1f7d4348b6ebd37a076767bb3fb6178033558d8ab1717a6dfa89079ec2e5d601","evidence":null,"evidence_sha256":null,"experiment_id":"tr-realturnturk-window600-20260913","metadata":{"configuration_sha256":"9063ecd0dd567f7e16c5a44dee5a40558a6f1919b82379f9a8054805686d4bd2","dataset":"Real-TurnTurk","dataset_revision":"db8f20f6eb6b215ec75fb466374fc5cc861b91df","date":"2026-09-13","language":"tr","models":[{"id":"pyannote/speaker-diarization-community-1","revision":"3533c8cf8e369892e6b79ff1bf80f7b0286a54ee"},{"id":"speechbrain/spkrec-ecapa-voxceleb","revision":"0f99f2d0ebe89ac095bcc5903c4dd8f72b367286"},{"id":"Systran/faster-whisper-large-v3","revision":"edaa852ec7e145841d8ffdb056a99866b5f0a478"}],"pipeline":"meeting-memory","protocol_sha256":"63c2f30133120dd012070d90ea9b36ef9ea8a9550f323b189e79a265bb83a6b7","role":"frozen-test"},"record_sha256":"acc4f75d7e12125bd99fe61a39b74749c9f828fa7f2a3b8660fb1df90ce5f8d0","recorded_at_utc":"2026-09-13T12:42:33.719176+00:00","result":{"coverage":{"observed_meetings":6,"planned_meetings":6},"kind":"meeting_identity","metrics":{"cumulative_enrollment_coverage":1.0,"decision_coverage":1.0,"first_enrollment_coverage":1.0,"identity":{"false_negative":0,"false_positive":0,"macro_f1":1.0,"micro_f1":1.0,"precision":1.0,"recall":1.0,"true_positive":6},"observed_meetings":6,"planned_meetings":6,"protocol":"voiceup-real-turnturk-v1","protocol_sha256":"63c2f30133120dd012070d90ea9b36ef9ea8a9550f323b189e79a265bb83a6b7","support":{"known_probes":6,"known_speakers":4,"observed_probes":12,"planned_probes":12,"unique_speakers":6,"unknown_probes":6},"transcripts":[{"meeting":1,"metrics":{"assigned_only":{"deletions":91,"errors":273,"insertions":55,"rate":0.37916666666666665,"substitutions":127},"counts":{"hypothesis_speakers":2,"hypothesis_words":684,"reference_speakers":2,"reference_words":720,"unassigned_words":8},"cpwer":{"deletions":91,"errors":273,"insertions":55,"rate":0.37916666666666665,"substitutions":127},"normalization":"turkish-words-v1","unassigned_word_fraction":0.011695906432748537},"source_sha256":"4f9f95b1c4c12d4e42075b84afd3c1059b6cae4db5752a25f775063433317d5b"},{"meeting":2,"metrics":{"assigned_only":{"deletions":84,"errors":206,"insertions":48,"rate":0.32087227414330216,"substitutions":74},"counts":{"hypothesis_speakers":2,"hypothesis_words":606,"reference_speakers":2,"reference_words":642,"unassigned_words":2},"cpwer":{"deletions":84,"errors":206,"insertions":48,"rate":0.32087227414330216,"substitutions":74},"normalization":"turkish-words-v1","unassigned_word_fraction":0.0033003300330033004},"source_sha256":"5c743a0d61e5a11ecc0ed35f3189bbf31245666fa5c2bc134db0359b148f7f19"},{"meeting":3,"metrics":{"assigned_only":{"deletions":97,"errors":199,"insertions":23,"rate":0.2814710042432815,"substitutions":79},"counts":{"hypothesis_speakers":2,"hypothesis_words":633,"reference_speakers":2,"reference_words":707,"unassigned_words":6},"cpwer":{"deletions":97,"errors":199,"insertions":23,"rate":0.2814710042432815,"substitutions":79},"normalization":"turkish-words-v1","unassigned_word_fraction":0.009478672985781991},"source_sha256":"e026fea692e7e465fd22422d9fb83f8d7c5d7ef7e82fca50fddb1a7191ff56fb"},{"meeting":4,"metrics":{"assigned_only":{"deletions":87,"errors":186,"insertions":19,"rate":0.27393225331369664,"substitutions":80},"counts":{"hypothesis_speakers":2,"hypothesis_words":611,"reference_speakers":2,"reference_words":679,"unassigned_words":3},"cpwer":{"deletions":87,"errors":186,"insertions":19,"rate":0.27393225331369664,"substitutions":80},"normalization":"turkish-words-v1","unassigned_word_fraction":0.004909983633387889},"source_sha256":"cbdf681ba2aacc7533368652f18657cdbe50ed097fe7e1d45dc02647e6befb01"},{"meeting":5,"metrics":{"assigned_only":{"deletions":85,"errors":201,"insertions":16,"rate":0.2648221343873518,"substitutions":100},"counts":{"hypothesis_speakers":2,"hypothesis_words":690,"reference_speakers":2,"reference_words":759,"unassigned_words":0},"cpwer":{"deletions":85,"errors":201,"insertions":16,"rate":0.2648221343873518,"substitutions":100},"normalization":"turkish-words-v1","unassigned_word_fraction":0.0},"source_sha256":"3bde2680a47f6a5410e0317c31e0c4252d9b052480061758cb74593ea5924d15"},{"meeting":6,"metrics":{"assigned_only":{"deletions":77,"errors":196,"insertions":35,"rate":0.3081761006289308,"substitutions":84},"counts":{"hypothesis_speakers":2,"hypothesis_words":594,"reference_speakers":2,"reference_words":636,"unassigned_words":14},"cpwer":{"deletions":77,"errors":196,"insertions":35,"rate":0.3081761006289308,"substitutions":84},"normalization":"turkish-words-v1","unassigned_word_fraction":0.02356902356902357},"source_sha256":"6db7c1b7b2e86550a1ec749a86b53a03d29be56042e7f570c5246f81cfb7520f"}],"unknown":{"f1":1.0,"false_negative":0,"false_positive":0,"precision":1.0,"recall":1.0,"true_positive":6},"voiceup_score":100.0},"observed_audio_seconds":1800,"planned_audio_seconds":1800,"reference_quality":"automatic-activity-unverified-text-diagnostic","selection":{"duration_seconds":300,"start_seconds":600},"source_protocol_id":"voiceup-real-turnturk-window600-v1","source_sessions":6,"status":"complete","use_known_speaker_count":true},"revision":1,"snapshot_sha256":"f6af747214ddb4f90fbc010b3aeea4ccc40dfccc045c55a4ef6573a75b96245b"} -->

## tr-mediaspeech-expanded-20260913 · sürüm 1

2026-09-13 · `MediaSpeech-TR` / `c3f8aeebe085553d9fa0baf2fed25613b3d80f07b4d6665e88e0610250fc5b3c` · tr · **frozen-test** · `meeting-asr` · **incomplete**

[Toplu kaynak kanıtı](docs/evidence/2026-09-13-expanded-turkish/mediaspeech-preflight-incomplete.json) · dosya SHA-256 `bb35037b87a6fadc0d8fc431e0b2c18b4b45f55de392665e146d1dbfeb3507d3`

Klip 0/2433; koşum tamamlanmadı.

Kimlik precision/recall/F1, VoiceUp Score ve metin hata skoru: **— (ölçülmedi veya deney tamamlanmadı)**.

<!-- voiceup-data-v1 {"aggregate_sha256":"01ed5f4564045c60e57cd3a296f3a8c3c0c4dcef553408b7a5b7c7ffe6dc00d0","evidence":"docs/evidence/2026-09-13-expanded-turkish/mediaspeech-preflight-incomplete.json","evidence_sha256":"bb35037b87a6fadc0d8fc431e0b2c18b4b45f55de392665e146d1dbfeb3507d3","experiment_id":"tr-mediaspeech-expanded-20260913","metadata":{"dataset":"MediaSpeech-TR","dataset_revision":"c3f8aeebe085553d9fa0baf2fed25613b3d80f07b4d6665e88e0610250fc5b3c","date":"2026-09-13","language":"tr","pipeline":"meeting-asr","protocol_sha256":"e5439bc09b057af136bac6d85be1a511eea646c6f942fe519f06a7d0db3929ef","role":"frozen-test"},"record_sha256":"49fd1a8ef7b6f209a86bc22db6320e61847d1d22a582521c7b6521cfcc879b0b","recorded_at_utc":"2026-09-13T12:51:55.585722+00:00","result":{"coverage":{"observed_clips":0,"planned_clips":2433},"input_sha256":"e5439bc09b057af136bac6d85be1a511eea646c6f942fe519f06a7d0db3929ef","kind":"asr_clips","metrics":null,"protocol":"voiceup-mediaspeech-tr-expanded-v1","source_sha256":"c3f8aeebe085553d9fa0baf2fed25613b3d80f07b4d6665e88e0610250fc5b3c","status":"incomplete"},"revision":1,"snapshot_sha256":"b4903eae4450fc57a4604ce9f7aba5eef914ff36c30186d4a45ec891e44b9b86"} -->

## tr-mediaspeech-expanded-full-20260913 · sürüm 1

2026-09-13 · `MediaSpeech-TR` / `c3f8aeebe085553d9fa0baf2fed25613b3d80f07b4d6665e88e0610250fc5b3c` · tr · **frozen-test** · `meeting-asr` · **incomplete**

[Toplu kaynak kanıtı](docs/evidence/2026-09-13-expanded-turkish/mediaspeech-full-preflight-incomplete.json) · dosya SHA-256 `5e167d9d8b11447e1a5dcb75bdd5524280c6ecc014a8a87e219b6209370de982`

Klip 0/2433; koşum tamamlanmadı.

Kimlik precision/recall/F1, VoiceUp Score ve metin hata skoru: **— (ölçülmedi veya deney tamamlanmadı)**.

<!-- voiceup-data-v1 {"aggregate_sha256":"b2794caae1326c88b04474d1fffb10a511b8ab6ea1ddfedd53ab56d499832626","evidence":"docs/evidence/2026-09-13-expanded-turkish/mediaspeech-full-preflight-incomplete.json","evidence_sha256":"5e167d9d8b11447e1a5dcb75bdd5524280c6ecc014a8a87e219b6209370de982","experiment_id":"tr-mediaspeech-expanded-full-20260913","metadata":{"dataset":"MediaSpeech-TR","dataset_revision":"c3f8aeebe085553d9fa0baf2fed25613b3d80f07b4d6665e88e0610250fc5b3c","date":"2026-09-13","language":"tr","pipeline":"meeting-asr","protocol_sha256":"e5439bc09b057af136bac6d85be1a511eea646c6f942fe519f06a7d0db3929ef","role":"frozen-test"},"record_sha256":"80aebe2885a1ad13b43fa7a771994385381e262a3262838d5da3d3a3140c5f10","recorded_at_utc":"2026-09-13T12:51:55.607916+00:00","result":{"coverage":{"observed_clips":0,"planned_clips":2433},"input_sha256":"e5439bc09b057af136bac6d85be1a511eea646c6f942fe519f06a7d0db3929ef","kind":"asr_clips","metrics":null,"protocol":"voiceup-mediaspeech-tr-expanded-v1","source_sha256":"c3f8aeebe085553d9fa0baf2fed25613b3d80f07b4d6665e88e0610250fc5b3c","status":"incomplete"},"revision":1,"snapshot_sha256":"857635c377bf84357f5c42b797c0038f83112a71ee7ad0379d6803b98a6c6641"} -->

## tr-mediaspeech-expanded-optimized-20260913 · sürüm 1

2026-09-13 · `MediaSpeech-TR` / `c3f8aeebe085553d9fa0baf2fed25613b3d80f07b4d6665e88e0610250fc5b3c` · tr · **frozen-test** · `meeting-asr` · **complete**

Klip 2433/2433; 71767 referans kelime / 70153 çıktı kelimesi.

| Kelime hata oranı (WER) | Hata | Değiştirme | Silme | Ekleme |
|---|---|---|---|---|
| 14.12% | 10137 | 5303 | 3224 | 1610 |

Normalizasyon `turkish-words-v1`. Her klibin kelime hataları ayrı hesaplanıp bütün referans kelimelerine bölünür; klipler farklı kişiler sayılmaz. Kimlik precision/recall/F1, VoiceUp Score, konuşmacı zaman hatası ve cpWER ölçülmez.

Modeller: `Systran/faster-whisper-large-v3` @ `edaa852ec7e145841d8ffdb056a99866b5f0a478`.

<!-- voiceup-data-v1 {"aggregate_sha256":"db19513073f4f4f9056a26c7861c1f06aa0a02eb758fa469cbe6f0821e2567e3","evidence":null,"evidence_sha256":null,"experiment_id":"tr-mediaspeech-expanded-optimized-20260913","metadata":{"configuration_sha256":"6072285ee3274c1074de1009486aed8d3f42aa2a0f6998d94aeec95999e4029a","dataset":"MediaSpeech-TR","dataset_revision":"c3f8aeebe085553d9fa0baf2fed25613b3d80f07b4d6665e88e0610250fc5b3c","date":"2026-09-13","elapsed_seconds":4038.40868986,"language":"tr","models":[{"id":"Systran/faster-whisper-large-v3","revision":"edaa852ec7e145841d8ffdb056a99866b5f0a478"}],"pipeline":"meeting-asr","protocol_sha256":"e5439bc09b057af136bac6d85be1a511eea646c6f942fe519f06a7d0db3929ef","role":"frozen-test"},"record_sha256":"fc39015f7f9265d85244c2bdcef331be2107cee72721bc5fbae1fed0ecc11263","recorded_at_utc":"2026-09-13T14:07:24.853600+00:00","result":{"coverage":{"observed_clips":2433,"planned_clips":2433},"input_sha256":"e5439bc09b057af136bac6d85be1a511eea646c6f942fe519f06a7d0db3929ef","kind":"asr_clips","metrics":{"deletions":3224,"errors":10137,"hypothesis_words":70153,"insertions":1610,"normalization":"turkish-words-v1","observed_clips":2433,"planned_clips":2433,"protocol":"voiceup-mediaspeech-tr-expanded-v1","reference_words":71767,"substitutions":5303,"wer":0.14124876335920408},"protocol":"voiceup-mediaspeech-tr-expanded-v1","source_sha256":"c3f8aeebe085553d9fa0baf2fed25613b3d80f07b4d6665e88e0610250fc5b3c","status":"complete"},"revision":1,"snapshot_sha256":"b0b7a2f10b03935ade5df190ab8a2fc8d5771df868f7b515c278800368dcdbf8"} -->

## tr-fleurs-test-20260913 · sürüm 1

2026-09-13 · `FLEURS-TR` / `70bb2e84b976b7e960aa89f1c648e09c59f894dd` · tr · **frozen-test** · `meeting-asr` · **complete**

Klip 743/743; 12914 referans kelime / 12966 çıktı kelimesi.

| Kelime hata oranı (WER) | Hata | Değiştirme | Silme | Ekleme |
|---|---|---|---|---|
| 6.50% | 840 | 676 | 56 | 108 |

Normalizasyon `turkish-words-v1`. Her klibin kelime hataları ayrı hesaplanıp bütün referans kelimelerine bölünür; klipler farklı kişiler sayılmaz. Kimlik precision/recall/F1, VoiceUp Score, konuşmacı zaman hatası ve cpWER ölçülmez.

Modeller: `Systran/faster-whisper-large-v3` @ `edaa852ec7e145841d8ffdb056a99866b5f0a478`.

<!-- voiceup-data-v1 {"aggregate_sha256":"7e8825c45d7d0d3fd2203c98acd05464b824821f40f9cb673c0864b99d5e9538","evidence":null,"evidence_sha256":null,"experiment_id":"tr-fleurs-test-20260913","metadata":{"configuration_sha256":"6072285ee3274c1074de1009486aed8d3f42aa2a0f6998d94aeec95999e4029a","dataset":"FLEURS-TR","dataset_revision":"70bb2e84b976b7e960aa89f1c648e09c59f894dd","date":"2026-09-13","elapsed_seconds":887.8973182089994,"language":"tr","models":[{"id":"Systran/faster-whisper-large-v3","revision":"edaa852ec7e145841d8ffdb056a99866b5f0a478"}],"pipeline":"meeting-asr","protocol_sha256":"77fa49973ee399d0378842ef9697697a54a29fb9a5f71a04ea55f6bf818624f8","role":"frozen-test"},"record_sha256":"7ee39128474b879946f0860dba50f43e68637e3ab4bf0c24ddd2e04df4cc0fd6","recorded_at_utc":"2026-09-13T14:24:29.959570+00:00","result":{"coverage":{"observed_clips":743,"planned_clips":743},"input_sha256":"77fa49973ee399d0378842ef9697697a54a29fb9a5f71a04ea55f6bf818624f8","kind":"asr_clips","metrics":{"deletions":56,"errors":840,"hypothesis_words":12966,"insertions":108,"normalization":"turkish-words-v1","observed_clips":743,"planned_clips":743,"protocol":"voiceup-fleurs-tr-test-v1","reference_words":12914,"substitutions":676,"wer":0.06504568685147902},"protocol":"voiceup-fleurs-tr-test-v1","source_sha256":"9e57cfefe7f0e8efb3298bb79fd04fc849e94794f684e43415969a6d7e0cdda6","status":"complete"},"revision":1,"snapshot_sha256":"a03c52a755f9ae4c4fe1b0548b44d88a9c2de1dd3069c15267cc7155ceff16d1"} -->

## tr-qwen27b-context-controlled-v1 · sürüm 1

2026-09-13 · `tr-context-controlled` / `dee1b9050455cd7b527ef3f6eebaf0d2db9bad14ddb56e5f98bd4019518f7f94` · tr · **calibration** · `transcript-review` · **complete**

Referans: `synthetic-authored`. İstek 16/16; başarısız 0 istek ham metinle paydada kaldı.

| Ham WER | Öneri WER | İyileşen / kötüleşen satır | Düzeltme isabeti | Temiz metni bozma |
|---|---|---|---|---|
| 4.40% | 2.20% | 3 / 1 | 75.00% (3/4) | 8.33% (1/12) |

91 referans kelime; değişen satır 4/16; reddedilen öneri 0; medyan/en uzun süre 5.67/47.44 saniye.

İsabet, tek başına uygulanan önerinin referansa göre kelime hatasını azaltmasıdır; insan onayı veya anlamsal doğruluk garantisi değildir. Noktalama değişimleri lexical başarı sayılmaz. Bu deney konuşmacı tanıma skorunu ölçmez.

Modeller: `ollama/qwen3.5-27b` @ `7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e`.

<!-- voiceup-data-v1 {"aggregate_sha256":"595631944a3218cfb51ca31412deef4d978d7fe680efa837000bf65267354e35","evidence":null,"evidence_sha256":null,"experiment_id":"tr-qwen27b-context-controlled-v1","metadata":{"code_commit":"d00036d5e8ac02545ac32ef4b535c248d717c1fc","configuration_sha256":"c094eaec03719df9b7157f178e25fb18b7f82d9bdeefba3934ebb93287069bb8","dataset":"tr-context-controlled","dataset_revision":"dee1b9050455cd7b527ef3f6eebaf0d2db9bad14ddb56e5f98bd4019518f7f94","date":"2026-09-13","language":"tr","models":[{"id":"ollama/qwen3.5-27b","revision":"7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e"}],"pipeline":"transcript-review","protocol_sha256":"dee1b9050455cd7b527ef3f6eebaf0d2db9bad14ddb56e5f98bd4019518f7f94","role":"calibration"},"record_sha256":"192edd034ce1390e85954bbec778bc3c24fd7768c7853fe908dcc6385d2acdb6","recorded_at_utc":"2026-09-13T16:41:04.018315+00:00","result":{"input_sha256":"dee1b9050455cd7b527ef3f6eebaf0d2db9bad14ddb56e5f98bd4019518f7f94","kind":"transcript_review","metrics":{"accepted_edits":4,"beneficial_edits":3,"change_coverage":0.25,"changed_rows":4,"clean_damage_rate":0.08333333333333333,"clean_rows":12,"completed_rows":16,"completion_coverage":1.0,"corrected_errors":2,"corrected_wer":0.02197802197802198,"damaged_clean_rows":1,"edit_precision":0.75,"elapsed_seconds":143.88999999999942,"failed_rows":0,"harmful_edits":1,"improved_rows":3,"latency_max_seconds":47.43700000000172,"latency_median_seconds":5.671999999998661,"neutral_edits":0,"planned_rows":16,"raw_errors":4,"raw_wer":0.04395604395604396,"reference_words":91,"rejected_edits":0,"worsened_rows":1},"protocol":"voiceup-context-review-v1","reference_quality":"synthetic-authored","status":"complete"},"revision":1,"snapshot_sha256":"f764a364bd4606728f66c87344a6a3122517ed0dd002f7a4c41562a9c8a146e5"} -->

## tr-qwen27b-context-controlled-v2 · sürüm 1

2026-09-13 · `tr-context-controlled` / `dee1b9050455cd7b527ef3f6eebaf0d2db9bad14ddb56e5f98bd4019518f7f94` · tr · **calibration** · `transcript-review` · **complete**

Referans: `synthetic-authored`. İstek 16/16; başarısız 0 istek ham metinle paydada kaldı.

| Ham WER | Öneri WER | İyileşen / kötüleşen satır | Düzeltme isabeti | Temiz metni bozma |
|---|---|---|---|---|
| 4.40% | 2.20% | 2 / 0 | 75.00% (3/4) | 0.00% (0/12) |

91 referans kelime; değişen satır 3/16; reddedilen öneri 0; medyan/en uzun süre 5.88/29.84 saniye.

İsabet, tek başına uygulanan önerinin referansa göre kelime hatasını azaltmasıdır; insan onayı veya anlamsal doğruluk garantisi değildir. Noktalama değişimleri lexical başarı sayılmaz. Bu deney konuşmacı tanıma skorunu ölçmez.

Modeller: `ollama/qwen3.5-27b` @ `7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e`.

<!-- voiceup-data-v1 {"aggregate_sha256":"e737d80b50dea3eacce2a1e292b249099d4eae9c4223af33aa5d17b0fd0b12ec","evidence":null,"evidence_sha256":null,"experiment_id":"tr-qwen27b-context-controlled-v2","metadata":{"code_commit":"d00036d5e8ac02545ac32ef4b535c248d717c1fc","configuration_sha256":"9d08531db7c83ce1ec405be12f346f5d392e753d81ec6c35e3c9a26d9f50e150","dataset":"tr-context-controlled","dataset_revision":"dee1b9050455cd7b527ef3f6eebaf0d2db9bad14ddb56e5f98bd4019518f7f94","date":"2026-09-13","language":"tr","models":[{"id":"ollama/qwen3.5-27b","revision":"7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e"}],"pipeline":"transcript-review","protocol_sha256":"dee1b9050455cd7b527ef3f6eebaf0d2db9bad14ddb56e5f98bd4019518f7f94","role":"calibration"},"record_sha256":"434ee391e41a48a6056919222285605651ec93598a4b2de8b03ccd3a25fa1123","recorded_at_utc":"2026-09-13T16:45:08.644126+00:00","result":{"input_sha256":"dee1b9050455cd7b527ef3f6eebaf0d2db9bad14ddb56e5f98bd4019518f7f94","kind":"transcript_review","metrics":{"accepted_edits":4,"beneficial_edits":3,"change_coverage":0.1875,"changed_rows":3,"clean_damage_rate":0.0,"clean_rows":12,"completed_rows":16,"completion_coverage":1.0,"corrected_errors":2,"corrected_wer":0.02197802197802198,"damaged_clean_rows":0,"edit_precision":0.75,"elapsed_seconds":125.68699999999444,"failed_rows":0,"harmful_edits":1,"improved_rows":2,"latency_max_seconds":29.84400000000096,"latency_median_seconds":5.875,"neutral_edits":0,"planned_rows":16,"raw_errors":4,"raw_wer":0.04395604395604396,"reference_words":91,"rejected_edits":0,"worsened_rows":0},"protocol":"voiceup-context-review-v1","reference_quality":"synthetic-authored","status":"complete"},"revision":1,"snapshot_sha256":"95a06bf02880003e0dc0b62e5f3c8ae493fccc3d12e9b0022f8f9171b4660196"} -->

## tr-qwen27b-context-mediaspeech-v1 · sürüm 1

2026-09-13 · `tr-context-mediaspeech` / `166052be1412be25d1cf3c54d2be53f122224c7561fddedb4cb86044b1a6ff6d` · tr · **regression** · `transcript-review` · **complete**

Referans: `corpus-provided-not-listened`. İstek 12/12; başarısız 0 istek ham metinle paydada kaldı.

| Ham WER | Öneri WER | İyileşen / kötüleşen satır | Düzeltme isabeti | Temiz metni bozma |
|---|---|---|---|---|
| 7.85% | 7.85% | 0 / 0 | — (0/0) | 0.00% (0/6) |

331 referans kelime; değişen satır 0/12; reddedilen öneri 2; medyan/en uzun süre 5.95/22.16 saniye.

İsabet, tek başına uygulanan önerinin referansa göre kelime hatasını azaltmasıdır; insan onayı veya anlamsal doğruluk garantisi değildir. Noktalama değişimleri lexical başarı sayılmaz. Bu deney konuşmacı tanıma skorunu ölçmez.

Modeller: `ollama/qwen3.5-27b` @ `7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e`.

<!-- voiceup-data-v1 {"aggregate_sha256":"cfa8d489f1ecca9ada6a001af06026cb626975c8e473dbd8d9be14bfa7ec954c","evidence":null,"evidence_sha256":null,"experiment_id":"tr-qwen27b-context-mediaspeech-v1","metadata":{"code_commit":"d00036d5e8ac02545ac32ef4b535c248d717c1fc","configuration_sha256":"9d08531db7c83ce1ec405be12f346f5d392e753d81ec6c35e3c9a26d9f50e150","dataset":"tr-context-mediaspeech","dataset_revision":"166052be1412be25d1cf3c54d2be53f122224c7561fddedb4cb86044b1a6ff6d","date":"2026-09-13","language":"tr","models":[{"id":"ollama/qwen3.5-27b","revision":"7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e"}],"pipeline":"transcript-review","protocol_sha256":"166052be1412be25d1cf3c54d2be53f122224c7561fddedb4cb86044b1a6ff6d","role":"regression"},"record_sha256":"5d4e6854bc72fd998fab413e65fa889e1125bc47dcfa54feca962e6e92f69997","recorded_at_utc":"2026-09-13T16:46:40.262298+00:00","result":{"input_sha256":"166052be1412be25d1cf3c54d2be53f122224c7561fddedb4cb86044b1a6ff6d","kind":"transcript_review","metrics":{"accepted_edits":0,"beneficial_edits":0,"change_coverage":0.0,"changed_rows":0,"clean_damage_rate":0.0,"clean_rows":6,"completed_rows":12,"completion_coverage":1.0,"corrected_errors":26,"corrected_wer":0.07854984894259819,"damaged_clean_rows":0,"edit_precision":null,"elapsed_seconds":91.375,"failed_rows":0,"harmful_edits":0,"improved_rows":0,"latency_max_seconds":22.15599999999904,"latency_median_seconds":5.953000000001339,"neutral_edits":0,"planned_rows":12,"raw_errors":26,"raw_wer":0.07854984894259819,"reference_words":331,"rejected_edits":2,"worsened_rows":0},"protocol":"voiceup-context-review-v1","reference_quality":"corpus-provided-not-listened","status":"complete"},"revision":1,"snapshot_sha256":"8c8a85caff698163319eb2dae1874c0f84a53ba6974830df8d680bbcb7c4ad70"} -->

## tr-qwen27b-context-fleurs-v1 · sürüm 1

2026-09-13 · `tr-context-fleurs` / `25b51f40a6435da6bc503a3c2196be97ae2221d770832a24db64f6ddf8abce57` · tr · **regression** · `transcript-review` · **complete**

Referans: `corpus-provided-not-listened`. İstek 12/12; başarısız 0 istek ham metinle paydada kaldı.

| Ham WER | Öneri WER | İyileşen / kötüleşen satır | Düzeltme isabeti | Temiz metni bozma |
|---|---|---|---|---|
| 4.98% | 4.98% | 0 / 0 | 0.00% (0/1) | 0.00% (0/6) |

201 referans kelime; değişen satır 1/12; reddedilen öneri 10; medyan/en uzun süre 5.80/35.33 saniye.

İsabet, tek başına uygulanan önerinin referansa göre kelime hatasını azaltmasıdır; insan onayı veya anlamsal doğruluk garantisi değildir. Noktalama değişimleri lexical başarı sayılmaz. Bu deney konuşmacı tanıma skorunu ölçmez.

Modeller: `ollama/qwen3.5-27b` @ `7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e`.

<!-- voiceup-data-v1 {"aggregate_sha256":"7056420749bff1016e0338e70be9dc1661189deae4f9b5c9277c89de35a5cdf1","evidence":null,"evidence_sha256":null,"experiment_id":"tr-qwen27b-context-fleurs-v1","metadata":{"code_commit":"d00036d5e8ac02545ac32ef4b535c248d717c1fc","configuration_sha256":"9d08531db7c83ce1ec405be12f346f5d392e753d81ec6c35e3c9a26d9f50e150","dataset":"tr-context-fleurs","dataset_revision":"25b51f40a6435da6bc503a3c2196be97ae2221d770832a24db64f6ddf8abce57","date":"2026-09-13","language":"tr","models":[{"id":"ollama/qwen3.5-27b","revision":"7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e"}],"pipeline":"transcript-review","protocol_sha256":"25b51f40a6435da6bc503a3c2196be97ae2221d770832a24db64f6ddf8abce57","role":"regression"},"record_sha256":"8ce6f6391d046b25c2806e85c6be0fa79fbe8b20b2c44a19840de22c313c1901","recorded_at_utc":"2026-09-13T16:49:19.782158+00:00","result":{"input_sha256":"25b51f40a6435da6bc503a3c2196be97ae2221d770832a24db64f6ddf8abce57","kind":"transcript_review","metrics":{"accepted_edits":1,"beneficial_edits":0,"change_coverage":0.08333333333333333,"changed_rows":1,"clean_damage_rate":0.0,"clean_rows":6,"completed_rows":12,"completion_coverage":1.0,"corrected_errors":10,"corrected_wer":0.04975124378109453,"damaged_clean_rows":0,"edit_precision":0.0,"elapsed_seconds":159.3440000000046,"failed_rows":0,"harmful_edits":0,"improved_rows":0,"latency_max_seconds":35.32800000000134,"latency_median_seconds":5.796999999998661,"neutral_edits":1,"planned_rows":12,"raw_errors":10,"raw_wer":0.04975124378109453,"reference_words":201,"rejected_edits":10,"worsened_rows":0},"protocol":"voiceup-context-review-v1","reference_quality":"corpus-provided-not-listened","status":"complete"},"revision":1,"snapshot_sha256":"404648984cec481494426e9e7ba4d0d6862bcf0d0aed707d0793b27a772e1b08"} -->

## tr-qwen27b-context-controlled-v1 · sürüm 2

2026-09-13 · `tr-context-controlled` / `dee1b9050455cd7b527ef3f6eebaf0d2db9bad14ddb56e5f98bd4019518f7f94` · tr · **calibration** · `transcript-review` · **complete**

[Toplu kaynak kanıtı](docs/evidence/2026-09-13-contextual-transcript-review/controlled-v1-aggregate.json) · dosya SHA-256 `8a8c13649d1d13dd8ee4880cc17d6e992d3456445c74ac2dc7f533d0f393647d`

Referans: `synthetic-authored`. İstek 16/16; başarısız 0 istek ham metinle paydada kaldı.

| Ham WER | Öneri WER | İyileşen / kötüleşen satır | Düzeltme isabeti | Temiz metni bozma |
|---|---|---|---|---|
| 4.40% | 2.20% | 3 / 1 | 75.00% (3/4) | 8.33% (1/12) |

91 referans kelime; değişen satır 4/16; reddedilen öneri 0; medyan/en uzun süre 5.62/47.44 saniye.

İsabet, tek başına uygulanan önerinin referansa göre kelime hatasını azaltmasıdır; insan onayı veya anlamsal doğruluk garantisi değildir. Noktalama değişimleri lexical başarı sayılmaz. Bu deney konuşmacı tanıma skorunu ölçmez.

Modeller: `ollama/qwen3.5-27b` @ `7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e`.

<!-- voiceup-data-v1 {"aggregate_sha256":"6e3c2439eaddf1f21ff81e8195f697530dc01883e38d0b23ef5edb1daea3d999","evidence":"docs/evidence/2026-09-13-contextual-transcript-review/controlled-v1-aggregate.json","evidence_sha256":"8a8c13649d1d13dd8ee4880cc17d6e992d3456445c74ac2dc7f533d0f393647d","experiment_id":"tr-qwen27b-context-controlled-v1","metadata":{"code_commit":"d00036d5e8ac02545ac32ef4b535c248d717c1fc","dataset":"tr-context-controlled","dataset_revision":"dee1b9050455cd7b527ef3f6eebaf0d2db9bad14ddb56e5f98bd4019518f7f94","date":"2026-09-13","language":"tr","models":[{"id":"ollama/qwen3.5-27b","revision":"7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e"}],"pipeline":"transcript-review","protocol_sha256":"dee1b9050455cd7b527ef3f6eebaf0d2db9bad14ddb56e5f98bd4019518f7f94","role":"calibration"},"record_sha256":"7741fb0473186978cfe3c97933a8e4abdb18fdb12e88043f057bf59369f4b6e1","recorded_at_utc":"2026-09-13T16:52:57.512058+00:00","result":{"input_sha256":"dee1b9050455cd7b527ef3f6eebaf0d2db9bad14ddb56e5f98bd4019518f7f94","kind":"transcript_review","metrics":{"accepted_edits":4,"beneficial_edits":3,"change_coverage":0.25,"changed_rows":4,"clean_damage_rate":0.08333333333333333,"clean_rows":12,"completed_rows":16,"completion_coverage":1.0,"corrected_errors":2,"corrected_wer":0.02197802197802198,"damaged_clean_rows":1,"edit_precision":0.75,"elapsed_seconds":143.88999999999942,"failed_rows":0,"harmful_edits":1,"improved_rows":3,"latency_max_seconds":47.43700000000172,"latency_median_seconds":5.624999999998181,"neutral_edits":0,"planned_rows":16,"raw_errors":4,"raw_wer":0.04395604395604396,"reference_words":91,"rejected_edits":0,"worsened_rows":1},"protocol":"voiceup-context-review-v1","reference_quality":"synthetic-authored","status":"complete"},"revision":2,"snapshot_sha256":"d1387e9ff1df3a4b99a9c07a7f9ab31fd8c548591a1ddd5d11fa3e5b3ad718dd"} -->

## tr-qwen27b-context-controlled-v2 · sürüm 2

2026-09-13 · `tr-context-controlled` / `dee1b9050455cd7b527ef3f6eebaf0d2db9bad14ddb56e5f98bd4019518f7f94` · tr · **calibration** · `transcript-review` · **complete**

[Toplu kaynak kanıtı](docs/evidence/2026-09-13-contextual-transcript-review/controlled-v2-aggregate.json) · dosya SHA-256 `6fdc3a8f87a2c495da254c4c12d9740674a2609a15585682723bfd8c97cb15dc`

Referans: `synthetic-authored`. İstek 16/16; başarısız 0 istek ham metinle paydada kaldı.

| Ham WER | Öneri WER | İyileşen / kötüleşen satır | Düzeltme isabeti | Temiz metni bozma |
|---|---|---|---|---|
| 4.40% | 2.20% | 2 / 0 | 75.00% (3/4) | 0.00% (0/12) |

91 referans kelime; değişen satır 3/16; reddedilen öneri 0; medyan/en uzun süre 5.87/29.84 saniye.

İsabet, tek başına uygulanan önerinin referansa göre kelime hatasını azaltmasıdır; insan onayı veya anlamsal doğruluk garantisi değildir. Noktalama değişimleri lexical başarı sayılmaz. Bu deney konuşmacı tanıma skorunu ölçmez.

Modeller: `ollama/qwen3.5-27b` @ `7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e`.

<!-- voiceup-data-v1 {"aggregate_sha256":"91d2552e7bf3b2a5b30cecdc60071adbad50fdfeef89a8e47163a13ad73513e6","evidence":"docs/evidence/2026-09-13-contextual-transcript-review/controlled-v2-aggregate.json","evidence_sha256":"6fdc3a8f87a2c495da254c4c12d9740674a2609a15585682723bfd8c97cb15dc","experiment_id":"tr-qwen27b-context-controlled-v2","metadata":{"code_commit":"d00036d5e8ac02545ac32ef4b535c248d717c1fc","configuration_sha256":"9d08531db7c83ce1ec405be12f346f5d392e753d81ec6c35e3c9a26d9f50e150","dataset":"tr-context-controlled","dataset_revision":"dee1b9050455cd7b527ef3f6eebaf0d2db9bad14ddb56e5f98bd4019518f7f94","date":"2026-09-13","language":"tr","models":[{"id":"ollama/qwen3.5-27b","revision":"7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e"}],"pipeline":"transcript-review","protocol_sha256":"dee1b9050455cd7b527ef3f6eebaf0d2db9bad14ddb56e5f98bd4019518f7f94","role":"calibration"},"record_sha256":"36ee09be0be660eba4e2830ce2dd8957a8317430d03def8f95aae9f3781b1570","recorded_at_utc":"2026-09-13T16:52:57.596884+00:00","result":{"input_sha256":"dee1b9050455cd7b527ef3f6eebaf0d2db9bad14ddb56e5f98bd4019518f7f94","kind":"transcript_review","metrics":{"accepted_edits":4,"beneficial_edits":3,"change_coverage":0.1875,"changed_rows":3,"clean_damage_rate":0.0,"clean_rows":12,"completed_rows":16,"completion_coverage":1.0,"corrected_errors":2,"corrected_wer":0.02197802197802198,"damaged_clean_rows":0,"edit_precision":0.75,"elapsed_seconds":125.68699999999444,"failed_rows":0,"harmful_edits":1,"improved_rows":2,"latency_max_seconds":29.84400000000096,"latency_median_seconds":5.867500000000291,"neutral_edits":0,"planned_rows":16,"raw_errors":4,"raw_wer":0.04395604395604396,"reference_words":91,"rejected_edits":0,"worsened_rows":0},"protocol":"voiceup-context-review-v1","reference_quality":"synthetic-authored","status":"complete"},"revision":2,"snapshot_sha256":"e202bfce4a8a34b09348ce1a4303ebf48331e37989da247d19b4b25a3a20a471"} -->

## tr-qwen27b-context-mediaspeech-v1 · sürüm 2

2026-09-13 · `tr-context-mediaspeech` / `166052be1412be25d1cf3c54d2be53f122224c7561fddedb4cb86044b1a6ff6d` · tr · **regression** · `transcript-review` · **complete**

[Toplu kaynak kanıtı](docs/evidence/2026-09-13-contextual-transcript-review/mediaspeech-v1-aggregate.json) · dosya SHA-256 `a2ead46265bec857f0788180f679655dbfab6c6adb9ed2c5860337e2c036c09b`

Referans: `corpus-provided-not-listened`. İstek 12/12; başarısız 0 istek ham metinle paydada kaldı.

| Ham WER | Öneri WER | İyileşen / kötüleşen satır | Düzeltme isabeti | Temiz metni bozma |
|---|---|---|---|---|
| 7.85% | 7.85% | 0 / 0 | — (0/0) | 0.00% (0/6) |

331 referans kelime; değişen satır 0/12; reddedilen öneri 2; medyan/en uzun süre 5.91/22.16 saniye.

İsabet, tek başına uygulanan önerinin referansa göre kelime hatasını azaltmasıdır; insan onayı veya anlamsal doğruluk garantisi değildir. Noktalama değişimleri lexical başarı sayılmaz. Bu deney konuşmacı tanıma skorunu ölçmez.

Modeller: `ollama/qwen3.5-27b` @ `7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e`.

<!-- voiceup-data-v1 {"aggregate_sha256":"bab3d28d99b3462e1c8f7c2d06515547dd7234be772e70c670ac295df5ede70e","evidence":"docs/evidence/2026-09-13-contextual-transcript-review/mediaspeech-v1-aggregate.json","evidence_sha256":"a2ead46265bec857f0788180f679655dbfab6c6adb9ed2c5860337e2c036c09b","experiment_id":"tr-qwen27b-context-mediaspeech-v1","metadata":{"code_commit":"d00036d5e8ac02545ac32ef4b535c248d717c1fc","configuration_sha256":"9d08531db7c83ce1ec405be12f346f5d392e753d81ec6c35e3c9a26d9f50e150","dataset":"tr-context-mediaspeech","dataset_revision":"166052be1412be25d1cf3c54d2be53f122224c7561fddedb4cb86044b1a6ff6d","date":"2026-09-13","language":"tr","models":[{"id":"ollama/qwen3.5-27b","revision":"7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e"}],"pipeline":"transcript-review","protocol_sha256":"166052be1412be25d1cf3c54d2be53f122224c7561fddedb4cb86044b1a6ff6d","role":"regression"},"record_sha256":"cef236d2145386d4e50358eb0fa2a90749523b2579f4f3227f68f739248d2c4a","recorded_at_utc":"2026-09-13T16:52:57.713263+00:00","result":{"input_sha256":"166052be1412be25d1cf3c54d2be53f122224c7561fddedb4cb86044b1a6ff6d","kind":"transcript_review","metrics":{"accepted_edits":0,"beneficial_edits":0,"change_coverage":0.0,"changed_rows":0,"clean_damage_rate":0.0,"clean_rows":6,"completed_rows":12,"completion_coverage":1.0,"corrected_errors":26,"corrected_wer":0.07854984894259819,"damaged_clean_rows":0,"edit_precision":null,"elapsed_seconds":91.375,"failed_rows":0,"harmful_edits":0,"improved_rows":0,"latency_max_seconds":22.15599999999904,"latency_median_seconds":5.914000000000669,"neutral_edits":0,"planned_rows":12,"raw_errors":26,"raw_wer":0.07854984894259819,"reference_words":331,"rejected_edits":2,"worsened_rows":0},"protocol":"voiceup-context-review-v1","reference_quality":"corpus-provided-not-listened","status":"complete"},"revision":2,"snapshot_sha256":"ceca7fa8e7547e07bdcfb57b29fde52309b50884773fa8ada301d9a1482481ec"} -->

## tr-qwen27b-context-fleurs-v1 · sürüm 2

2026-09-13 · `tr-context-fleurs` / `25b51f40a6435da6bc503a3c2196be97ae2221d770832a24db64f6ddf8abce57` · tr · **regression** · `transcript-review` · **complete**

[Toplu kaynak kanıtı](docs/evidence/2026-09-13-contextual-transcript-review/fleurs-v1-aggregate.json) · dosya SHA-256 `049c9d69a0a4fa5fbdc5db90b856eceb0cfaf576365c5747fb3812f4b90315fa`

Referans: `corpus-provided-not-listened`. İstek 12/12; başarısız 0 istek ham metinle paydada kaldı.

| Ham WER | Öneri WER | İyileşen / kötüleşen satır | Düzeltme isabeti | Temiz metni bozma |
|---|---|---|---|---|
| 4.98% | 4.98% | 0 / 0 | 0.00% (0/1) | 0.00% (0/6) |

201 referans kelime; değişen satır 1/12; reddedilen öneri 10; medyan/en uzun süre 5.71/35.33 saniye.

İsabet, tek başına uygulanan önerinin referansa göre kelime hatasını azaltmasıdır; insan onayı veya anlamsal doğruluk garantisi değildir. Noktalama değişimleri lexical başarı sayılmaz. Bu deney konuşmacı tanıma skorunu ölçmez.

Modeller: `ollama/qwen3.5-27b` @ `7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e`.

<!-- voiceup-data-v1 {"aggregate_sha256":"0cc8210a8d1b21582cf24a019c2ae0c326a7bf1cf85df2a358ae7945d12614fe","evidence":"docs/evidence/2026-09-13-contextual-transcript-review/fleurs-v1-aggregate.json","evidence_sha256":"049c9d69a0a4fa5fbdc5db90b856eceb0cfaf576365c5747fb3812f4b90315fa","experiment_id":"tr-qwen27b-context-fleurs-v1","metadata":{"code_commit":"d00036d5e8ac02545ac32ef4b535c248d717c1fc","configuration_sha256":"9d08531db7c83ce1ec405be12f346f5d392e753d81ec6c35e3c9a26d9f50e150","dataset":"tr-context-fleurs","dataset_revision":"25b51f40a6435da6bc503a3c2196be97ae2221d770832a24db64f6ddf8abce57","date":"2026-09-13","language":"tr","models":[{"id":"ollama/qwen3.5-27b","revision":"7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e"}],"pipeline":"transcript-review","protocol_sha256":"25b51f40a6435da6bc503a3c2196be97ae2221d770832a24db64f6ddf8abce57","role":"regression"},"record_sha256":"22455ddfdffee0ce1502c90194e3d2009db59e046c709f4e7f5d096745ce555e","recorded_at_utc":"2026-09-13T16:52:57.818612+00:00","result":{"input_sha256":"25b51f40a6435da6bc503a3c2196be97ae2221d770832a24db64f6ddf8abce57","kind":"transcript_review","metrics":{"accepted_edits":1,"beneficial_edits":0,"change_coverage":0.08333333333333333,"changed_rows":1,"clean_damage_rate":0.0,"clean_rows":6,"completed_rows":12,"completion_coverage":1.0,"corrected_errors":10,"corrected_wer":0.04975124378109453,"damaged_clean_rows":0,"edit_precision":0.0,"elapsed_seconds":159.3440000000046,"failed_rows":0,"harmful_edits":0,"improved_rows":0,"latency_max_seconds":35.32800000000134,"latency_median_seconds":5.710999999999331,"neutral_edits":1,"planned_rows":12,"raw_errors":10,"raw_wer":0.04975124378109453,"reference_words":201,"rejected_edits":10,"worsened_rows":0},"protocol":"voiceup-context-review-v1","reference_quality":"corpus-provided-not-listened","status":"complete"},"revision":2,"snapshot_sha256":"fef754c367053ff5c1527e32236d156fcdb628d7d4520a6f712c3b0fed438038"} -->

## tr-qwen27b-context-final-residency-v1 · sürüm 1

2026-09-13 · `tr-context-final-residency` / `acb7cf2bb5cd2316ecf142fcc18412c4e46bd687b18c5422e3b1dfb61dca8b27` · tr · **smoke** · `transcript-review` · **complete**

Referans: `synthetic-authored`. İstek 3/3; başarısız 0 istek ham metinle paydada kaldı.

| Ham WER | Öneri WER | İyileşen / kötüleşen satır | Düzeltme isabeti | Temiz metni bozma |
|---|---|---|---|---|
| 15.38% | 0.00% | 2 / 0 | 100.00% (2/2) | 0.00% (0/1) |

13 referans kelime; değişen satır 2/3; reddedilen öneri 0; medyan/en uzun süre 32.80/35.20 saniye.

İsabet, tek başına uygulanan önerinin referansa göre kelime hatasını azaltmasıdır; insan onayı veya anlamsal doğruluk garantisi değildir. Noktalama değişimleri lexical başarı sayılmaz. Bu deney konuşmacı tanıma skorunu ölçmez.

Modeller: `ollama/qwen3.5-27b` @ `7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e`.

<!-- voiceup-data-v1 {"aggregate_sha256":"f2749b21d51e1a3f7faf5b187353246bc4f7fc60c53eacdcf145a88c1e9cf71b","evidence":null,"evidence_sha256":null,"experiment_id":"tr-qwen27b-context-final-residency-v1","metadata":{"code_commit":"d00036d5e8ac02545ac32ef4b535c248d717c1fc","configuration_sha256":"2758aba83f63924ed678f2ca7bb9bb97dae22df9232a6abf2bba569f6457458a","dataset":"tr-context-final-residency","dataset_revision":"acb7cf2bb5cd2316ecf142fcc18412c4e46bd687b18c5422e3b1dfb61dca8b27","date":"2026-09-13","language":"tr","models":[{"id":"ollama/qwen3.5-27b","revision":"7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e"}],"pipeline":"transcript-review","protocol_sha256":"acb7cf2bb5cd2316ecf142fcc18412c4e46bd687b18c5422e3b1dfb61dca8b27","role":"smoke"},"record_sha256":"300986f6e9a66d07f3601eb97bb30dede8f9b9972fa8681662ab9c6c53500605","recorded_at_utc":"2026-09-13T16:55:11.867804+00:00","result":{"input_sha256":"acb7cf2bb5cd2316ecf142fcc18412c4e46bd687b18c5422e3b1dfb61dca8b27","kind":"transcript_review","metrics":{"accepted_edits":2,"beneficial_edits":2,"change_coverage":0.6666666666666666,"changed_rows":2,"clean_damage_rate":0.0,"clean_rows":1,"completed_rows":3,"completion_coverage":1.0,"corrected_errors":0,"corrected_wer":0.0,"damaged_clean_rows":0,"edit_precision":1.0,"elapsed_seconds":77.96899999999732,"failed_rows":0,"harmful_edits":0,"improved_rows":2,"latency_max_seconds":35.20300000000134,"latency_median_seconds":32.79699999999866,"neutral_edits":0,"planned_rows":3,"raw_errors":2,"raw_wer":0.15384615384615385,"reference_words":13,"rejected_edits":0,"worsened_rows":0},"protocol":"voiceup-context-review-v1","reference_quality":"synthetic-authored","status":"complete"},"revision":1,"snapshot_sha256":"4abe54c96f61cdabbaff81df385fe7a19a2d2f0bdd2aed447c1ed19833a74ed1"} -->

## tr-qwen27b-context-final-residency-v1 · sürüm 2

2026-09-13 · `tr-context-final-residency` / `acb7cf2bb5cd2316ecf142fcc18412c4e46bd687b18c5422e3b1dfb61dca8b27` · tr · **smoke** · `transcript-review` · **complete**

[Toplu kaynak kanıtı](docs/evidence/2026-09-13-contextual-transcript-review/final-residency-aggregate.json) · dosya SHA-256 `48c047d6c0ca16e014c082bb6612a62d0942c5c6bf15150feeca5a2557676914`

Referans: `synthetic-authored`. İstek 3/3; başarısız 0 istek ham metinle paydada kaldı.

| Ham WER | Öneri WER | İyileşen / kötüleşen satır | Düzeltme isabeti | Temiz metni bozma |
|---|---|---|---|---|
| 15.38% | 0.00% | 2 / 0 | 100.00% (2/2) | 0.00% (0/1) |

13 referans kelime; değişen satır 2/3; reddedilen öneri 0; medyan/en uzun süre 32.80/35.20 saniye.

İsabet, tek başına uygulanan önerinin referansa göre kelime hatasını azaltmasıdır; insan onayı veya anlamsal doğruluk garantisi değildir. Noktalama değişimleri lexical başarı sayılmaz. Bu deney konuşmacı tanıma skorunu ölçmez.

Modeller: `ollama/qwen3.5-27b` @ `7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e`.

<!-- voiceup-data-v1 {"aggregate_sha256":"ac131dccac576298dd5a447beb0676fb57739e3d91f5b961b52d193136cc33dc","evidence":"docs/evidence/2026-09-13-contextual-transcript-review/final-residency-aggregate.json","evidence_sha256":"48c047d6c0ca16e014c082bb6612a62d0942c5c6bf15150feeca5a2557676914","experiment_id":"tr-qwen27b-context-final-residency-v1","metadata":{"code_commit":"d00036d5e8ac02545ac32ef4b535c248d717c1fc","configuration_sha256":"2758aba83f63924ed678f2ca7bb9bb97dae22df9232a6abf2bba569f6457458a","dataset":"tr-context-final-residency","dataset_revision":"acb7cf2bb5cd2316ecf142fcc18412c4e46bd687b18c5422e3b1dfb61dca8b27","date":"2026-09-13","language":"tr","models":[{"id":"ollama/qwen3.5-27b","revision":"7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e"}],"pipeline":"transcript-review","protocol_sha256":"acb7cf2bb5cd2316ecf142fcc18412c4e46bd687b18c5422e3b1dfb61dca8b27","role":"smoke"},"record_sha256":"633ff4b14832b342b8cff72934f3e93cbbe387f02075004b9dc6f144c8ce8829","recorded_at_utc":"2026-09-13T16:57:33.728657+00:00","result":{"input_sha256":"acb7cf2bb5cd2316ecf142fcc18412c4e46bd687b18c5422e3b1dfb61dca8b27","kind":"transcript_review","metrics":{"accepted_edits":2,"beneficial_edits":2,"change_coverage":0.6666666666666666,"changed_rows":2,"clean_damage_rate":0.0,"clean_rows":1,"completed_rows":3,"completion_coverage":1.0,"corrected_errors":0,"corrected_wer":0.0,"damaged_clean_rows":0,"edit_precision":1.0,"elapsed_seconds":77.96899999999732,"failed_rows":0,"harmful_edits":0,"improved_rows":2,"latency_max_seconds":35.20300000000134,"latency_median_seconds":32.79699999999866,"neutral_edits":0,"planned_rows":3,"raw_errors":2,"raw_wer":0.15384615384615385,"reference_words":13,"rejected_edits":0,"worsened_rows":0},"protocol":"voiceup-context-review-v1","reference_quality":"synthetic-authored","status":"complete"},"revision":2,"snapshot_sha256":"f0bab0f71cf698c3815fe919bd48f6e7c963f1508a6619d208fdc7eef49851c8"} -->

## tr-qwen27b-context-functional-v1 · sürüm 1

2026-09-13 · `existing-turkish-meeting-fixtures` / `fb0314761e77b042162aa322fd483b01e1d3d1abf5fcdf8d041577f93da494db` · tr · **smoke** · `transcript-review` · **unscored**

[Toplu kaynak kanıtı](docs/evidence/2026-09-13-contextual-transcript-review/functional-aggregate.json) · dosya SHA-256 `56703c3108ddead045c1d8e7796dc47b8bdf6f2b921e7fb2a07d868be830681c`

Kimlik precision/recall/F1, VoiceUp Score ve metin hata skoru: **— (ölçülmedi veya deney tamamlanmadı)**.

Modeller: `ollama/qwen3.5-27b` @ `7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e`.

<!-- voiceup-data-v1 {"aggregate_sha256":"4d09aa4c85bf8a3cb05d22e28a3a31f0dc41667fa5b3b3f29ca5aaebbc2d2d8a","evidence":"docs/evidence/2026-09-13-contextual-transcript-review/functional-aggregate.json","evidence_sha256":"56703c3108ddead045c1d8e7796dc47b8bdf6f2b921e7fb2a07d868be830681c","experiment_id":"tr-qwen27b-context-functional-v1","metadata":{"dataset":"existing-turkish-meeting-fixtures","dataset_revision":"fb0314761e77b042162aa322fd483b01e1d3d1abf5fcdf8d041577f93da494db","date":"2026-09-13","language":"tr","models":[{"id":"ollama/qwen3.5-27b","revision":"7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e"}],"pipeline":"transcript-review","role":"smoke"},"record_sha256":"7b28f45631874d064b77535a8f123815b7dd5ef16cba8a6a175969f61c36f5ce","recorded_at_utc":"2026-09-13T17:21:42.983108+00:00","result":{"kind":"observation","metrics":null,"observations":{},"status":"unscored"},"revision":1,"snapshot_sha256":"d38a993769d60cfa4194a5ae31c7ec5f38ecd12a5f3c1ee3b0f38492079a9558"} -->

## tr-visible-qwen3.5-9b-regression-v1 · sürüm 1

2026-09-13 · `four-authored-context-regressions` / `8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30` · tr · **regression** · `transcript-review` · **complete**

Görünür öneri politikası `tr-context-words-v2`: bütün eşlenebilir model değişiklikleri ölçülür; anlamsal uyarı öneriyi gizlemez. Bu ölçüm kullanıcı kaydı/onayı değildir.

Referans: `synthetic-authored`. İstek 4/4; başarısız 0 istek ham metinle paydada kaldı.

| Ham WER | Öneri WER | İyileşen / kötüleşen satır | Düzeltme isabeti | Temiz metni bozma |
|---|---|---|---|---|
| 12.50% | 12.50% | 0 / 0 | — (0/0) | 0.00% (0/2) |

16 referans kelime; değişen satır 0/4; metne eşlenemeyen öneri 0; medyan/en uzun süre 6.93/43.47 saniye.

İsabet, tek başına uygulanan önerinin referansa göre kelime hatasını azaltmasıdır; insan onayı veya anlamsal doğruluk garantisi değildir. Noktalama değişimleri lexical başarı sayılmaz. Bu deney konuşmacı tanıma skorunu ölçmez.

Modeller: `ollama/qwen3.5-9b` @ `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`.

<!-- voiceup-data-v1 {"aggregate_sha256":"ac850935ad60e6302cadb8509adf2bdc45b81c3ff7876f33ea8e9d402e4f7971","evidence":null,"evidence_sha256":null,"experiment_id":"tr-visible-qwen3.5-9b-regression-v1","metadata":{"configuration_sha256":"d576372a75664a155914794a87801cf05a641191f78fc87e4ea102d3588cb4af","dataset":"four-authored-context-regressions","dataset_revision":"8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30","date":"2026-09-13","language":"tr","models":[{"id":"ollama/qwen3.5-9b","revision":"6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"}],"pipeline":"transcript-review","protocol_sha256":"8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30","role":"regression"},"record_sha256":"225d1638714aec82a157e1be8cdf115380a0d1523b95e1f71c1b7c91a47b68a0","recorded_at_utc":"2026-09-13T17:46:28.472654+00:00","result":{"input_sha256":"8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30","kind":"transcript_review","metrics":{"accepted_edits":0,"beneficial_edits":0,"change_coverage":0.0,"changed_rows":0,"clean_damage_rate":0.0,"clean_rows":2,"completed_rows":4,"completion_coverage":1.0,"corrected_errors":2,"corrected_wer":0.125,"damaged_clean_rows":0,"edit_precision":null,"elapsed_seconds":64.09400000000096,"failed_rows":0,"harmful_edits":0,"improved_rows":0,"latency_max_seconds":43.46900000000096,"latency_median_seconds":6.930000000000291,"neutral_edits":0,"planned_rows":4,"raw_errors":2,"raw_wer":0.125,"reference_words":16,"rejected_edits":0,"worsened_rows":0},"policy_version":"tr-context-words-v2","protocol":"voiceup-context-review-visible-v1","reference_quality":"synthetic-authored","status":"complete"},"revision":1,"snapshot_sha256":"025603025edda31c494035ddcb6f754f7422b263b761fb497da899f9fb20d735"} -->

## tr-visible-qwen3.6-12B-regression-v1 · sürüm 1

2026-09-13 · `four-authored-context-regressions` / `8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30` · tr · **regression** · `transcript-review` · **complete**

Görünür öneri politikası `tr-context-words-v2`: bütün eşlenebilir model değişiklikleri ölçülür; anlamsal uyarı öneriyi gizlemez. Bu ölçüm kullanıcı kaydı/onayı değildir.

Referans: `synthetic-authored`. İstek 4/4; başarısız 0 istek ham metinle paydada kaldı.

| Ham WER | Öneri WER | İyileşen / kötüleşen satır | Düzeltme isabeti | Temiz metni bozma |
|---|---|---|---|---|
| 12.50% | 12.50% | 0 / 0 | — (0/0) | 0.00% (0/2) |

16 referans kelime; değişen satır 0/4; metne eşlenemeyen öneri 4; medyan/en uzun süre 11.45/22.69 saniye.

İsabet, tek başına uygulanan önerinin referansa göre kelime hatasını azaltmasıdır; insan onayı veya anlamsal doğruluk garantisi değildir. Noktalama değişimleri lexical başarı sayılmaz. Bu deney konuşmacı tanıma skorunu ölçmez.

Modeller: `ollama/qwen3.6-12B` @ `afb0554657e2d4de0f95504944b0e22184582d4be91e2b3fd59c2180515d9d42`.

<!-- voiceup-data-v1 {"aggregate_sha256":"1703875eb7ba8f524cfe4e6a4efad2e6846fa492e6765e2e6b3b53e9a35668f9","evidence":null,"evidence_sha256":null,"experiment_id":"tr-visible-qwen3.6-12B-regression-v1","metadata":{"configuration_sha256":"d576372a75664a155914794a87801cf05a641191f78fc87e4ea102d3588cb4af","dataset":"four-authored-context-regressions","dataset_revision":"8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30","date":"2026-09-13","language":"tr","models":[{"id":"ollama/qwen3.6-12B","revision":"afb0554657e2d4de0f95504944b0e22184582d4be91e2b3fd59c2180515d9d42"}],"pipeline":"transcript-review","protocol_sha256":"8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30","role":"regression"},"record_sha256":"74b87db60610009ef24d72ff06fea2a5cae230f3201c7025bae64671eab71164","recorded_at_utc":"2026-09-13T17:47:41.076311+00:00","result":{"input_sha256":"8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30","kind":"transcript_review","metrics":{"accepted_edits":0,"beneficial_edits":0,"change_coverage":0.0,"changed_rows":0,"clean_damage_rate":0.0,"clean_rows":2,"completed_rows":4,"completion_coverage":1.0,"corrected_errors":2,"corrected_wer":0.125,"damaged_clean_rows":0,"edit_precision":null,"elapsed_seconds":56.87499999999636,"failed_rows":0,"harmful_edits":0,"improved_rows":0,"latency_max_seconds":22.687999999998283,"latency_median_seconds":11.44549999999981,"neutral_edits":0,"planned_rows":4,"raw_errors":2,"raw_wer":0.125,"reference_words":16,"rejected_edits":4,"worsened_rows":0},"policy_version":"tr-context-words-v2","protocol":"voiceup-context-review-visible-v1","reference_quality":"synthetic-authored","status":"complete"},"revision":1,"snapshot_sha256":"a705cab024cae5bd8b767262db9691449df509ac1ce977901c8cd4137de33027"} -->

## tr-visible-qwen3.5-27b-regression-v1 · sürüm 1

2026-09-13 · `four-authored-context-regressions` / `8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30` · tr · **regression** · `transcript-review` · **complete**

Görünür öneri politikası `tr-context-words-v2`: bütün eşlenebilir model değişiklikleri ölçülür; anlamsal uyarı öneriyi gizlemez. Bu ölçüm kullanıcı kaydı/onayı değildir.

Referans: `synthetic-authored`. İstek 4/4; başarısız 0 istek ham metinle paydada kaldı.

| Ham WER | Öneri WER | İyileşen / kötüleşen satır | Düzeltme isabeti | Temiz metni bozma |
|---|---|---|---|---|
| 12.50% | 6.25% | 1 / 0 | 66.67% (2/3) | 0.00% (0/2) |

16 referans kelime; değişen satır 2/4; metne eşlenemeyen öneri 0; medyan/en uzun süre 34.21/51.95 saniye.

İsabet, tek başına uygulanan önerinin referansa göre kelime hatasını azaltmasıdır; insan onayı veya anlamsal doğruluk garantisi değildir. Noktalama değişimleri lexical başarı sayılmaz. Bu deney konuşmacı tanıma skorunu ölçmez.

Modeller: `ollama/qwen3.5-27b` @ `7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e`.

<!-- voiceup-data-v1 {"aggregate_sha256":"ca1f0c8a0c4e3c9e781c413fa7a106da704303b5c30f480ac540dddb42b55818","evidence":null,"evidence_sha256":null,"experiment_id":"tr-visible-qwen3.5-27b-regression-v1","metadata":{"configuration_sha256":"d576372a75664a155914794a87801cf05a641191f78fc87e4ea102d3588cb4af","dataset":"four-authored-context-regressions","dataset_revision":"8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30","date":"2026-09-13","language":"tr","models":[{"id":"ollama/qwen3.5-27b","revision":"7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e"}],"pipeline":"transcript-review","protocol_sha256":"8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30","role":"regression"},"record_sha256":"cec73c345a5305d2f37abcd8174bbf686efc0325fbf0ebcbf7a941c8e2d51eda","recorded_at_utc":"2026-09-13T17:50:58.328128+00:00","result":{"input_sha256":"8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30","kind":"transcript_review","metrics":{"accepted_edits":3,"beneficial_edits":2,"change_coverage":0.5,"changed_rows":2,"clean_damage_rate":0.0,"clean_rows":2,"completed_rows":4,"completion_coverage":1.0,"corrected_errors":1,"corrected_wer":0.0625,"damaged_clean_rows":0,"edit_precision":0.6666666666666666,"elapsed_seconds":151.0470000000023,"failed_rows":0,"harmful_edits":1,"improved_rows":1,"latency_max_seconds":51.9529999999977,"latency_median_seconds":34.21100000000115,"neutral_edits":0,"planned_rows":4,"raw_errors":2,"raw_wer":0.125,"reference_words":16,"rejected_edits":0,"worsened_rows":0},"policy_version":"tr-context-words-v2","protocol":"voiceup-context-review-visible-v1","reference_quality":"synthetic-authored","status":"complete"},"revision":1,"snapshot_sha256":"9bdb6016383a3e0e96f4df4a9a9d6689178731e9e6b8246ceababe2433e1bc0a"} -->

## tr-visible-qwen3.5-9b-regression-v1 · sürüm 2

2026-09-13 · `four-authored-context-regressions` / `8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30` · tr · **regression** · `transcript-review` · **complete**

[Toplu kaynak kanıtı](docs/evidence/2026-09-13-saved-transcript-corrections/qwen3.5-9b-aggregate.json) · dosya SHA-256 `4eca5aada348b79459694c62b94794b5711e9d5a2f0e92b48017d07bf5895a56`

Görünür öneri politikası `tr-context-words-v2`: kayda uygun yanıttaki bütün model değişiklikleri ölçülür; anlamsal uyarı öneriyi gizlemez. Eşlenemeyen veya geçersiz yanıt ham metinle puanlanır. Bu ölçüm kullanıcı kaydı/onayı değildir.

Referans: `synthetic-authored`. İstek 4/4; başarısız 0 istek ham metinle paydada kaldı.

| Ham WER | Öneri WER | İyileşen / kötüleşen satır | Düzeltme isabeti | Temiz metni bozma |
|---|---|---|---|---|
| 12.50% | 12.50% | 0 / 0 | — (0/0) | 0.00% (0/2) |

16 referans kelime; değişen satır 0/4; kayda alınamayan öneri 0; medyan/en uzun süre 6.93/43.47 saniye.

İsabet, tek başına uygulanan önerinin referansa göre kelime hatasını azaltmasıdır; insan onayı veya anlamsal doğruluk garantisi değildir. Noktalama değişimleri lexical başarı sayılmaz. Bu deney konuşmacı tanıma skorunu ölçmez.

Modeller: `ollama/qwen3.5-9b` @ `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`.

<!-- voiceup-data-v1 {"aggregate_sha256":"d6e57a5423496ba2a9d663739a30bf3d44fb363706a30de18d1a84b7b15e1c41","evidence":"docs/evidence/2026-09-13-saved-transcript-corrections/qwen3.5-9b-aggregate.json","evidence_sha256":"4eca5aada348b79459694c62b94794b5711e9d5a2f0e92b48017d07bf5895a56","experiment_id":"tr-visible-qwen3.5-9b-regression-v1","metadata":{"configuration_sha256":"d576372a75664a155914794a87801cf05a641191f78fc87e4ea102d3588cb4af","dataset":"four-authored-context-regressions","dataset_revision":"8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30","date":"2026-09-13","language":"tr","models":[{"id":"ollama/qwen3.5-9b","revision":"6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"}],"pipeline":"transcript-review","protocol_sha256":"8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30","role":"regression"},"record_sha256":"f4fc921d868c8678dd8ac4a3695d501223c06c9fb5b014fe7ea406cbb3f5526e","recorded_at_utc":"2026-09-13T17:54:39.969160+00:00","result":{"input_sha256":"8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30","kind":"transcript_review","metrics":{"accepted_edits":0,"beneficial_edits":0,"change_coverage":0.0,"changed_rows":0,"clean_damage_rate":0.0,"clean_rows":2,"completed_rows":4,"completion_coverage":1.0,"corrected_errors":2,"corrected_wer":0.125,"damaged_clean_rows":0,"edit_precision":null,"elapsed_seconds":64.09400000000096,"failed_rows":0,"harmful_edits":0,"improved_rows":0,"latency_max_seconds":43.46900000000096,"latency_median_seconds":6.930000000000291,"neutral_edits":0,"planned_rows":4,"raw_errors":2,"raw_wer":0.125,"reference_words":16,"rejected_edits":0,"worsened_rows":0},"policy_version":"tr-context-words-v2","protocol":"voiceup-context-review-visible-v1","reference_quality":"synthetic-authored","status":"complete"},"revision":2,"snapshot_sha256":"29e5634c6cd2ae1ed8b9a620f0ee709be550712f19e062d8950805e6f8f5894a"} -->

## tr-visible-qwen3.6-12B-regression-v1 · sürüm 2

2026-09-13 · `four-authored-context-regressions` / `8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30` · tr · **regression** · `transcript-review` · **complete**

[Toplu kaynak kanıtı](docs/evidence/2026-09-13-saved-transcript-corrections/qwen3.6-12B-aggregate.json) · dosya SHA-256 `e00cd791b7b11e93299b8b44ff9fadd7de98ec804e000a1025e637e595d9e22d`

Görünür öneri politikası `tr-context-words-v2`: kayda uygun yanıttaki bütün model değişiklikleri ölçülür; anlamsal uyarı öneriyi gizlemez. Eşlenemeyen veya geçersiz yanıt ham metinle puanlanır. Bu ölçüm kullanıcı kaydı/onayı değildir.

Referans: `synthetic-authored`. İstek 4/4; başarısız 0 istek ham metinle paydada kaldı.

| Ham WER | Öneri WER | İyileşen / kötüleşen satır | Düzeltme isabeti | Temiz metni bozma |
|---|---|---|---|---|
| 12.50% | 12.50% | 0 / 0 | — (0/0) | 0.00% (0/2) |

16 referans kelime; değişen satır 0/4; kayda alınamayan öneri 4; medyan/en uzun süre 11.45/22.69 saniye.

İsabet, tek başına uygulanan önerinin referansa göre kelime hatasını azaltmasıdır; insan onayı veya anlamsal doğruluk garantisi değildir. Noktalama değişimleri lexical başarı sayılmaz. Bu deney konuşmacı tanıma skorunu ölçmez.

Modeller: `ollama/qwen3.6-12B` @ `afb0554657e2d4de0f95504944b0e22184582d4be91e2b3fd59c2180515d9d42`.

<!-- voiceup-data-v1 {"aggregate_sha256":"d20e71342779ca98772e45eb872a34f94c3e432a3a6e893255c71b061e5fe21c","evidence":"docs/evidence/2026-09-13-saved-transcript-corrections/qwen3.6-12B-aggregate.json","evidence_sha256":"e00cd791b7b11e93299b8b44ff9fadd7de98ec804e000a1025e637e595d9e22d","experiment_id":"tr-visible-qwen3.6-12B-regression-v1","metadata":{"configuration_sha256":"d576372a75664a155914794a87801cf05a641191f78fc87e4ea102d3588cb4af","dataset":"four-authored-context-regressions","dataset_revision":"8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30","date":"2026-09-13","language":"tr","models":[{"id":"ollama/qwen3.6-12B","revision":"afb0554657e2d4de0f95504944b0e22184582d4be91e2b3fd59c2180515d9d42"}],"pipeline":"transcript-review","protocol_sha256":"8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30","role":"regression"},"record_sha256":"ea5ab875b370659a9169bdb3d9f98753024f92079af1530ab598d71c4b2b6aba","recorded_at_utc":"2026-09-13T17:54:40.006620+00:00","result":{"input_sha256":"8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30","kind":"transcript_review","metrics":{"accepted_edits":0,"beneficial_edits":0,"change_coverage":0.0,"changed_rows":0,"clean_damage_rate":0.0,"clean_rows":2,"completed_rows":4,"completion_coverage":1.0,"corrected_errors":2,"corrected_wer":0.125,"damaged_clean_rows":0,"edit_precision":null,"elapsed_seconds":56.87499999999636,"failed_rows":0,"harmful_edits":0,"improved_rows":0,"latency_max_seconds":22.687999999998283,"latency_median_seconds":11.44549999999981,"neutral_edits":0,"planned_rows":4,"raw_errors":2,"raw_wer":0.125,"reference_words":16,"rejected_edits":4,"worsened_rows":0},"policy_version":"tr-context-words-v2","protocol":"voiceup-context-review-visible-v1","reference_quality":"synthetic-authored","status":"complete"},"revision":2,"snapshot_sha256":"33710413110902496648477d64bc54f13998228b9f24ba27082cb9b11e6a2af1"} -->

## tr-visible-qwen3.5-27b-regression-v1 · sürüm 2

2026-09-13 · `four-authored-context-regressions` / `8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30` · tr · **regression** · `transcript-review` · **complete**

[Toplu kaynak kanıtı](docs/evidence/2026-09-13-saved-transcript-corrections/qwen3.5-27b-aggregate.json) · dosya SHA-256 `f74595008ed2bbf4b75ccbc6eba2219d705879bb38bfbf09b08d01dc3a6ca3ad`

Görünür öneri politikası `tr-context-words-v2`: kayda uygun yanıttaki bütün model değişiklikleri ölçülür; anlamsal uyarı öneriyi gizlemez. Eşlenemeyen veya geçersiz yanıt ham metinle puanlanır. Bu ölçüm kullanıcı kaydı/onayı değildir.

Referans: `synthetic-authored`. İstek 4/4; başarısız 0 istek ham metinle paydada kaldı.

| Ham WER | Öneri WER | İyileşen / kötüleşen satır | Düzeltme isabeti | Temiz metni bozma |
|---|---|---|---|---|
| 12.50% | 6.25% | 1 / 0 | 66.67% (2/3) | 0.00% (0/2) |

16 referans kelime; değişen satır 2/4; kayda alınamayan öneri 0; medyan/en uzun süre 34.21/51.95 saniye.

İsabet, tek başına uygulanan önerinin referansa göre kelime hatasını azaltmasıdır; insan onayı veya anlamsal doğruluk garantisi değildir. Noktalama değişimleri lexical başarı sayılmaz. Bu deney konuşmacı tanıma skorunu ölçmez.

Modeller: `ollama/qwen3.5-27b` @ `7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e`.

<!-- voiceup-data-v1 {"aggregate_sha256":"3da57cffd189d717f784dd554ade1146950302444ddc071136d7bec96a7b14cf","evidence":"docs/evidence/2026-09-13-saved-transcript-corrections/qwen3.5-27b-aggregate.json","evidence_sha256":"f74595008ed2bbf4b75ccbc6eba2219d705879bb38bfbf09b08d01dc3a6ca3ad","experiment_id":"tr-visible-qwen3.5-27b-regression-v1","metadata":{"configuration_sha256":"d576372a75664a155914794a87801cf05a641191f78fc87e4ea102d3588cb4af","dataset":"four-authored-context-regressions","dataset_revision":"8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30","date":"2026-09-13","language":"tr","models":[{"id":"ollama/qwen3.5-27b","revision":"7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e"}],"pipeline":"transcript-review","protocol_sha256":"8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30","role":"regression"},"record_sha256":"0df8985b1c9eae0e72fb1c4c7ac8db8e4da1a6fda5966d449be09f63ab8b7901","recorded_at_utc":"2026-09-13T17:54:40.042094+00:00","result":{"input_sha256":"8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30","kind":"transcript_review","metrics":{"accepted_edits":3,"beneficial_edits":2,"change_coverage":0.5,"changed_rows":2,"clean_damage_rate":0.0,"clean_rows":2,"completed_rows":4,"completion_coverage":1.0,"corrected_errors":1,"corrected_wer":0.0625,"damaged_clean_rows":0,"edit_precision":0.6666666666666666,"elapsed_seconds":151.0470000000023,"failed_rows":0,"harmful_edits":1,"improved_rows":1,"latency_max_seconds":51.9529999999977,"latency_median_seconds":34.21100000000115,"neutral_edits":0,"planned_rows":4,"raw_errors":2,"raw_wer":0.125,"reference_words":16,"rejected_edits":0,"worsened_rows":0},"policy_version":"tr-context-words-v2","protocol":"voiceup-context-review-visible-v1","reference_quality":"synthetic-authored","status":"complete"},"revision":2,"snapshot_sha256":"331d5575427c678bdf8a6ab0877f5079de803640c91d571af835fa06c906b666"} -->

## tr-visible-qwen3.5-9b-regression-v1 · sürüm 3

2026-09-13 · `four-authored-context-regressions` / `8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30` · tr · **regression** · `transcript-review` · **complete**

[Toplu kaynak kanıtı](docs/evidence/2026-09-13-saved-transcript-corrections/qwen3.5-9b-aggregate.json) · dosya SHA-256 `4eca5aada348b79459694c62b94794b5711e9d5a2f0e92b48017d07bf5895a56`

Görünür öneri politikası `tr-context-words-v2`: kayda uygun yanıttaki bütün model değişiklikleri ölçülür; anlamsal uyarı öneriyi gizlemez. Eşlenemeyen veya geçersiz yanıt ham metinle puanlanır. Bu ölçüm kullanıcı kaydı/onayı değildir.

Ulaşan yanıt 4: değişmedi 4; öneri 0; eşlenemedi 0; geçersiz çıktı 0. Ulaşmayan istek 0; yanıtın ulaşması geçerli veya doğru öneri olduğu anlamına gelmez.

Kayda uygun satır 0; inceleme işaretli öneri 0. Bunlar kullanıcı onayı veya kayıt sayısı değildir.

Referans: `synthetic-authored`. İstek 4/4; başarısız 0 istek ham metinle paydada kaldı.

| Ham WER | Öneri WER | İyileşen / kötüleşen satır | Düzeltme isabeti | Temiz metni bozma |
|---|---|---|---|---|
| 12.50% | 12.50% | 0 / 0 | — (0/0) | 0.00% (0/2) |

16 referans kelime; değişen satır 0/4; kayda alınamayan öneri 0; medyan/en uzun süre 6.93/43.47 saniye.

İsabet, tek başına uygulanan önerinin referansa göre kelime hatasını azaltmasıdır; insan onayı veya anlamsal doğruluk garantisi değildir. Noktalama değişimleri lexical başarı sayılmaz. Bu deney konuşmacı tanıma skorunu ölçmez.

Modeller: `ollama/qwen3.5-9b` @ `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`.

<!-- voiceup-data-v1 {"aggregate_sha256":"d6e57a5423496ba2a9d663739a30bf3d44fb363706a30de18d1a84b7b15e1c41","evidence":"docs/evidence/2026-09-13-saved-transcript-corrections/qwen3.5-9b-aggregate.json","evidence_sha256":"4eca5aada348b79459694c62b94794b5711e9d5a2f0e92b48017d07bf5895a56","experiment_id":"tr-visible-qwen3.5-9b-regression-v1","metadata":{"configuration_sha256":"d576372a75664a155914794a87801cf05a641191f78fc87e4ea102d3588cb4af","dataset":"four-authored-context-regressions","dataset_revision":"8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30","date":"2026-09-13","language":"tr","models":[{"id":"ollama/qwen3.5-9b","revision":"6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"}],"pipeline":"transcript-review","protocol_sha256":"8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30","role":"regression"},"record_sha256":"5e02323c04d057feb44a55169d4470761403cb55521071dde76e819583684e41","recorded_at_utc":"2026-09-13T18:03:26.161272+00:00","result":{"input_sha256":"8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30","kind":"transcript_review","metrics":{"accepted_edits":0,"beneficial_edits":0,"change_coverage":0.0,"changed_rows":0,"clean_damage_rate":0.0,"clean_rows":2,"completed_rows":4,"completion_coverage":1.0,"corrected_errors":2,"corrected_wer":0.125,"damaged_clean_rows":0,"edit_precision":null,"elapsed_seconds":64.09400000000096,"failed_rows":0,"harmful_edits":0,"improved_rows":0,"latency_max_seconds":43.46900000000096,"latency_median_seconds":6.930000000000291,"neutral_edits":0,"planned_rows":4,"raw_errors":2,"raw_wer":0.125,"reference_words":16,"rejected_edits":0,"worsened_rows":0},"policy_version":"tr-context-words-v2","protocol":"voiceup-context-review-visible-v1","reference_quality":"synthetic-authored","review_required_edits":0,"saveable_rows":0,"status":"complete","visible_status_counts":{"invalid_output":0,"suggested":0,"unchanged":4,"unmapped":0}},"revision":3,"snapshot_sha256":"7b8b5ca232250c8d09f2bdfa913311af3421e405110405e89e10214d68e6e590"} -->

## tr-visible-qwen3.6-12B-regression-v1 · sürüm 3

2026-09-13 · `four-authored-context-regressions` / `8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30` · tr · **regression** · `transcript-review` · **complete**

[Toplu kaynak kanıtı](docs/evidence/2026-09-13-saved-transcript-corrections/qwen3.6-12B-aggregate.json) · dosya SHA-256 `e00cd791b7b11e93299b8b44ff9fadd7de98ec804e000a1025e637e595d9e22d`

Görünür öneri politikası `tr-context-words-v2`: kayda uygun yanıttaki bütün model değişiklikleri ölçülür; anlamsal uyarı öneriyi gizlemez. Eşlenemeyen veya geçersiz yanıt ham metinle puanlanır. Bu ölçüm kullanıcı kaydı/onayı değildir.

Ulaşan yanıt 4: değişmedi 0; öneri 0; eşlenemedi 4; geçersiz çıktı 0. Ulaşmayan istek 0; yanıtın ulaşması geçerli veya doğru öneri olduğu anlamına gelmez.

Kayda uygun satır 0; inceleme işaretli öneri 0. Bunlar kullanıcı onayı veya kayıt sayısı değildir.

Referans: `synthetic-authored`. İstek 4/4; başarısız 0 istek ham metinle paydada kaldı.

| Ham WER | Öneri WER | İyileşen / kötüleşen satır | Düzeltme isabeti | Temiz metni bozma |
|---|---|---|---|---|
| 12.50% | 12.50% | 0 / 0 | — (0/0) | 0.00% (0/2) |

16 referans kelime; değişen satır 0/4; kayda alınamayan öneri 4; medyan/en uzun süre 11.45/22.69 saniye.

İsabet, tek başına uygulanan önerinin referansa göre kelime hatasını azaltmasıdır; insan onayı veya anlamsal doğruluk garantisi değildir. Noktalama değişimleri lexical başarı sayılmaz. Bu deney konuşmacı tanıma skorunu ölçmez.

Modeller: `ollama/qwen3.6-12B` @ `afb0554657e2d4de0f95504944b0e22184582d4be91e2b3fd59c2180515d9d42`.

<!-- voiceup-data-v1 {"aggregate_sha256":"d20e71342779ca98772e45eb872a34f94c3e432a3a6e893255c71b061e5fe21c","evidence":"docs/evidence/2026-09-13-saved-transcript-corrections/qwen3.6-12B-aggregate.json","evidence_sha256":"e00cd791b7b11e93299b8b44ff9fadd7de98ec804e000a1025e637e595d9e22d","experiment_id":"tr-visible-qwen3.6-12B-regression-v1","metadata":{"configuration_sha256":"d576372a75664a155914794a87801cf05a641191f78fc87e4ea102d3588cb4af","dataset":"four-authored-context-regressions","dataset_revision":"8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30","date":"2026-09-13","language":"tr","models":[{"id":"ollama/qwen3.6-12B","revision":"afb0554657e2d4de0f95504944b0e22184582d4be91e2b3fd59c2180515d9d42"}],"pipeline":"transcript-review","protocol_sha256":"8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30","role":"regression"},"record_sha256":"57c10bbcf9aa084897df6be4f37ecbb9f25fd5a7e1ca660cf91a9a9c307605d4","recorded_at_utc":"2026-09-13T18:03:26.276524+00:00","result":{"input_sha256":"8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30","kind":"transcript_review","metrics":{"accepted_edits":0,"beneficial_edits":0,"change_coverage":0.0,"changed_rows":0,"clean_damage_rate":0.0,"clean_rows":2,"completed_rows":4,"completion_coverage":1.0,"corrected_errors":2,"corrected_wer":0.125,"damaged_clean_rows":0,"edit_precision":null,"elapsed_seconds":56.87499999999636,"failed_rows":0,"harmful_edits":0,"improved_rows":0,"latency_max_seconds":22.687999999998283,"latency_median_seconds":11.44549999999981,"neutral_edits":0,"planned_rows":4,"raw_errors":2,"raw_wer":0.125,"reference_words":16,"rejected_edits":4,"worsened_rows":0},"policy_version":"tr-context-words-v2","protocol":"voiceup-context-review-visible-v1","reference_quality":"synthetic-authored","review_required_edits":0,"saveable_rows":0,"status":"complete","visible_status_counts":{"invalid_output":0,"suggested":0,"unchanged":0,"unmapped":4}},"revision":3,"snapshot_sha256":"07999c31efe77f91718fad9356d0893dc31506eff0dba3acc10343f0d14457b5"} -->

## tr-visible-qwen3.5-27b-regression-v1 · sürüm 3

2026-09-13 · `four-authored-context-regressions` / `8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30` · tr · **regression** · `transcript-review` · **complete**

[Toplu kaynak kanıtı](docs/evidence/2026-09-13-saved-transcript-corrections/qwen3.5-27b-aggregate.json) · dosya SHA-256 `f74595008ed2bbf4b75ccbc6eba2219d705879bb38bfbf09b08d01dc3a6ca3ad`

Görünür öneri politikası `tr-context-words-v2`: kayda uygun yanıttaki bütün model değişiklikleri ölçülür; anlamsal uyarı öneriyi gizlemez. Eşlenemeyen veya geçersiz yanıt ham metinle puanlanır. Bu ölçüm kullanıcı kaydı/onayı değildir.

Ulaşan yanıt 4: değişmedi 2; öneri 2; eşlenemedi 0; geçersiz çıktı 0. Ulaşmayan istek 0; yanıtın ulaşması geçerli veya doğru öneri olduğu anlamına gelmez.

Kayda uygun satır 2; inceleme işaretli öneri 0. Bunlar kullanıcı onayı veya kayıt sayısı değildir.

Referans: `synthetic-authored`. İstek 4/4; başarısız 0 istek ham metinle paydada kaldı.

| Ham WER | Öneri WER | İyileşen / kötüleşen satır | Düzeltme isabeti | Temiz metni bozma |
|---|---|---|---|---|
| 12.50% | 6.25% | 1 / 0 | 66.67% (2/3) | 0.00% (0/2) |

16 referans kelime; değişen satır 2/4; kayda alınamayan öneri 0; medyan/en uzun süre 34.21/51.95 saniye.

İsabet, tek başına uygulanan önerinin referansa göre kelime hatasını azaltmasıdır; insan onayı veya anlamsal doğruluk garantisi değildir. Noktalama değişimleri lexical başarı sayılmaz. Bu deney konuşmacı tanıma skorunu ölçmez.

Modeller: `ollama/qwen3.5-27b` @ `7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e`.

<!-- voiceup-data-v1 {"aggregate_sha256":"3da57cffd189d717f784dd554ade1146950302444ddc071136d7bec96a7b14cf","evidence":"docs/evidence/2026-09-13-saved-transcript-corrections/qwen3.5-27b-aggregate.json","evidence_sha256":"f74595008ed2bbf4b75ccbc6eba2219d705879bb38bfbf09b08d01dc3a6ca3ad","experiment_id":"tr-visible-qwen3.5-27b-regression-v1","metadata":{"configuration_sha256":"d576372a75664a155914794a87801cf05a641191f78fc87e4ea102d3588cb4af","dataset":"four-authored-context-regressions","dataset_revision":"8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30","date":"2026-09-13","language":"tr","models":[{"id":"ollama/qwen3.5-27b","revision":"7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e"}],"pipeline":"transcript-review","protocol_sha256":"8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30","role":"regression"},"record_sha256":"837c4b6fad6979c8762116b7565fe4a897549bffa52ce349905769dce952f26c","recorded_at_utc":"2026-09-13T18:03:26.393662+00:00","result":{"input_sha256":"8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30","kind":"transcript_review","metrics":{"accepted_edits":3,"beneficial_edits":2,"change_coverage":0.5,"changed_rows":2,"clean_damage_rate":0.0,"clean_rows":2,"completed_rows":4,"completion_coverage":1.0,"corrected_errors":1,"corrected_wer":0.0625,"damaged_clean_rows":0,"edit_precision":0.6666666666666666,"elapsed_seconds":151.0470000000023,"failed_rows":0,"harmful_edits":1,"improved_rows":1,"latency_max_seconds":51.9529999999977,"latency_median_seconds":34.21100000000115,"neutral_edits":0,"planned_rows":4,"raw_errors":2,"raw_wer":0.125,"reference_words":16,"rejected_edits":0,"worsened_rows":0},"policy_version":"tr-context-words-v2","protocol":"voiceup-context-review-visible-v1","reference_quality":"synthetic-authored","review_required_edits":0,"saveable_rows":2,"status":"complete","visible_status_counts":{"invalid_output":0,"suggested":2,"unchanged":2,"unmapped":0}},"revision":3,"snapshot_sha256":"fb6c7bc099c2e182afc668fd31b04465c59a9a9797d226c63ccfb318a5fb1f06"} -->

## tr-visible-corrections-live-flow-20260913 · sürüm 1

2026-09-13 · `authored-text-http-browser-smoke` / `8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30` · tr · **smoke** · `transcript-review` · **unscored**

[Toplu kaynak kanıtı](docs/evidence/2026-09-13-saved-transcript-corrections/live-flow-aggregate.json) · dosya SHA-256 `555f5a395d6a3ec483206281e49c5c358d41eb728ce0689bb67e726e5757655e`

Kimlik precision/recall/F1, VoiceUp Score ve metin hata skoru: **— (ölçülmedi veya deney tamamlanmadı)**.

Gözlenen sayılar: `transcript_segments`=6.

<!-- voiceup-data-v1 {"aggregate_sha256":"57d8e4f51d28f2b89f49e9ba3ea5064ac0c61cbf6bebf3ced5f66bada43a1eba","evidence":"docs/evidence/2026-09-13-saved-transcript-corrections/live-flow-aggregate.json","evidence_sha256":"555f5a395d6a3ec483206281e49c5c358d41eb728ce0689bb67e726e5757655e","experiment_id":"tr-visible-corrections-live-flow-20260913","metadata":{"dataset":"authored-text-http-browser-smoke","dataset_revision":"8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30","date":"2026-09-13","language":"tr","pipeline":"transcript-review","role":"smoke"},"record_sha256":"68a76093d95af0e30747262697b9dee82666eed164d2c2aa255ed0f48bfac053","recorded_at_utc":"2026-09-13T18:09:19.342235+00:00","result":{"kind":"observation","metrics":null,"observations":{"transcript_segments":6},"source_sha256":"8c6f82f8215f771d8c324656b2ffb9fa3fb50b92b24852b816fcf89ac7b59d30","status":"unscored"},"revision":1,"snapshot_sha256":"740e846d86fb0935c3a934dfe3d1c8447ba5155f67f020cb27c9fb5cec3e1ad8"} -->
