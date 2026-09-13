# Koşum raporu — 2026-09-13 · Kurulu model seçimi ve kaydedilen düzeltmelerin teslim kanıtı

1. Sonuç: Model seçimi, bütün önerilerin görünürlüğü ve açık kayıt akışı L2 düzeyinde gözlendi; tam profil kapısı ve GitHub yayın doğrulaması geçti — birim 777 başarılı / tarayıcı 4 başarılı / atlanan 3; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`; Windows RTX 4060, yerel Ollama ve Docker FastAPI/PostgreSQL/React yığını.

   | Kanıt | Kapsam |
   |---|---|
   | [Son kalite kapısı](quality-report.md) | 1.084 otomatik test: 570 backend birim + 307 PostgreSQL entegrasyonu + 207 arayüz. Sözleşmeler, şema ve chart kontrolleri başarılı. |
   | [Adaptör](adapter-report.md), [backend](backend.md), [arayüz](frontend-report.md) | Kırmızı/yeşil geliştirme, model kimliği, görünür bozuk yanıt, imzalı kanıt, yarış/tekrar/tenant/retention ve yeşil sürüm davranışı. Dar testler tam kapı sayısına tekrar eklenmedi. |
   | [Değerlendirme ölçümü](evaluation-review-report.md) | Ayrı 97 araştırma testi: eşlenemeyen kısmi yanıt özgün metinle puanlanır, görünür durum ve kayda uygunluk sayaçları tarihçe korunarak deftere yazılır. |
   | [Gerçek modeller](model-report.md) | Üç kurulu model × aynı dört yazılmış regresyon = 12 çağrı; 27B iki yararlı ve bir zararlı kelime değişikliği üretti. |
   | [Normal kullanıcı HTTP](live-http-report.md) | 16 gerçek HTTP isteği, bir gerçek model çağrısı ve bir kayıt; özgün kaynak, tekrar güvenliği ve tenant sınırı gözlendi. |
   | [Gerçek tarayıcı](browser-report.md) | TR/EN geniş/dar dört işlevsel varyant; iki model çağrısı, ayrı test kaynağında bir kayıt, yenileme ve özgün görünüm. |
   | [Yayın dosyası incelemesi](publication-audit.md) | Model/ses/veritabanı/sır dosyaları dışarıda; kamu deney bağlantıları ve hash'leri denetlendi. |
   | [Commit ve uzak doğrulama](publication-report.md) | Uygulama commit'i `5d47874e6d3eb6ce60da4bf5f83b1f2ef8d94512` yerel ve GitHub `main` üzerinde aynı. |
   | [Deney defteri](../../../results.md) | Üç yeni politika deneyinin ayrı sürümleri ve [puanlanmamış canlı akış](live-flow-aggregate.json); önceki sonuçlar korunur. |

   Otomatik kapının 777 birim testi ile 307 gerçek PostgreSQL testi ayrı
   sayılmıştır. Dört tarayıcı varyantı aynı test kaynağındaki farklı görünümlerdir.
   Atlanan üç kanıt, iki headless scriptin doğrudan yürütümü ve dar görsel
   yakalamadır. Araştırma testleri ve gerçek model çağrıları bu sayılara katılmaz.

3. Maddeler:

   **KUSUR**
   M1 Ters sırada gelen model önerileri ve bozuk Unicode yanıtının 500 hatası düzeltildi; gerçek PostgreSQL/HTTP regresyonları ve son tam kapı başarılı.
   M2 27B'nin bir gereksiz kelime değişikliği ve 12B'nin hedef satıra eşlenmeyen yanıtları model kıyasında raporlandı; yeşil görünüm doğruluk garantisi değildir.

   **TUZAK**
   M3 Kaydetme açık kullanıcı eylemidir; özgün transcript, ses zamanı ve konuşmacı hafızası korunur. Eşlenemeyen veya kesilmiş yanıt görünür kalır ancak kaydedilemez.
   M4 Güncellenen mevcut kurulum yeni tablo için önce migration gerektirir; [TR çalışma zamanı rehberi](../../TEXT_REVIEW_RUNTIME.md) ve [EN rehber](../../TEXT_REVIEW_RUNTIME_EN.md) sırayı açıklar.

   **GÖZLEM**
   M5 9B, 12B ve 27B kurulu modelleri gerçek adaptörle sınandı; varsayılan 27B değişmedi. Seçim tek başına hesaplama başlatmaz, başka modele otomatik geçiş yapılmaz.
   M6 Görünür öneri, tam model yanıtı, yeşil kayıtlı sürüm, yeniden açma ve özgün metne dönüş canlı uygulamada gözlendi; kullanıcı kabulü L3 iddia edilmedi.
   M7 Kullanıcının istediği uygulama commit ve push işlemi tamamlandı; [yayın raporunda](publication-report.md) uzak commit eşleşmesi kayıtlıdır.

   **AÇIK**
   M8 Güvenlik kapısı eksik `gitleaks` yüzünden çalışmadı; sınırlı yayın incelemesi güvenlik tarayıcılarının yerine geçmez.
   M9 Dar görsel yakalama araç zaman aşımı nedeniyle tamamlanmadı; headless scriptler doğrudan yürütülmedi. Native Apple/Spark ve canlı Kubernetes kanıtı yoktur.
   M10 Dört yazılmış regresyon temsilî Türkçe doğruluk veya 50 kişilik tanıma başarısı ölçümü değildir; bu değişiklik için yeni ASR/mikrofon doğruluk iddiası yoktur.

   **YAN-ETKİ**
   M11 Yerel şemaya eklemeli revizyon tablosu eklendi; iki açıkça adlandırılmış sentetik toplantıda toplam iki sürüm kaydedildi. Kullanıcının mevcut toplantı metinleri değiştirilmedi.
   M12 Model/seçim/kayıt sözleşmeleri, UI, TR/EN rehberler, kalıcı senaryolar, deney defteri ve kanıtlar güncellendi; ham metin/yanıt, kimlik ve tokenlar Git dışı kaldı.
