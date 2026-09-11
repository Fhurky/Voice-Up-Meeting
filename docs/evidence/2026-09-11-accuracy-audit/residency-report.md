# Koşum raporu — 2026-09-11 · İstek boyunca GPU modelini tutma yaşam döngüsü

1. Sonuç: İstek kapsamlı model yaşam döngüsü 2.979 gerçek ses penceresinde birebir aynı vektörleri üretti; mevcut karışık profil kusuru ayrıca doğrulandı — birim 205 başarılı / eşli GPU 56 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`, çevrimdışı Python 3.13.14; düzeltilmiş RED 9 başarısız/2 başarılı → GREEN 11 başarılı, tüm çıkarım paketi 205 başarılı. Ayrı RTX 4060 koşumu: eski 19 + yeni 37 sabit kayıt, 56 eşli kontrol ve aynı pencerelerde ECAPA tanısı; değerlendirme 264,26 saniye, toplam 288,36 saniye. Sayısal sonuçlar ve hashler: [residency-results.json](residency-results.json); komut/XML/günlükler: `outputs/2026-09-11-accuracy-audit/residency/`.
3. Maddeler:
   **KUSUR**
   M1 Her kısa pencere için yinelenen GPU/CPU taşıması, istek ömürlü ve ilk gerçek çıkarıma kadar yüklemeyen encoder ile azaltıldı; tekli örnek sırası ve sayısal dönüşüm korunur (`meeting_models.py`, `test_meeting_residency.py`).
   M2 Başarı, model yükleme/çıkarım/çıktı biçimi/CPU taşıma ve istek gövdesi hatalarında hassasiyet ayarları ile kilidin geri bırakılması; iç içe, eşzamanlı ve süresi bitmiş encoder kullanımının reddi sınandı.
   M3 Mevcut karışık profilin 94 penceresi iki güçlü kümeye ayrılır; WeSpeaker merkez benzerliği 0,625568 olduğu için 0,55 ayrım koşulunu geçemez. Her kümede 12 bağımsız pencere ve yaklaşık 24 saniye konuşma vardır; eksik destek neden değildir. Kusur hızlandırmada değiştirilmedi.
   **TUZAK**
   M4 İlk RED koşumunda üç HTTP testi yanlışlıkla pilotun ikili içerik başlığını taşıdı; JSON başlığı düzeltildi, ilk çıktı silinmedi. İlk tam koşumda yeni protokolü taşımayan iki sağlayıcı fikstürü ortak session fikstürüne geçirildi; kalite beklentileri değişmedi.
   M5 İsteğe bağlı decoder, kernel önbelleği ve mevcut Starlette/AnyIO kullanım uyarıları korundu. Ses doğrudan PCM üzerinden işlendi; zamanlar sabit eski→yeni sırasındadır ve tüm 50 kişilik işin süresi olarak yorumlanmaz.
   **GÖZLEM**
   M6 Gerçek HTTP uygulamasının otomatik testi aynı doğrulama gövdesinde tam yanıt eşitliğini, tek taşıma çiftini, gizli hata ayrıntılarının çıkarılmasını ve sonraki isteğin çalışmasını gösterdi. Boş/hatalı ve meşgul istekler modeli taşımadı.
   M7 Gerçek GPU kontrolünde tüm 56 karar, tüm hassasiyet ayarları ve 2.979 vektör birebir aynı kaldı; en büyük fark 0. Kısa pencere kontrolleri toplam 155,64 → 24,98 saniye oldu; 6,23 kat hızlandı.
   M8 Gerçek kaynak bağlamlarından yeniden kurulan tek hafıza isteği 15,40 → 3,96 saniyede tamamlandı; iki vektör ve saklanan PCM özeti dahil tam JSON yanıtı birebir eşitti. GPU ayrılmış bellek tepesi 701,11 → 733,08 MiB oldu; yaklaşık 32 MiB ek kullanım vardır.
   M9 Ayrı ECAPA tanısında aynı karışık örneğin merkez benzerliği 0,541786; iki destekli grup ayrılır. 53 temiz kontrolde her iki modelde yanlış veto 0; temiz merkezlerin en düşüğü WeSpeaker 0,696415 ve ECAPA 0,661899. Üç karışık kontrolün WeSpeaker 2'sini, tanısal ECAPA 3'ünü ayırdı; ECAPA için yeni üretim eşiği kabul edilmedi.
   M10 Sabit Starlette 1.6.0 `run_in_threadpool`, AnyIO 4.15.1 varsayılan `abandon_on_cancel=False` yolunu kullanır; mevcut HTTP kilidi iş parçacığının tamamlanmasını bekleyen sınırını korur. Bu kaynak incelemesidir, ayrı istemci bağlantı kopma deneyi değildir.
   **AÇIK**
   M11 Bu eşli ölçüm sırasında ana uygulama eski imajda kaldı; sonrasında yeni imajın 10 kaynak dosyası ve gerçek özel HTTP çağrısı [ayrı L2 kanıtıyla](deployed-critical-memory-results.json) doğrulandı. Taze 50 kişilik sonlandırma bu ölçümün dışındadır. 53 temiz kontrolün kaynak saflığı en az %99'dur; artık gözlenmiş bu küme kör değerlendirme sayılamaz.
   **YAN-ETKİ**
   M12 Yalnız yerel çıkarım adaptörü, iç protokol/runtime bağlantısı, bunların testleri ve kanıt dosyaları değişti. Eski 48 kaynak kaydı aynı sabit yeniden kurma yordamıyla ayrı WAV dosyalarına aktarıldı; model, bağımlılık, kalite eşiği, ASR, veritabanı ve HTTP veri sözleşmesi değişmedi. Tam proje kalite kapısı kök ajan tarafından yürütülür.
