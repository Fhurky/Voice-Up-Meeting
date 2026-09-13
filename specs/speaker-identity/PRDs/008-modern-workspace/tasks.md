# Görevler — Modern toplantı çalışma alanı

Kaynak: [PRD](PRD.md), [plan](plan.md).
Profil: `kt-vibecoding-python-web-v2`.

- [x] Kullanıcının görsel yenileme talimatını Accepted 008 PRD ve karşılıklı yol haritası bağlantısıyla kaydet. Kanıt: bu dizin ve `../../roadmap.md`.
- [x] Mevcut geniş/dar ekran görünümü ve davranış sınırlarını incele; tasarım kararlarını uygula. Çıktı: ortak anlamsal değişkenler ve gezinme düzeni; kanıt: kaynak incelemesi ve tarayıcı görüntüsü.
- [x] Giriş ve ana sayfayı yenile; gerçek giriş, yerel admin ve izin davranışını koru. Çıktı: ilgili sayfalar/kataloglar; kanıt: giriş/ana sayfa testleri ve gerçek giriş.
- [x] Toplantı listesi, yükleme, ilerleme ve konuşmacılı sonuç sunumunu yenile. Çıktı: toplantı sayfaları/bileşenleri; kanıt: mevcut sözleşme testleri ve gerçek sonuç incelemesi.
- [x] Profil, tek ses analizi ve iş sonucu sunumunu yenile. Çıktı: profil/analiz sayfaları ve ortak bileşenler; kanıt: profil/sonuç testleri ve sıradan rol görünürlüğü.
- [x] TR/EN anahtar eşitliği, dar/geniş yerleşim, semantik etiket ve klavye/odak erişimini doğrula. Çıktı: katalog ve erişilebilir etkileşimler; kanıt: otomatik testler ve gerçek tarayıcı.
- [x] Ortak harness kullanan kalıcı çalışma alanı senaryosunu oluştur ve kalite manifestine kaydet. Çıktı: `e2e/speaker-identity/07-modern-workspace.mjs`; kanıt: `node --check` yeni 07 ve uyarlanan 04/05/auth02 dosyalarında exit 0; canlı çalıştırma kanıtı henüz yoktur.
- [x] Ön yüz lint, üretim derlemesi ve testleri çalıştır; tam `scripts/quality-gate.sh all` sonucunu kaydet. Çıktı: tarihli koşum raporu; kanıt: gerçek komut/çıktı/sayılar.
- [x] Gerçek ters proxy üzerinde sıradan rol, iki dil ve mevcut gerçek toplantı sonucunu gözle; konsol/ağ bulgularını incele. Çıktı: tarayıcı kanıtı; kayıt modeli doğruluk kabulüne dönüştürülmez.
- [x] Güvenlik kontrolü ve erişilemeyen kontrolleri açıkla; eksik görevleri ve ulaşılan en yüksek kanıt seviyesini son raporda belirt. Çıktı: sabit biçimli koşum raporu; L3 kullanıcı kabulü ayrıca gerekir.

Yeni commit/push bu sunum kabulünün görevi değildir.

## Gözlenen kanıt ve açık kontroller

11 Eylül son kaynakta tam kalite kapısı başarılı: 595 backend + 96 frontend testi.
Gerçek sıradan hesaplarla TR/EN ve 1440/390 CSS pikselde 22 ekran kontrolü geçti.
Kalıcı tarayıcı senaryosunun dosyası/sözdizimi tamamlandı; kabul edilmiş tarayıcı
paketi eksik olduğundan yürütücü çalışmadı. Gitleaks eksikliği nedeniyle güvenlik
kapısı da çalışmadı. Yukarıdaki açıklama/raporlama görevi bu kontrollerin geçtiği
anlamına gelmez. Canlı görünüm kanıtı L2; kullanıcı kabulü L3 gözlenmedi.

[Sabit biçimli koşum raporu](../../../../docs/evidence/2026-09-11-modern-workspace/README.md)
komutları, ara hataları, yan etkileri ve eksik kanıtları kaydeder.
