# Uygulama planı — Modern toplantı çalışma alanı

Status: Accepted

Kaynak: [PRD](PRD.md). Sabit profil: `kt-vibecoding-python-web-v2`.

## Katman eşlemesi

| Gereksinim | Çıktı | Doğrulama |
|---|---|---|
| Requirement 1, 4 | `app/frontend/src/globals.css`, `components/SpeakerLayout.tsx`, ortak sunum bileşenleri | Ön yüz lint/derleme, gerçek tarayıcıda geniş/dar yerleşim ve gezinme |
| Requirement 1, 5, 6 | `pages/HomePage.tsx`, `pages/LoginPage.tsx`, `locales/tr.json`, `locales/en.json` | Giriş/ana sayfa/katalog testleri, iki dilde gerçek oturum |
| Requirement 1, 6 | Ana sayfada mevcut `MeetingService.list` ve `SpeakerService.profiles` kaynaklarına izne göre erişim | Gerçek toplamlar/son dört kayıt, yükleme/hata/boş sonuç ve yasak kaynağa istek gönderilmemesi testleri |
| Requirement 2, 4, 5 | `pages/MeetingsPage.tsx`, `components/MeetingUploadForm.tsx`, `components/MeetingSourceUpload.tsx` | Mevcut yükleme testleri, gerçek form etiketleri ve durumları |
| Requirement 3, 4, 5 | `pages/MeetingPage.tsx`, `components/MeetingResults.tsx`, `components/MeetingPagination.tsx` | Sonuç testleri, mevcut gerçek sonuç üzerinde tarayıcı incelemesi |
| Requirement 1, 3, 6 | `pages/SpeakerProfilesPage.tsx`, `pages/SpeakerAnalysisPage.tsx`, `pages/SpeakerJobPage.tsx`, ilgili form/sonuç bileşenleri | Mevcut profil/analiz testleri, sıradan salt okunur rol görünürlüğü |
| Requirement 4–6 | `e2e/speaker-identity/07-modern-workspace.mjs`, `e2e/QUALITY_MANIFEST.md` | Gerçek oturum, izinlere göre rota/eylem, TR/EN ve dar/geniş ekran |
| Tüm gereksinimler | Bu PRD'nin görevleri ve tarihli koşum raporu | Tam profil kalite kapısı, güvenlik kapısı sonucu, gerçek kanıt seviyesi |

Backend, API, üretilmiş OpenAPI/tipler, şema, migration, model, worker ve yeni
dağıtım ayarı: N/A — bu sunum değişikliğinde mevcut yeteneklerin sözleşmesi değişmez.
Mevcut üretim derlemesi ve chart doğrulaması tam kapıda yine çalışır.

## Uygulama sırası

1. Mevcut ekran, bileşen ve erişilebilirlik durumunu incele; ortak değişkenler ve
   bilgi hiyerarşisini belirle. Yeni davranış varsa ilgili sözleşme testini önce ekle.
2. Ortak gezinme ve sunum öğelerini, ardından giriş ve ana sayfayı uygula.
3. Toplantı yükleme/sonuç ve profil/analiz ekranlarını ortak örüntülere geçir;
   mevcut servis, izin ve form durumunu koru. İki katalog aynı değişiklikte güncellenir.
4. Ön yüz test, lint ve üretim derlemesini çalıştır. Gerçek ters proxy kökeninde
   sıradan rolün gerçek girişini, TR/EN gezinmesini ve mevcut kayıt görünümünü incele.
5. Geniş/dar ekran, klavye, odak ve konsol/ağ bulgularını düzelt; ilgili kontrolleri yinele.
   Dar sonuç görünümünde metni önce göster; konuşmacı ve metin başlıklarına yerel
   bağlantılarla klavye üzerinden geçiş sağla. Uzun konuşmacı listesi metne erişimi zorlaştırmaz.
6. `scripts/quality-gate.sh all` ve uygulanabilir güvenlik kontrolünü çalıştır;
   bütün başarısız/erişilemeyen kanıtları gerçek çıktıyla raporla.

## Çalıştırma sınırı

Kalıcı tarayıcı senaryosu mevcut ortak harness ve kabul edilmiş çevrimdışı tarayıcı
paketini kullanır. Paket yoksa yeni sürüm sessizce indirilmez; gerçek tarayıcıda
aynı kabul noktalarının gözlenmesi ayrıca kaydedilir. Senaryo iş, ses veya profil
oluşturmaz; sağlanan test hesabına gerçek formdan giriş yapıp mevcut veriyi okur.
Bu nedenle biyometrik doğruluk deneyi veya yeni cihaz yeterlilik ölçümü değildir.

11 Eylül uygulaması ve gözlenen kontroller
[koşum raporunda](../../../../docs/evidence/2026-09-11-modern-workspace/README.md) kayıtlıdır.
