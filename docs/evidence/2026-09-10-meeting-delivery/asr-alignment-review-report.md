# Koşum raporu — 2026-09-11 · ASR filtresi karşılaştırması ve konuşmacı zaman hizalaması incelemesi

1. Sonuç: Yerleşik ASR VAD filtresi uzun sözcük zamanlarını düzeltmedi; yeni konuşmacı hizalaması değiştirilmemiş C checkpoint'i üzerinde mevcut referans eşleme koşulunu geçti — birim 0 başarılı / gerçek GPU çıkarımı 8 başarılı / kaynak tekrarı 1 başarılı / sentetik sınır gözlemi 4 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`; aynı Python 3.13/CUDA imajında dört sabit A/B/D/C kaydının her biri için `vad_filter=False/True`, ardından yalnız CPU üzerinde C checkpoint tekrarı ve bağımsız sentetik sınır incelemesi.

   | Kanıt / karşılaştırma | Sonuç |
   | --- | --- |
   | Model imajı | `sha256:09dbebcbdaff48b701260d8e837344aca6c5bb13cde762cf14781dc37bd08110` |
   | ASR kimliği | `Systran/faster-whisper-large-v3`, `edaa852ec7e145841d8ffdb056a99866b5f0a478`, `int8_float16` |
   | Kaynak protokol SHA-256 | `6f6e9a731ad7efec7c09e18fe507077504dcdb1c545c59d5c96287a68dfe05dc` |
   | Sabit diğer ASR ayarları | 5 beam, sözcük zamanları açık, önceki metne koşullanma kapalı, dil otomatik, 4 CPU iş parçacığı, 1 worker, yalnız yerel dosyalar |
   | İki modda A/B/D/C sözcük sayısı | 499 / 262 / 224 / 347; eklenen, silinen veya değiştirilen sözcük yok |
   | VAD'ın çıkardığı süre | Dört kaydın tamamında 0 saniye |
   | A/B/D/C en uzun sözcük süresi | Her iki modda 1,70 / 1,54 / 4,74 / 12,66 saniye |
   | Son incelenen timeline SHA-256 | `c02e5c9e4bdd20633735367fe5aeb06eb277938bc5b2930aa38caf859a5e0f09` |
   | C'de en düşük referans baskın payı | Eski gerçek çıktı %88,343; yeni kaynak tekrarı %97,771 |
   | C'de mevcut en az %90 eşleme koşulu | Eski çıktı başarısız; yeni tekrar altı kişinin tamamında başarılı |
   | C'de satır / belirsiz süre | 37 → 40 satır; 0 → 16,48 saniye kişiye atanmayan aralık; sözcük dizisi korunmuş |

3. Maddeler:
   **KUSUR**
   M1 AÇIK: Bir sözcüğün farklı konuşmacıların kaynak sürelerine taşan aşırı uzun zaman aralığı yerleşik VAD ile düzelmedi; bu ayar üretime alınmadı. Sorun metindeki sözcüklerin kime atanacağına ilişkin ayrı belirsizlik kuralıyla ele alındı.
   M2 DÜZELTİLDİ: Bağımsız sentetik inceleme, düzenli konuşmada %91 baskın kişi varken kısa exclusive gözlemin başka kişiyi kesin seçtirebildiğini gösterdi; son kaynak örtüşmeyen konuşmada düzenli puanları kullanıyor, gerçek örtüşmenin politikasını koruyor.
   **TUZAK**
   M3 Yerleşik VAD varsayılan 0,5 eşik, 2000 ms sessizlik ve 400 ms kenar payıyla çalıştı; başka ayar taranmadı. Sonuçlar yalnız bu dört kayda aittir.
   M4 Yeni %80 baskınlık sınırında tam %80 destek kimliği korur, %79,9 destek kimlikten çekinir; yinelenen aynı-kişi aralıkları puanı iki kez artırmaz. Aradaki rakip konuşma aynı kişinin satırlarını birleştiremez.
   M5 Referans eşleme ölçüsü yalnız atanmış aralıkların baskın payını değerlendirir; açık belirsizlik bu payı yükseltebilir. Bu sonuç gerçek sözcük recall, DER, WER veya biyometrik F1 değildir.
   **GÖZLEM**
   M6 `faster-whisper==1.2.1` kabul edilmiş wheel SHA-256 değeri `79a66ad50688c0b794dd501dc340a736992a6342f7f95e5811be60b5224a26a7`; içindeki 1.245.151 bayt VAD varlığı `4cbf549b8326f60f80f2536d9eefeb450a9abe83365a098031c89719f1be17d2` hash'iyle gerçek imaj ve RECORD kaydında aynı doğrulandı.
   M7 Sekiz gerçek GPU koşumu ağsız kapsayıcıda sıfır ağ girişimiyle tamamlandı. İki modun zaman farkı yalnız en fazla `2,85e-14` saniyelik kayan nokta yuvarlamasıdır; sözcük olasılıkları aynı kaldı.
   M8 C tekrarında yerel etiketler yalnız checkpoint'teki akustik konuşma zamanlarıyla %99,9 üzerinde tek kişiye eşlendi; referans adları, sayı ipucu veya ses vektörü bu eşlemeye girmedi. Oracle'ın %90, 0,5 saniye ve %10 koşulları değişmedi.
   M9 Ham araştırma çıktıları ignore kapsamındaki `outputs/2026-09-10-meeting-delivery/asr-vad-comparison/` ve `timeline-review/` altında korundu; bu kalıcı rapor konuşma metni, sözcük içeriği, ses vektörü veya erişim sırrı içermez.
   **AÇIK**
   M10 Kaynak kesitlerine elle hizalanmış sözcük referansı olmadığından gerçek WER/recall hesaplanmadı. C kaynak tekrarı yeni çalışan uygulama koşumu değildir; sonraki canlı A/B/D/C akışı ayrı teslim kanıtıdır.
   **YAN-ETKİ**
   M11 Araştırma üretim ASR ayarını, model ağırlıklarını veya kabul edilmiş sürümleri değiştirmedi; yalnız kaynak kopyaları/çıktılar ve bu sadeleştirilmiş rapor üretildi. İncelemede bulunan hizalama kusurunun üretim düzeltmesi ana değişiklikte kendi testleriyle yer alır.
