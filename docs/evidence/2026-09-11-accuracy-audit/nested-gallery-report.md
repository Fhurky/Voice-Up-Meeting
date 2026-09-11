# Koşum raporu — 2026-09-11 · Değişmez 190 kayıtta kontrollü galeri büyüklüğü ve iki modelin eşleştirmesi

1. Sonuç: 190/190 kayıt gerçek özel HTTP model yolunda tamamlandı; aynı 140 sorgu dört galeride puanlandı — gerçek çıkarım 190 tamamlanan / kontrollü ilişkili karar 560 / hazırlık birim 4 başarılı / sınır 2 başarılı / çatışma 2 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`, mevcut Python 3.13 Linux backend ve RTX 4060 çıkarımı; `nested-gallery190-v6/run.py extract --gpu-released-by-root`, ardından `run.py score`. Kaynaklar bir kez işlendi; gerçek `HttpMeetingAdapter` ve `HttpMeetingMemoryAdapter`, üretimin konuşmacı eşlemesi/bağlam kalitesi ve saf karar birleştiricisi kullanıldı. Ayrıntılı anonim sayımlar, her gruptaki paydalar, kaynak/model hashleri ve süreler: [nested-gallery-results.json](nested-gallery-results.json). Her tablodaki tanıma ve hata sayısı 140 klip paydasından gelir; planlı pozitifler sırasıyla 10/20/40/100'dür.

   | Planlanan / gerçek galeri | Model | Doğru tanıma | Yanlış kimlik | Yanlış kabul | Precision | Planlı recall | F1 |
   |---|---|---:|---:|---:|---:|---:|---:|
   | 5 / 5 | ecapa192 | 10 | 0 | 0 | %100.00 | %100.00 | %100.00 |
   | 5 / 5 | community256 | 10 | 0 | 0 | %100.00 | %100.00 | %100.00 |
   | 5 / 5 | fused | 10 | 0 | 0 | %100.00 | %100.00 | %100.00 |
   | 10 / 10 | ecapa192 | 20 | 0 | 0 | %100.00 | %100.00 | %100.00 |
   | 10 / 10 | community256 | 20 | 0 | 0 | %100.00 | %100.00 | %100.00 |
   | 10 / 10 | fused | 20 | 0 | 0 | %100.00 | %100.00 | %100.00 |
   | 20 / 20 | ecapa192 | 40 | 0 | 0 | %100.00 | %100.00 | %100.00 |
   | 20 / 20 | community256 | 40 | 0 | 0 | %100.00 | %100.00 | %100.00 |
   | 20 / 20 | fused | 40 | 0 | 0 | %100.00 | %100.00 | %100.00 |
   | 50 / 49 | ecapa192 | 95 | 0 | 0 | %100.00 | %95.00 | %97.44 |
   | 50 / 49 | community256 | 96 | 0 | 0 | %100.00 | %96.00 | %97.96 |
   | 50 / 49 | fused | 95 | 0 | 0 | %100.00 | %95.00 | %97.44 |

3. Maddeler:
   **KUSUR**
   M1 Toplam 1/50 planlı kayıt, tek global satır ve mevcut kalite şartlarıyla kontrollü galeriye kabul edilmedi. Birleşik karardaki beş kaçırmanın ikisi bu kayıt eksikliğinden, biri kısmen kullanılabilir satırlardan, biri iki kullanılabilir satırın anlaşmamasından, biri tek satırdaki yetersiz eşleşme güveninden gelir; hiçbiri kolay bilinmeyen sonuca dönüştürülmez.
   M2 İlk hazırlıklar boş grup sayacı, başarısız kayıt paydası ve 192 vektörün float32 öncesi üretim normalizasyonu farklarını buldu. Ayrı sürümler ve RED/GREEN kanıtları korundu; son puanlayıcı 192 için `checked_vector`, 256 için değişmemiş ham kalite yolunu kullanır.
   M3 İki başlatma girişimi modelden önce Windows yol dönüşümü ve uzun komut satırının kesilmesi nedeniyle durdu. Ayrı uzunluk çerçeveli stdin taşıması doğrulandı; bu hatalar kötü ses örneği veya model tekrarı sayılmadı, eski kanıtlar silinmedi.
   **TUZAK**
   M4 Galeri ekleme gözetimli kontrollü kabul işlemidir; sıralı yeni kişi keşfi ölçülmez. Birleştirici kararı son kalıcılık çatışma denetimi değildir; aynı kazananlı yerel ayrılık/örtüşme çiftleri ayrıca raporlanır ve bu tabloda karar değiştirmez.
   M5 Tanınma bütün global satırların kullanılabilir olup aynı profile eşleşmesini gerektirir. Yetersiz parçalar gizlenmez; kısmi kullanılabilirlik belirsiz, sıfır kullanılabilir satır niteliksizdir. Kayıt için tek global satır, 20 saniyeden kesin fazla özgün konuşma ve en az üç bağımsız bağlam gerekir.
   M6 Dört aşama aynı 140 sorguyu kullanır; 560 bağımsız örnek değildir ve aynı kişinin iki sorgusu da ilişkili olabilir. Planlı bilinen/yabancı sayıları 10/130, 20/120, 40/100 ve 100/40 değişir; precision/F1 eğrisi yalnız galeri büyüklüğünün etkisini göstermez. Gruplar ve planlı/gerçek paydalar ayrı verilir.
   **GÖZLEM**
   M7 Toplam 194 yerel etiket, üretimin değişmemiş uzlaştırmasıyla 193 global satıra dönüştü; 3 klipte birden fazla global satır kaldı. Her aşamada 140 sorgu/142 satır; aynı kazananlı ayrılık/örtüşme tanısı 0, 1e-6 karar sınırı yakınlığı 0; bütün satırlar JSON'da korunur.
   M8 Plan50 birleşik kararında hiç kaydedilmemiş 40 sorgunun 30'u bilinmeyen, 10'u belirsizdir; yabancı kabul 0'dır. Klip toplamı 2407.03 saniye: parça çağrıları 1232.45, kalite çağrıları 610.82; model tekrarı ve sorgu/veritabanı yazımı 0'dır.
   M9 Corpus kimliği, kişi sayısı, dil ve referans metin modele gönderilmedi. 190 özgün kaynak, `sha256:d14a4e65159af176…` imaj kimliği, 22 backend dosyası ve iki ayrı model nüfusu değişmez denetlendi; eşik ayarı yapılmadı.
   **AÇIK**
   M10 Gerçek model HTTP çağrıları gözlendi; uzlaştırmanın depolama adaptörü imzası kısıtlanmış bellek nesnesidir. Bu sonuç tek-klip eşleştirmesi içindir; tam toplantı, PostgreSQL/son profil ataması veya kullanıcı kabulü kanıtı değildir.
   M11 Bu, önceden sabitlenmiş kişi/bölüm ayrımlı kontrollü galeri ölçümüdür: önceki corpus kişilerinden ayrı seçilmiş olsa da türetilmiş A/B/C artık görüldü ve A düzeltmeleri etkiledi; yeni kör test değildir. Genel Türkçe/mikrofon/gün başarısı veya PostgreSQL SIMD ile bit eşitliği iddiası yoktur; 1e-6 sınır yakınlığı ayrıca verilir.
   **YAN-ETKİ**
   M12 Ham ses, transkript, vektör ve ayrıntılı kaynaklar yalnız yok sayılan `outputs/` dizinindedir. Üretim kodu, model, bağımlılık, ayar, ana veritabanı veya profil değiştirilmedi; bu iki kalıcı kanıt dosyası yalnız anonim toplamları içerir.
