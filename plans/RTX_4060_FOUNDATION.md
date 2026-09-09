# 4060 üzerinde ilk uygulama adımı

Tarih: 8 Eylül 2026. Tarihsel ön karar envanteri; aşağıdaki gözlemler kabul öncesine aittir.
Kapsam daha sonra kullanıcı tarafından kabul edildi. Güncel uygulama ve kanıt
[Accepted PRD görevlerinde](../specs/speaker-identity/PRDs/001-local-speaker-pilot/tasks.md) izlenir.
Bağlı kapsam: [001 — yerel konuşmacı pilotu](../specs/speaker-identity/PRDs/001-local-speaker-pilot/PRD.md).

## Önerilen ilk kullanıcı akışı

1. Kullanıcı giriş yapar ve `Konuşmacılar` ekranını açar.
2. Bir kişiye ait 20–30 saniyelik tek konuşmacılı örnekle profil oluşturur.
3. Başka bir ses kaydını yükler; analiz işinin bekleme/çalışma durumunu görür.
4. Sonuçta tanınan kişi veya `bilinmeyen/belirsiz` kararı ve gerekçesi görünür.
5. Beş kişilik kayıt setiyle karşılaştırma, ardından altıncı kişiyi açıkça ekleyip yeniden tanıma denenir.

Bu akış kalıcı veri, ekran, API, dosya yükleme, iş durumu ve gerçek model adaptörünü
birleştirir. Çok konuşmacılı otomatik toplantı bölümleme ve ASR ilk PRD'nin dışında
tutulmuştur; bunlar tamamlandı sayılmaz.

## Şu an gözlenen ortam

| Bileşen | Durum |
| --- | --- |
| GPU | RTX 4060 Laptop, 8188 MiB VRAM, sürücü 610.62 |
| Docker | Engine 29.6.1 ve Compose5.3.0 erişilebilir; önceki bağlantı engeli kalkmış |
| VoiceUp servisleri | Henüz çalışmıyor |
| Mevcut ses ortamı | Python3.12.10, torch2.8.0+cpu; CUDA aktif değil |
| Python3.13 | 3.13.14 kurulu; oluşturucu ayrı sanal ortamda mevcut |
| Host Node | 26.4.0; ürün Node22 ister, sabit container çalışma ortamı kullanılacak |
| Yerel adres | 8080 başka uygulamaya ait; 8081 yeniden boşluk kontrolünden sonra kullanılacak |
| Container girdileri | Gerekli10 sabit image/base image yerelde bulunamadı |
| Platform araçları | Helm ve güvenlik tarayıcıları mevcut PATH'te yok; bundle/scanner ortamı ayarlı değil |
| GPU servisi | Compose'ta henüz yok; Alpine web image'ı GPU çıkarım ortamı sayılmıyor |

Bu envanter okuma ve sürüm/bağlantı kontrollerine dayanır; image indirme, yeni paket
kurma, servis başlatma veya uygulama veritabanı migrasyonu yapılmadı. Mevcut başka
uygulamanın servislerine dokunulmadı.

## Kapsam kabul edilince izlenecek hazırlık sırası

**Ortam:** Sabit image/bundle girdilerini ve araçları hazırla; VoiceUp için ayrı local
ayarları/portu kaydet. Docker'ın erişilebilir olması platformun çalıştığı anlamına gelmez.
PostgreSQL, backend, frontend ve giriş akışını kendi veri alanında doğrula.

**4060 çıkarımı:** Onaylı bağımlılık envanteriyle uyumlu CUDA ortamı ve önceden hazırlanmış
model paketini oluştur. Önce gerçek CUDA tensor/model kontrolü; sonra ses çıkarımı.
Mevcut CPU kilidini sessizce değiştirme. İşçi aynı anda bir işi yürütür; Spark için
aynı HTTP sözleşmesinin ARM64/NVIDIA image karşılığı ayrıca doğrulanır.

**Ürün dilimi:** Kabul edilmiş PRD'den şema, pgvector, profil/iş API'si, tipli çıkarım
adaptörü ve ekran/test görevlerini türet. Idempotency, tenant izolasyonu ve başarısız
sesin profil oluşturmaması işin parçasıdır.

**Kanıt:** Gerçek PostgreSQL ve tarayıcı akışı,4060 model çıkarımı ve ayrı oturumlu
ses deneyi farklı sonuçlar olarak raporlanır. Kullanıcı sesleri yoksa Türkçe doğruluk
deneyi eksik kalır; sentetik vektör veya kısa model örneği onun yerine konmaz.

## Envanter alındığındaki kabul sınırı

Bu envanter alındığında PRD **Draft** durumundaydı; sonrasında Accepted olarak kaydedildi. `rules/10-spec-first.md` açık Accepted PRD olmadan iş kodu
üretimini yetkilendirmez. İncelenebilir kapsam hazırlandı; kabul edilmeden yeni endpoint,
domain tablosu, migrasyon, GPU işleyici veya UI bağlaması oluşturulmadı.

Gözlenen hazırlık kontrolleri [koşum raporunda](../docs/evidence/2026-09-08-rtx4060-foundation/README.md).
