# PRD — Toplantıları CPU'da çalıştırma

Status: Accepted

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [027 — meeting-cpu-mode](../../roadmap.md)
Profil: `kt-vibecoding-python-web-v2`; şema profili `sqlalchemy-alembic`.
Kaynak ve kabul (30 Ekim 2026): Kullanıcı, insanların ilk denemelerini hızlıca yapabilmesi için uygulamanın ayarlarla CPU'da
çalışabilmesini istedi. Kabul edilirse 005'in "CPU yalnız tek konuşmacılı pilot içindir" sınırı toplantı için bu PRD ile kalkar.

## Amaç ve önceki durum

Toplantı işleme GPU ister: çalışma profili, Whisper yüklemesi ve hazırlık denetimi `cuda` varsayar. 005 CPU modu yalnız tek
konuşmacılı pilotu çalıştırır. Hedef: GPU'su olmayan kişinin kısa toplantılarla sistemi deneyebilmesi. CPU modu üretim kapasitesi
değildir; yavaştır ve bunu ekranda söyler.

## Kararlar

Decision 1: Seçim açılışta yapılır, uygulama içi düğme yoktur; modeller servis açılırken bir kez yüklenir. `scripts/start-local.ps1
-Processor Cpu` veya `outputs/local-meeting-processor.txt` içindeki `cpu` değeri seçer. Seçim kalıcıdır; `-Processor Gpu` geri alır.
Varsayılan GPU'dur. GPU yokken sessiz CPU'ya geçiş olmaz.

Decision 2: Yeni çalışma profili `x86_64-meeting-cpu`'dur. Mevcut toplantı imajı kullanılır, yeni paket veya bağımlılık kaydı yoktur.
`require_cpu` bu profilde CUDA içeren PyTorch yapısını kabul eder, çünkü aynı yapı CPU'da da çalışır. Whisper `int8` ile
çalışır. Model kimlikleri ve eşikler GPU ile aynıdır. Kullanıcı çoklu çekirdek kullanımını şart koştu: Whisper fiziksel çekirdek sayısı
kadar iş parçacığı kullanır. Mantıksal çekirdek sayısı denendi ve 2 dakikalık klibi 30 yerine 310 saniyede işledi (16 fiziksel, 32 mantıksal
çekirdek; 2,3 çekirdek kullanıldı). PyTorch zaten fiziksel çekirdek sayısını seçer.

Decision 3: Kompozisyon `app/infra/docker-compose.meeting-cpu.yml` ile değişir: NVIDIA rezervasyonu kalkar, cihaz `cpu` olur, parça zaman
aşımı üst sınır olan 1800 saniyeye çıkar. Daha yavaş bir parça mevcut `job_timeout` hatasıyla biter.

Decision 4: Arka uç `GET /meetings/processing-mode` ile `gpu` veya `cpu` döndürür (`meeting_processing_device` ayarı). Yükleme formu `cpu`
modunda yavaşlık uyarısı gösterir ve kısa kayıt önerir. Uç nokta `meeting_analysis:read` ister; kişisel veri içermez.

Decision 5: CPU sonuçları GPU ile aynı sayılmaz. Doğruluk ve süre kısa bir AMI toplantısında ölçülür ve `x86_64-meeting-cpu` profiliyle
ayrı kaydedilir. GPU'suz makinede ilk kurulum bu makinede sınanamaz; görevlerde açık kalır.

## Gereksinimler

Requirement 1: Çıkarım servisi: profil, `require_cpu`, `LocalMeetingModels`; testleriyle.

Requirement 2: Arka uç: cihaz doğrulaması `cpu` kabul eder; ayar yüzeyleri; `processing-mode` uç noktası, yetki testi, OpenAPI ve tipler.

Requirement 3: Ön yüz: `cpu` modunda uyarı, TR/EN metin, birim testi.

Requirement 4: Açılış: kompozisyon dosyası, `start-local.ps1`, `stack.sh`, hazırlık denetimi ve belgeler.

Requirement 5: Bu makinede GPU gizlenerek gerçek CPU koşumu; süre ve GPU sonucuyla fark raporlanır.

## Katmanlar

Şema: N/A — yeni tablo veya kolon yok. Vektör: N/A — modeller ve boyutlar aynı. Gözlemlenebilirlik: N/A — mevcut `device` alanı yeterli.
Dağıtım: N/A — yalnız yerel kompozisyon; kurum dağıtımı GPU kullanır (018).

## Kabul ölçütleri

- [ ] Birim testleri ve tam kalite kapısı geçer.
- [ ] GPU görünmeyen konteynerde gerçek toplantı işlenir; süre ve GPU sonucuyla fark raporlanır.
- [ ] GPU modu değişmeden çalışır; seçim geri alınabilir.
- [ ] GPU'suz bir makinede ilk kurulum denenir (L3).
