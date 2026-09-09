# PRD — Uzun toplantı kaydı analizi

Status: Draft

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [002 — long-recording-analysis](../../roadmap.md)
Tarih: 9 Eylül 2026. Seçilen sıra, kullanıcının asistana bıraktığı teknik karara dayanır.
Bağımlılık: 001 gerçek kişi doğruluk başlangıç deneyi; bu dosya uygulanmış özellik değildir.
Mimari gerekçe: [uzun kayıt kararı](../../../../docs/LONG_RECORDING_STRATEGY.md).

## Amaç, aktör ve sınır

Yetkili kullanıcı uzun, birden çok kişinin konuştuğu toplantı kaydını tek toplantı
olarak yükler; tek zaman çizelgesinde konuşmacıları görür. Sistem yeniden bağlantı
ve worker kesintisinden devam eder. İlk cihaz 4060; Spark ayrıca sınanır. Metne
çevirme, canlı yakalama ve platform bağlantısı bu yeteneğin kapsamına girmez.

## Kararlar

Decision 1: Ana kayıt diskte; aktarım, çözme ve çıkarım sınırlı bloklarla yapılır.
Mevcut tek konuşmacılı 120 saniye endpoint'i uzun toplantı API'sine dönüştürülmez.

Decision 2: İlk deney 60 saniyelik ana bölge ve her yanda 5 saniye bağlamdır.
Parça etiketi, toplantı kişi kümesi ve kalıcı kimlik ayrı varlıklardır. Kayıtlı
kişiler ortak tenant/model deposuyla eşleşir; belirsiz durumlar kimlik atamaz.

Decision 3: Karışık ses önce konuşmacılara ayrılır; profil karşılaştırmasına temiz
tek kişi pencereleri gider. Ayrı katılımcı kanalları korunur. Örtüşen konuşma tek
kişiye zorlanmaz. Kimlik ve yeni aday politikası ayrı kalite deneyinden geçirilir.

## Gereksinimler

Requirement 1: Sıralı, hashli aktarım parçaları ve kaynak manifesti ile kesintiden
devam; dosya adı yol olamaz. Bütün kaynak doğrulanmadan tamamlandı denmez.

Requirement 2: Toplantı ve parça işleri PostgreSQL'de kalıcı, tenant kapsamlı ve
idempotent olur; lease/fencing, iptal ve yeniden deneme davranışı tanımlanır.
Bir parçanın hatası sessizce toplantı başarısına dönüştürülmez.

Requirement 3: Örnek indisleri ve ana bölge sahipliğiyle zaman çizelgesi korunur;
bağlam çift sayılmaz. Parçalar arası kimlik değişimi ve yeni aday tekrarları
son toplantı birleştirmesinde düzeltilir; kararın model/sürüm/kaynağı izlenir.

Requirement 4: Arayüz aktarım, analiz ve son birleştirme ilerlemesini ayrı gösterir;
yenilemede devam eder. Ara sonuç ile kesin sonuç ayırt edilir.

Requirement 5: API/şema/migrasyon, gerçek disk/süre/kota limitleri, kaynak ve geçici
parçaların saklama/silme politikası, normalizasyon ve codec listesi uygulama öncesi
bu PRD'de kesinleşir. Tek temiz profil örneği tüm uzun kaydı süresiz tutturmamalıdır.

## Dağıtım ve doğrulama

Sabit FastAPI/React/PostgreSQL/pgvector yapısı, ayrı model servisi, çalışma anında
ağdan model indirmeme, tenant yetkileri ve içeriksiz loglar korunur. Uzun upload
proxy/storage sınırları ve sırları Compose/Helm üzerinde birlikte ele alınır.
CPU/GPU belleği, disk ve kuyruk yaşı ölçülür. ASR bağımlılığı N/A — transkript bu
kapsamda yoktur; ses ve kimlik verisi için saklama/erişim gereksinimi devam eder.

- [ ] 1/2/4 saatlik kaynakta bellek kayıt süresiyle doğrusal büyümez; kaynak raporu vardır.
- [ ] Kesinti, tekrar, iptal ve parça sınırındaki konuşma için kayıp/çift çıktı oluşmaz.
- [ ] 5/10/20/50 kayıtlı galeri ve toplantı konuşmacı sayısı ayrı raporlanır.
- [ ] Konuşmacı ayrım hatası, kalıcı kimlik hatası ve örtüşme hatası ayrı ölçülür.
- [ ] Yerel gerçek GPU/API/browser ile şema, yetki ve deployment kontrolleri geçer.

Open Question 1: Hedef toplantılara göre üst süre/boyut/kota ve saklama politikasının sayısal değerleri.
Open Question 2: Türkçe, gürültü ve çok kişi deneyinden sonra model seçimi ve kalite/gecikme eşikleri.
