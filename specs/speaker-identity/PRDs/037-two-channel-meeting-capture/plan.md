# Plan — Teams masaüstü toplantısını iki kanalla kaydetme

PRD: [037](PRD.md). Profil: `kt-vibecoding-python-web-v2`. Sıra, risk önce gelecek şekilde seçildi: tarayıcının Edge'de
sistem sesini vermesi doğrulanmadan sunucu işi yapılmaz.

## 1. Tarayıcı kaydı (Decision 1–2, 8–11; Requirement 1–2)

- `app/frontend/src/lib/meetingCapture.ts` (yeni):
  - Tek `AudioContext({ sampleRate: 16000 })` açılır; gerçek hız doğrulanır.
  - Mikrofon `getUserMedia`, sistem sesi `getDisplayMedia({ video: true, audio: {...}, systemAudio: "include", selfBrowserSurface: "exclude", surfaceSwitching: "exclude", monitorTypeSurfaces: "include" })` ile alınır.
  - Ses izi yoksa `capture_system_audio_missing` hatası verilir. Görüntü izi hemen `stop()` edilir.
  - Kaynaklar `ChannelMergerNode(2)` ile birleşir: kanal 0 mikrofon, kanal 1 sistem.
  - OPFS yazımı 007 ile aynıdır: 44 byte yer tutucu, sıralı ekleme, "Bitir"de 2 kanallı başlıkla mühürleme.
- `app/frontend/src/lib/meetingCapture.worklet.ts` (yeni):
  - İki kanalı iç içe PCM16'ya çevirir ve 2 saniyelik bloklar üretir.
  - Kanal başına seviye ve zarf değerlerini gönderir.
  - "Mikrofonumu kaydetme" iletisi gelince kanal 0'a sıfır yazar.
- `app/frontend/src/lib/meetingCapturePcm.ts` (yeni): saf yardımcılar.
  - 2 kanallı WAV başlığı.
  - Sessizlik ve karışma göstergeleri: zarf benzerliği; eşik ölçümle yazılır.
  - Parça özeti zinciri: `chain_n = SHA-256(chain_{n-1} ‖ sha256(part_n))`, `chain_0` 32 sıfır byte.
- `app/frontend/src/lib/captureUpload.ts` (yeni): sıralı gönderici.
  - Aynı anda bir parça yoldadır. Bellek kuyruğu en çok 32 MiB'tır.
  - Tekrar deneme zamanlayıcıyla değil, her yeni parça iletisiyle tetiklenir; bekleme süresi `Date.now` ile denetlenir.
  - Kuyruk taşarsa en eski parçalar bellekten düşer ve "Bitir"de mühürlü OPFS dosyasından okunur.
- Birim testleri bu dosyaların yanında, mevcut `microphoneCapture` testlerinin düzeniyle yazılır.

## 2. Arka uç sözleşmesi ve şema (Decision 3–5, 12; Requirement 3–4)

- Şema (`app/backend/app/domain/models/meeting.py`):
  - `meeting` tablosuna eklenecek sütunlar:
    - `capture_mode`: `file` veya `two_channel`; varsayılan `file`; denetim kısıtı var.
    - `capture_frames`: alınan örnek çerçevesi.
    - `capture_chain`: 64 hex.
    - `capture_part_at`: zaman damgası.
  - `meeting_speaker.channel`: boş, 0 veya 1.
  - `meeting_diarization.channel`: boş olmayan, varsayılan 0. Tekillik kiracı + toplantı + kanal olur.
  - `meeting_chunk`: parçanın kanalı sonuç içinde tutulur. Kanal ve pencere sırası toplantı süresinden ve kanal
    sayısından belirlenir; ayrı sütun gerekmez.
  - Açıklamalar modelde yazılır, migrasyonda doğrulanır.
- Migrasyon: `scripts/db.sh generate two_channel_meeting_capture`, gözden geçirme, yerelde uygulama, doğrulama.
- Alan sabitleri (`app/backend/app/domain/meeting.py`):
  - `CAPTURE_PART_SECONDS = 2`.
  - `CAPTURE_PART_MAX_BYTES` (4 saniyelik iki kanal 48 kHz sınırı).
  - `CAPTURE_IDLE_SECONDS = 120`.
  - Kanal adları.
- API (`app/backend/app/api/meetings/router.py`, `schemas/meeting.py`):
  - `POST /meetings/captures`: başlık, dil, katılımcı, örnekleme hızı. Yanıt `201 MeetingResponse` ve
    `status="uploading"` olur; boyut kotası en çok kaynak boyutuyla ayrılır.
  - `PUT /meetings/{id}/capture-frames/{start_frame}`: `application/octet-stream` ve `X-Chunk-SHA256` başlığı.
    Yanıtta `received_frames` döner. Hatalar:
    - `409 capture_gap`: beklenen çerçeveyle;
    - `409 capture_conflict`;
    - `409 meeting_not_capturing`;
    - `413`;
    - `422 capture_part_unaligned`.
  - `POST /meetings/{id}/capture/complete`: `frames`, `chain_sha256`. Yanıt `202`. Hatalar `409 capture_incomplete`
    ve `422 capture_chain_mismatch`.
  - `POST /meetings/{id}/capture/seal` ("Gelen kısmı işle"). Yanıt `202`. Son parça 120 saniyeden yeniyse
    `409 capture_active`; alınan ses yoksa `409 capture_empty`.
  - `MeetingResponse` alanları: `capture_mode`, `captured_seconds`, `capture_idle`.
  - `MeetingSpeakerResponse` alanı: `channel` (`microphone`, `system` veya boş).
- Servis ve depo:
  - Çerçeve konumu koşullu güncellemeyle ilerler: `WHERE capture_frames = :start`.
  - Tekrar gelen parça dosyadan okunup özetle karşılaştırılır.
  - Zincir sunucuda her eklemede güncellenir.
  - Mühürlemede başlık yazılır ve `MeetingAudioStorage.validate` çalışır; ardından `queued` olur.
- Depolama (`infrastructure/meeting_audio.py`): ham ekleme ile başlık yazımı ve kanal seçen okuma eklenir:
  - `recording_blocks(key, channel=None)`;
  - `window(..., channel=None)`;
  - `sample_with_manifest(..., channel=None)`.
  `None` bugünkü karışımdır.

## 3. Kanallara göre işleme (Decision 6–7; Requirement 5)

- `services/meeting_worker.py`:
  - İki kanallı toplantıda ayırma adımı her kanal için ayrı yapılır.
  - Parça sırası pencere ve kanal düzenindedir.
  - Bekleyen kelimeler kanal değişince devretmez.
  - Parçalı akışta eşleme yalnız aynı kanalın konuşmacılarıyla yapılır.
  - 120 dakika ve CPU kuralları 030 ile aynıdır.
- `services/meeting_chunks.py`:
  - Etiketle bağlama kanal ve etiket çiftiyle yapılır.
  - Metin satırları zaman sırasıyla listelenir: aynı anda konuşma iki satırdır, sıra numaraları kesinleşmede zamana göre
    verilir.
- `services/meeting_memory.py`: kanıt örneği konuşmacının kanalından alınır.
- Gözlemlenebilirlik: `meeting_capture` olayı tamamlanma ve mühürlemede yazılır (Requirement 7).
- Testler:
  - `tests/unit/test_meeting_capture.py` ve `tests/integration/test_meeting_capture.py` şunları kapsar: kiracı
    yalıtımı, tekrar, boşluk, çakışma, hizasız parça, zincir uyuşmazlığı, kesilen kaydın mühürlenmesi, 4 saat ve 2 GiB
    sınırı, tek kanallı toplantının değişmemesi, kanal başına ayırma ve kanıt.
  - Şema testi kanal sütunlarını ve kısıtları denetler.

## 4. Ön yüz ekranları (Decision 5, 7–11; Requirement 1)

- `components/MeetingCaptureRecorder.tsx` (yeni), `MeetingUploadForm.tsx` içinde üçüncü kaynak olarak yer alır. İçeriği:
  - bilgilendirme kutusu ve mikrofon seçimi;
  - seviye göstergeleri ve süre;
  - mikrofon anahtarı;
  - "Bitir";
  - uyarılar ve hata eşlemesi.
- `pages/MeetingPage.tsx`: iki kanallı kayıt yüklenirken iki durumdan biri gösterilir:
  - "Kayıt sürüyor";
  - "Kayıt kesildi" ile "Gelen kısmı işle" ve silme seçenekleri.
- `components/MeetingResults.tsx`: konuşmacı ve satırlarda kanal etiketi.
- `services/meetings.ts`: yeni işlemler, üretilmiş tiplerden.
- `src/locales/tr.json` ve `en.json`: tüm yeni metinler.
- Ön yüz testleri.

## 5. Tarayıcı senaryosu ve ölçüm (Requirement 8–9)

- `e2e/speaker-identity/17-meeting-two-channel-capture.mjs` (yeni):
  - Edge'de `--use-fake-device-for-media-stream`, `--use-fake-ui-for-media-stream` ve
    `--auto-select-desktop-capture-source` ile çalışır.
  - Gerçek giriş formunu kullanır, kayıt başlatır, en az 10 saniye kaydeder, "Bitir"e basar, işlenmeyi bekler.
  - Konuşmacı listesini ve kanal etiketlerini doğrular.
  - Temizlik `finally` bloğunda genel API ile yapılır.
  - `e2e/QUALITY_MANIFEST.md`'ye bir satır eklenir.
- Elle doğrulama ve ölçüm bu bilgisayarda yapılır: Requirement 9 (a), (b) ve (c). Toplu sonuçlar `results.md`'ye
  yazılır.

## Doğrulama komutları

- `scripts/quality-gate.sh all`: tam kapı; adımlar `KT_GATE_*` satırlarıyla izlenir.
- `scripts/db.sh generate|apply|validate|status`.
- Ön yüz birim testleri ve tarayıcı senaryosu bu kapının ve canlı koşunun parçasıdır.
