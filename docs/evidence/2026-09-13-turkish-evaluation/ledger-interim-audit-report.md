# Koşum raporu — 2026-09-13 · İlk 15 deneyin bağımsız günlük denetimi

1. Sonuç: İlk 15 deneyin 266 dosya/hash/sayım kontrolü geçti — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Yerel Windows/Python 3.12, yalnız okuma; `results.md` tek bayt görüntüsü bağımsız JSON/SHA-256 ve aritmetik koduyla denetlendi; üretim günlük hesaplayıcısı çağrılmadı. [Sayılar ve kaynak hash](ledger-interim-audit.json).
3. Maddeler:

   **KUSUR** — yok

   **TUZAK**

   M1 Aritmetik doğruluk özel ses/model gözleminin doğruluğu değildir; macro F1 geçmiş bağımsız denetimli toplu kaynaklardan korunur, kişi düzeyinde özel veri yeniden açılmadı.

   **GÖZLEM**

   M2 15 ayrı kimlikte 15 sürüm, yinelenmeyen anlamsal hash, varsa tam kayıt mührü, 13 tarihsel kaynak dosyasının gerçek hashleri, kimlik precision/recall/F1/VoiceUp ve metin hata sayımları tutarlıydı.
   M3 ASR taban çizgisi ve reddedilen iki aday birlikte mevcut; başarısız/ölçülmeyen durumlar skor taşımıyor, kelime klipleri kişi sayısına çevrilmiyor, özel metin/kişi/tenant/token alanları bulunmuyor.

   **AÇIK**

   M4 Bu ara denetim, son Türkçe ayrılmış test ve toplantı zinciri sonuçlarından önceki günlük görüntüsüdür; nihai bütün-günlük denetimi ayrıca çalıştırılacaktır.

   **YAN-ETKİ**

   M5 Yalnız bu toplu denetim artefaktları yazıldı; `results.md`, kaynak kanıtlar, uygulama verisi ve model sonuçları değiştirilmedi.
