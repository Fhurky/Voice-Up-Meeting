# Koşum raporu — 2026-09-13 · Bütün deney günlüğünün bağımsız son denetimi

1. Sonuç: 18 deney ve altı güncel toplu model artefaktının 676 kontrolü geçti; beş gerçek CLI yeniden yayımı geçici günlüklerde eski kayıtlarla uyumlu çıktı — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Yerel Windows/Python 3.12, sabit `kt-vibecoding-python-web-v2`; `.venv/Scripts/python.exe outputs/2026-09-13-turkish-evaluation/ledger-final-audit.py` → çıkış 0. Üretim metrik hesaplayıcısından ayrı JSON/SHA-256/sayım aritmetiği, altı özel kayıt çiftinde yalnız toplu kelime dizisi eşitliği ve gerçek `record-experiment.py` işlemleri geçici dizinlerde çalıştırıldı. [676 kontrolün dağılımı ve tam kaynak hashleri](ledger-final-audit.json).

   | Denetlenen yüzey | Sonuç |
   |---|---|
   | Kök günlük | 18 ayrı kimlikte 18 sürüm: 13 tarihsel, 3 yeni Türkçe klip deneyi, 2 zayıf referanslı Türkçe toplantı zinciri; yinelenen sürüm yok. |
   | Tarihsel kanıt | Üç ECAPA özeti, ASR taban çizgisi ve reddedilen iki aday, 50 kişilik A/B/C metin ve hafıza gözlemleri, referanssız Türkçe kaynak korunuyor; 13 bağlı kaynak dosyasının gerçek hashleri eşleşiyor. |
   | Altı güncel toplu dosya | `asr-dev-tr.json`, `asr-dev-auto.json`, `asr-heldout-tr.json`, `meeting-baseline.json`, `meeting-count2.json`, `meeting-comparison.json`; hash, özel alan ve uygun aritmetik denetimleri geçti. |
   | Güncel CLI uyumu | Üç ASR ve iki toplantı dosyası mevcut CLI ile geçici günlüklere başarıyla yazıldı; eski temel kaydın birikimli alanı yalnız bellekte eşlenince bütün metrikler birebir uyuştu. |
   | Türkçe klip ayrımı | İki geliştirme koşusunda aynı 40 tekil kaynak hashı; ayrılmış testte 40 farklı hash; geliştirme/test kesişimi sıfır. Üç özel koşumdaki bütün kelime ve hata sayıları genel özetlere eşleşti. |
   | Toplantı karşılaştırması | Aynı altı kaynak, toplam 2.341 referans kelime, 734→651 kişi eşlemeli kelime hatası; altı normalize çıktı kelime dizisi birebir aynı. İyileşme konuşmacı gruplamasındadır; yeni ASR kelimesi kazanımı değildir. |
   | Kayıt kapsamı | İlk görünüm 4/6→5/6, koşu sonu birikimli kayıt her iki denemede 6/6; özel durum belgelerinden yalnız sayımlar alınarak doğrulandı. |

3. Maddeler:

   **KUSUR**

   M1 Denetim adaptörünün ilk çağrısında test deneyinin kimliği yanlış yazıldı; gerçek kimlikle düzeltildi. Sonraki ilk tam geçişte 652 kontrolden biri, ortak bütün-seçim manifestinin geliştirme/test için farklı olması gerektiği yönündeki yanlış denetim varsayımına takıldı; uygulama kaynağı doğrulanıp asıl klip hash kümeleri karşılaştırıldıktan sonra 676/676 geçti. Günlük/model artefaktı değiştirilmedi.

   **TUZAK**

   M2 `input_sha256` iki ayrımı içeren ortak 80-klip manifestidir; ayrım, metadata rolü ve gerçekten çalıştırılan klip hashleriyle doğrulanır. Aynı manifest özeti tek başına veri sızıntısı veya iki grubun aynı klipler olduğu anlamına gelmez; farklı kişi/oturum bağımsızlığı da kanıtlanmaz.
   M3 Eski v1 tam mühür bulunmayan kayıtlar kendi anlamsal hashleriyle okunur. Eski Real-TurnTurk `enrollment_coverage` alanı birikimlidir; kök açıklama ilk görünüm farkını açıklar, yeni sürüm iki alanı ayırır. Asıl makine blokları yeniden yazılmadı.

   **GÖZLEM**

   M4 Kimlik precision/recall/micro F1, bilinmeyen F1, VoiceUp Score, kelime değişim/silme/ekleme ve paydalar tutarlıydı. Eski macro F1, önceden bağımsız denetimli kaynağa bağlanır; özel tarihsel kişi verisinden yeni bir hesap iddiası yapılmaz.
   M5 Real-TurnTurk iki kişi girdisi görünür ve boolean olarak kaydedilmiş; otomatik etkinlik, doğrulanmamış metin/zaman ve kalibrasyon sınırı açık. MediaSpeech klip WER'i kalıcı kişi veya 50 katılımcı başarısına çevrilmemiştir.
   M6 Kaynak özetlerinde ve bütün makine bloklarında token/parola/tenant/kişi kimliği, ham metin/ses/embedding alanı yoktu; altı özel kelime dizisi karşılaştırmasında metin veya kimlik yayımlanmadı.

   **AÇIK**

   M7 Bu doğrulama otomatik kaynak etiketlerini insan referansına dönüştürmez; gerçek doğal Türkçe toplantı/50 kişi kabulü değildir. Model çıkarımı, birim veya tarayıcı testi bu denetimde yeniden çalıştırılmadı; ana teslimin koşumları ayrıdır.

   **YAN-ETKİ**

   M8 Yalnız bu toplu denetim belgeleri, ignore edilen yöntem/JSON çıktısı ve otomatik temizlenen geçici CLI dosyaları oluşturuldu. Kök günlük ve altı genel model artefaktının koşum başı/sonu baytları aynı kaldı; uygulama kayıtları ve model kaynakları değiştirilmedi.
