# Koşum raporu — 2026-09-10 · 50 kişilik doğruluk hedefinin ürün kotasından ayrılması.

1. Sonuç: Sayıya bağlı engelin kaldırılması canlı uygulamada gözlendi; yeni doğruluk kazanımı iddia edilmez — birim/entegrasyon 370 başarılı / tarayıcı 6 başarılı / atlanan 1; ayrıca gerçek HTTP/Spark akışı 1 başarılı; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`; son kaynaklar için Python 3.13/Docker/PostgreSQL ve gerçek yerel tarayıcı. Odaklı ve Windows tekrarları toplamda ikinci kez sayılmadı.

   | Kanıt | Sonuç |
   | --- | --- |
   | [Tam profil kapısı](quality-gate-report.md) | 97 backend + 39 frontend = 136 başarılı, 0 atlama |
   | [Değerlendirme/ölçüm/veri planlayıcı](evaluator-run-report.md) | Python 3.13: 234 başarılı, 1 Windows testi atlandı; Windows uyumlu tekrar 201 başarılı |
   | [Backend kırmızı/yeşil](backend-report.md) | 50→51, 200→201, eşzamanlılık ve eski iş davranışı; son kapı içinde tekrarlandı |
   | [Frontend kırmızı/yeşil](frontend-green-report.md) | 50/51/100/200/201 toplamlarında kayıt ve mevcut profile ekleme |
   | [Gerçek uygulama](live-report.md) | 51. profil Spark `cuda:0` üzerinde kaydoldu; Türkçe/İngilizce 6 kabul noktası |
   | [Mevcut sonuçların tanısı](diagnosis-report.md) | 40/50 kayıt; genel 116/150, kayıtlı kişilerde 116/120; yeni deney değil |
   | [Araştırma ve kontrollü deney önerisi](../../../plans/SPEAKER_QUALITY_50.md) | Önce kayıt kalitesi, sonra model karşılaştırması ve temsilî Türkçe test |

3. Maddeler:

   **KUSUR**
   M1 Kullanıcının 50 kişilik doğruluk hedefi yanlışlıkla kota olmuştu; servis/işçi/API/UI kotası kaldırıldı, sözleşmeler yeniden üretildi ve çalışan yerel uygulama yenilendi.
   M2 Değerlendirme girdileri 200 bilinen/200 bilinmeyene genişletildi; 201. dönüş profili ve pahalı çalışmadan önce bildirim/işlem bütçesi doğrulaması koruma altına alındı.
   **TUZAK**
   M3 370 testin geçmesi konuşmacı doğruluğu değildir. İlk Windows Python 3.12 dört paket koşumundaki yedi hazırlayıcı hatası ayrı raporda korunur; sabit profilin Python 3.13 son koşumu başarılıdır.
   **GÖZLEM**
   M4 Model, tanıma eşikleri ve önceki deney sonuçları değişmedi. Önceki kapasite kanıtı o tarihteki kararın tarihsel kaydı olarak korundu; mevcut karar [Decision 11](../../../specs/speaker-identity/PRDs/001-local-speaker-pilot/PRD.md) ile izlenir.
   **AÇIK**
   M5 Güvenlik kapısı `gitleaks`, kalıcı Playwright komutu kabul edilmiş çevrimdışı paket eksikliğinde durdu. Yeni model doğruluğu, 50 gerçek kayıtlı kişiyle temsilî Türkçe kabulü ve L3 açık; tam yetenek için koşulsuz tamamlanma iddiası yok.
   M6 Linux'taki Windows junction testi atlandı; ilk Windows koşumunda geçti. Bu platform ayrımı toplamdan gizlenmedi.
   **YAN-ETKİ**
   M7 Ürün kotası ve değerlendirme girdi sınırları için kaynaklar/testler/sözleşmeler/belgeler güncellendi; izole canlı fikstüre bir gerçek ses profili eklendi, durdurulmuş tünel açıldı. Bağımlılık/şema/model değişikliği ve Git yayını yapılmadı.

Kaynakların son hashları [source-manifest.json](source-manifest.json) içindedir.
