# Plan — Toplantı sürerken canlı ara sonuç

PRD: [003](PRD.md). Profil: `kt-vibecoding-python-web-v2`. Bu plan
[037](../037-two-channel-meeting-capture/PRD.md) tamamlandıktan sonra uygulanır. 037'nin kayıt, aktarım ve kanal
okuma yüzeyini kullanır.

## 1. Çıkarım servisi (Decision 2; Requirement 1)

- `app/inference/voiceup_inference/api.py` içine yeni uç nokta `POST /v1/meeting-live-window` eklenir.
  - Gövde: tek kanallı 16 kHz PCM16 WAV, en çok 30 saniye.
  - Başlıklar: yazıya çevrilecek aralık ve dil.
  - Tek iş yuvasını (`runtime.claim()`) bugünkü uç noktalarla paylaşır. CPU modunda `409 live_unavailable` döner.
- `meeting_runtime.py`:
  - Pencerede ses etkinliği ve konuşmacı ayırma: 030 tarifi, pencereye uygun ayarla.
  - Yerel küme başına izleme vektörü.
  - Yalnız kapanmış bölütlerde Whisper.
  - Bir bölüt sessizlikle ya da en çok 10 saniyede kapanır.
- Testler `app/inference/tests/test_meeting_live_window.py` dosyasında: meşgul, hazır değil, bozuk girdi, sınır, CPU
  reddi ve sonuç sözleşmesi.

## 2. Arka uç (Decision 3–6, 8–9; Requirement 2, 4)

- Şema:
  - `meeting_live_speaker`: kiracı, toplantı, kanal, sıra, 256 boyutlu izleme vektörü, kanıt süresi, ön tahmin kişisi
    ve puanı, sürüm.
  - `meeting_live_line`: kiracı, toplantı, sıra numarası, kanal, canlı konuşmacı, başlangıç, bitiş, metin.
  - İki tablo da yan tablodur, `public_id` yoktur. Açıklamalar ve gözden geçirilmiş migrasyon vardır.
- Port ve adaptör: `MeetingAnalysisPort.analyze_live_window`, `HttpMeetingAdapter` içinde uygulanır.
- `services/meeting_live.py` (yeni):
  - Oturum kilidi.
  - Kanal başına tur: yaklaşık 3 saniye, en çok 15 saniyelik pencere.
  - Eşleme (kosinüs, başlangıç eşiği 0,6), yeni konuşmacı (en az 2 saniye) ve birleştirme.
  - 10, 20 ve 40 saniyede ön tahmin: `MatchPolicy`, katılımcı listesi; ECAPA vektörü saklanmaz.
  - 60 saniye geride kalınca en yeni sese atlama.
- Worker önceliği (`speaker_worker.py`, `meeting_worker.py`):
  - Canlı oturum varken başka toplantının tek geçişi ve parça analizi başlamaz.
  - Bir servis aynı anda bir canlı oturum işler; ikinci oturum için `live_capacity_full` durumu gösterilir.
- API: `GET /meetings/{id}/live?after_seq=&version=`. Yanıtta yeni satırlar, değişen konuşmacılar, sürüm, geride kalma
  süresi ve kapasite durumu döner. Toplantı okuma izni ve kiracı kapsamı uygulanır.
- Temizlik: canlı veri kesin sonuç hazır olunca, toplantı silinince ve yarım yükleme temizliğinde silinir.
- Olay: `meeting_live_cycle`.
- Testler: birim testleri ve canlı PostgreSQL entegrasyon testleri; kapsamları PRD'deki Requirement 2 listesidir.

## 3. Ön yüz (Decision 7; Requirement 3)

- `components/MeetingLivePanel.tsx` (yeni), 037 kayıt ekranının altında yer alır. İçeriği:
  - satırlar;
  - konuşmacı ve ön tahmin;
  - kanal etiketi;
  - "geçici" işareti;
  - geride kalma göstergesi;
  - "Takip et" anahtarı.
- Ekran okuyucuya yeni satır sayısı duyurulur.
- Yoklama hook'u 2 saniyede bir çalışır. Sayfadan çıkınca ve oturum değişince eski yanıtlar yok sayılır.
- `services/meetings.ts`, yerelleştirme ve ön yüz testleri.

## 4. Senaryo ve ölçüm (Requirement 5–6)

- 037 senaryosuna canlı panel denetimi eklenir.
- Ölçüm araçları:
  - Gerçek zamanlı AMI oynatma betiği: genel API üzerinden, sistem kanalına, mikrofon kanalı sessiz.
  - Gecikme kaydı: konuşma bitişi ile satırın ekranda görünmesi arası.
- Sonuçlar `results.md`'ye yazılır.

## Doğrulama komutları

- `scripts/quality-gate.sh all`.
- `scripts/db.sh generate|apply|validate|status`.
- Çıkarım testleri.
- Canlı tarayıcı koşusu.
