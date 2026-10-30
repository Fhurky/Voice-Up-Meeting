# PRD — Ayarlar menüsü ve işlemci seçimi

Status: Accepted

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [028 — settings-processor-switch](../../roadmap.md)
Profil: `kt-vibecoding-python-web-v2`; şema profili `sqlalchemy-alembic`.
Kaynak ve kabul (30 Ekim 2026): Kullanıcı GPU/CPU gibi işler için sol menüye Ayarlar eklenmesini şart koştu. Bu PRD
[027](../027-meeting-cpu-mode/PRD.md) Decision 1'deki "uygulama içi düğme yoktur" kararının yerine geçer ve Decision 4'teki
ortam ayarına dayalı modu çalışan cihazı soran bir okumayla değiştirir.

## Amaç ve önceki durum

İşlemci seçimi bugün yalnız açılış komutuyla yapılır; kullanıcı ekrandan göremez ve değiştiremez. Hedef: yöneticinin sol menüdeki Ayarlar
sayfasından çalışan işlemciyi görmesi ve GPU ile CPU arasında geçmesi. Sayfa ileride başka ayarları da alacak biçimde kurulur, ama bugün
yalnız işlemci seçimini içerir.

## Kararlar

Decision 1: Sol menüde "Ayarlar" bağlantısı ve `/settings` sayfası eklenir. Sayfa ve geçiş yalnız `super_admin` içindir; diğer kullanıcılar
menüyü görmez, uç nokta 403 döner. Yeni izin ve şema yoktur.

Decision 2: Geçiş konteyner yeniden başlatılmadan yapılır: servis süreci aynı komutu seçilen cihazla kendi yerine yeniden başlatır (`exec`).
Aynı süreçte model değiştirmek denendi ve reddedildi: dört geçişten sonraki CPU işinde süreç 6,3 GB'a çıktı, sanal makine belleği yetmedi ve
işletim sistemi süreci öldürdü (31 Ekim 2026). Yeni süreç temiz başlar, önceki cihazın belleği kalmaz. Yükleme başarısız olursa servis önceki
cihazla yeniden başlar ve hata gösterilir.

Decision 3: Geçiş 110 saniyelik vekil sunucu sınırını aşabildiği için istek hemen döner, sayfa durumu izler. İş işlenirken geçiş reddedilir
(409 `inference_busy`); sayfa bunu açıkça söyler. Geçiş sırasında gelen iş mevcut yeniden deneme akışıyla bekler.

Decision 4: GPU, servis GPU'yu göremiyorsa seçilemez ve sayfa sebebini söyler. GPU'suz makine `-Processor Cpu` ile açılır; o kurulumda GPU
seçeneği kapalı görünür. GPU'lu makinede servis GPU görünür şekilde açılır ve CPU'ya geçiş ekrandan yapılır.

Decision 5: Seçim kalıcı değildir: servis yeniden başlayınca açılış ayarına döner ve sayfa bunu belirtir. Kalıcı seçim için şema gerekir; ihtiyaç
görülürse ayrı PRD olur.

Decision 6: Parça zaman aşımı yerel kompozisyonda 1800 saniyedir, çünkü cihaz çalışırken değişebilir. GPU'da bu yalnız takılan bir işin geç
fark edilmesi demektir.

Decision 7: `GET /meetings/processing-mode` ayar yerine çalışan servisin cihazını döndürür; form uyarısı buna göre çıkar. Servis okunamazsa
`unknown` döner ve uyarı gösterilmez. `meeting_processing_device` ayarı kaldırılır.

## Gereksinimler

Requirement 1: Çıkarım servisi: yetkili `GET /v1/meeting-processor` durumu ve `gpu_available` değerini döndürür, `POST` süreci yeniden başlatır;
`/meeting-ready` sözleşmesi değişmez. Yoğunluk, kullanılamayan GPU ve yükleme hatasında geri dönüş testleri.

Requirement 2: Arka uç: `GET` ve `PUT /meetings/processor`, yalnız `super_admin`; adaptör, hata eşleme, yetki testleri, OpenAPI ve tipler.

Requirement 3: Ön yüz: Ayarlar sayfası, menü bağlantısı, TR/EN metinler, yükleniyor/hata/meşgul durumları, klavye erişimi ve birim testleri.

Requirement 4: Kalıcı tarayıcı senaryosu: yönetici gerçek geçiş yapar, sıradan kullanıcı menüyü görmez.

## Katmanlar

Şema: N/A — kalıcı seçim yok. Vektör: N/A. Gözlemlenebilirlik: mevcut `device` alanı ve `inference_http` kaydı yeterli. Dağıtım: N/A — kurum
dağıtımı GPU kullanır; uç nokta yalnız `super_admin` içindir. Başlatma betiği: `start-local.ps1` servisi beklenen cihazda bulmazsa yeniden başlatır,
böylece ekrandan yapılan seçim açılış ayarının önüne geçip başlatmayı takmaz.

## Kabul ölçütleri

- [x] Birim testleri ve tam kalite kapısı geçer.
- [x] Çalışan uygulamada yönetici GPU'dan CPU'ya ve geri geçer; her iki cihazda bir toplantı işlenir.
- [x] Sıradan kullanıcı Ayarlar'ı görmez, uç nokta 403 döner.
- [ ] Kullanıcı sayfayı kabul eder (L3).
