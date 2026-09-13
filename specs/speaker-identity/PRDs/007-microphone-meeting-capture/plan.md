# Plan — Mikrofon kaydından toplantı analizi

Kaynak: [Accepted PRD](PRD.md). Sabit profil: `kt-vibecoding-python-web-v2`.
11 Eylül 2026 mikrofon isteğiyle etkinleştirilen plan; uygulama ve cihaz kanıtı
görevlerde ayrı işaretlenir.

1. Decision 1–2, 6 / Requirement 3: Mevcut 002 WAV/FLAC kaynağını, kesin boyut ve
   4 MiB parça sözleşmesini incele. `AudioWorklet` mono PCM16, gerçek örnekleme
   hızı ve OPFS desteğini hedef tarayıcıda denetle. Yeni decoder/API/şema/pin
   eklemeden aynı WAV sınırını kullan; mevcut disk adaptöründe Decision 7 RIFF
   kaynak bütünlüğünü önce kırmızı testlerle koru, gerçek decoder kanıtını kaydet.
2. Decision 3–5 / Requirement 1–2: `app/frontend/src/` altında işleme modülü,
   sınırlı üretici-yazıcı onayı, geçici OPFS dosyası ve yaşam döngüsünü testle
   geliştir. Tampon toplamı 16 MiB, dosya 2 GiB/4 saat ile sınırlı olsun; disk
   kotası/yazma hatası, bilinen süre/byte sınırında kayıpsız otomatik durdurma,
   son blok, PCM örnek sayısı, WAV başlığını tamamlama,
   iptal, cihaz/bağlam kesilmesi ve geç izin track temizliği testlerini ekle.
3. Decision 4–5 / Requirement 3–5: Mühürlenmiş `File` kaynağını mevcut
   `MeetingUploadForm` ve `meetingUpload` istemcisiyle aynı ekranda bütünleştir;
   mevcut dosya seçimi bağlamını değiştirme. Geçici dosyanın yükleme/tekrar
   boyunca yaşamını, tamamlanma
   ve iptal temizliğini koru; eksik kayıt API'de analiz işi başlatmasın. Başlık,
   dil, ayrı sayı ipuçları ve yetkiye bağlı hafıza seçeneklerini paylaş; TR/EN
   erişilebilir kontrolleri ve ortak 008 tasarımını aynı değişimde tamamla.
4. Veri/API/dağıtım: Yeni şema, migrasyon, OpenAPI alanı, decoder, bağımlılık,
   ayar veya model hazırlığı N/A; var olan otorite korunur. Derlenen worklet aynı
   kökenden sunulsun. Kullanım belgesine güvenli bağlam, OPFS/geçici disk, cihaz
   sınırı ve mikrofonun yalnız seçilen girişi yakaladığını ekle. Kontrat drift,
   bağımlılık kabulü ve chart kontrollerini N/A diye atlama.
5. Kabul ölçütleri: `e2e/speaker-identity/` altında paylaşılan harness kullanan
   kalıcı mikrofon senaryosu ve `e2e/QUALITY_MANIFEST.md` satırı ekle. Sıradan
   yetkili kullanıcıyla gerçek parola formundan TR/EN mikrofon→durdurma→WAV→
   metin/hafıza akışını çalıştır; test kaynaklarını kamu API'siyle `finally`
   yolunda temizle. Sahte kaynakla sınanan yaşam döngüsünü gerçek cihaz/metin
   kanıtından ayır. Dar ön yüz/decoder testlerinden sonra
   `scripts/quality-gate.sh all`, `scripts/security-gate.sh` ve
   `scripts/e2e.sh speaker-identity` komutlarını çalıştır; başarısız veya
   kullanılamayan adımları `53-test-run-report.md` biçiminde kaydet.

Bağımlılık: 002 yüklenen kaynak ve konuşmacılı metin/hafıza sözleşmesi.
Bu yetenek 002'nin mevcut dosya yüklemesini veya tanıma eşiklerini değiştirmez.
