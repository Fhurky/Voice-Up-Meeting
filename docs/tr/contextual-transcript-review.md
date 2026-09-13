# Konuşma kelimelerini bağlamla kontrol etme

Tamamlanan toplantının **Konuşma metni** bölümünde satırın **Bağlama göre
kontrol et** düğmesine basın. Panelde bu kurulumun Ollama dil modelleri
listelenir. Kullanılabilir bir model seçip **Kontrol et** düğmesine basın.
Model seçmek tek başına inceleme başlatmaz; uygulama model indirmez.
Varsayılan model kullanılamıyorsa başka modele kendiliğinden geçilmez.

Uygulama özgün satırı yakın konuşmaların bağlamıyla inceletir. Metne
eşlenebilen değişiklikler **Önerilen metin** içinde yeşil ve altı çizili
görünür. **Orijinal → Öneri** listesi eski ve yeni kelimeleri karşılaştırır.
İsim, sayı veya anlam değişimi gibi ayrıca incelenmesi gereken öneriler de
görünür; bu işaret doğruluk garantisi değildir. Emin olmadığınız kelimeyi
**Bu bölümü dinle** ile özgün sesle karşılaştırın.

Kaynakta kesin yeri bulunamayan veya birbiriyle çakışan öneriler ayrı
listede gösterilir; metne gelişigüzel yerleştirilmez. **Modelin tam yanıtı**
ayrıntıları, model geçerli bir düzenleme üretemediğinde de düz metin olarak
okunabilir. Kesilmiş yanıt açıkça belirtilir. Eşlenemeyen veya bozuk
çıktı kaydedilemez. Model hiç değişiklik önermeyebilir; bu sonuç metnin
hatasız olduğunu kanıtlamaz.

Öneriyi inceledikten sonra **Düzeltilmiş sürümü kaydet** ile ayrı bir sürüm
saklayabilirsiniz. Yalnız bu açık eylem kayıt oluşturur; özgün metin,
konuşmacı, ses ve zamanlar korunur. Kaydedilmiş sürüm sayfa yenilendiğinde
yeşil değişikliklerle görünür. **Orijinal / Düzeltilmiş** düğmeleri iki
görünüm arasında geçiş yapar. Yeni model incelemesi her zaman özgün
konuşma metnini kullanır. Değişen kelimelere kesin ses zamanları atanmaz.

Başka model, satır veya toplantı seçmek eski öneriyi ve kaydetme olanağını
kaldırır. Önerinin süresi dolarsa veya başka bir düzeltme kaydedilmişse yeni
inceleme başlatın. Kayıt sırasında bağlantı kesilirse aynı öneriyle tekrar
kaydetmek mükerrer sürüm oluşturmaz. Paneli kapatmak başlamış sunucu
hesaplamasının durduğunu garanti etmez.

Yeni inceleme ve kayıt için toplantı okuma ve analiz çalıştırma izinlerinin
ikisi gerekir; yalnız okuyucular da önceden kaydedilmiş sürümü görebilir.
Yerel metin kontrolü kurulumda etkin olmalıdır. Uzun satır, hazır olmayan
model veya süre aşımı açıklanır ve özgün metin okunabilir kalır. Model
listesi değiştiyse paneli kapatıp açarak güncel listeyi alın. Kaynak ses
silinse de toplantı metni saklandığı sürece metin incelemesi kullanılabilir.

Davranış kaynağı: [kabul edilmiş gereksinimler](../../specs/speaker-identity/PRDs/013-model-selection-saved-corrections/PRD.md).
