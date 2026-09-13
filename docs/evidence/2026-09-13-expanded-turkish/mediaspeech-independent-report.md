# Koşum raporu — 2026-09-13 · MediaSpeech sonucunun bağımsız kaynak ve metrik doğrulaması

1. Sonuç: Tam 2.433 kliplik gerçek deneyin kaynak bağı ve skorları bağımsız
   hesapla doğrulandı — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0;
   karar bekleyen: yok. Dosya ve hesap denetiminde **39.004 kontrol başarılı,
   0 başarısız**; bunlar 39.004 bağımsız ses örneği veya birim testi değildir.
2. Koşulan: Windows yerel Python; model çalıştırılmadan kayıtlı özel sonuç,
   kaynak ses/metin, dayanıklı klip dosyaları, toplu sonuç, dağılım raporu ve
   `results.md` deney girdisi okundu. Son kanıt
   [bağımsız doğrulama JSON'udur](mediaspeech-independent-audit-final.json).

   | İnceleme | Sonuç |
   | --- | --- |
   | Kesin manifest, eski 80 klip ve arşiv | Hashler değişmedi; 2.433 ses eski 80 kimlik ve ses hash'iyle örtüşmüyor. |
   | Bütün ses/metin dosyaları ve dayanıklı sonuçlar | 2.433/2.433 dosyanın ses/metin hash'i, gerçek ses süresi, referans eşliği ve klip checkpoint'i doğrulandı. |
   | İlk bağımsız kontrol | 38.995 kontrolün 2.533'ü hata verdi; neden model değil, denetçi kodunun PowerShell üzerinden taşınırken Türkçe karakter kaybetmesiydi. |
   | Karakter taşıma tanısı | Düz yazılmış `I/ı/İ/i` kodu `[73,63,63,105]`; ASCII Unicode kaçışları `[73,305,304,105]` üretti. Gerçek UTF-8 ses/metin/sonuç dosyaları değişmedi. |
   | Düzeltilmiş bağımsız hesap | Önceki 21.931 başarılı kaynak/sınır kontrolü, hash'i değişmeyen kanıta bağlı korundu; başarısız kontrol gruplarının tamamı ve ek denetçi kontrolleri yeniden hesaplandı: 17.073 başarılı. |
   | Kelime hata hesabı | Üretim skor fonksiyonu çağrılmadan bağımsız Unicode sözcükleme, tam uzaklık matrisi ve geriye izleme; bütün 2.433 klipte S/D/I, kelime sayısı ve oranlar eşleşti. |
   | Dağılım ve belirsizlik | Medyan/p90/p95, sıfır hata, yüksek hata ve 2.000 sabit tohumlu klip tekrar örneklemesi bağımsız olarak eşleşti. |
   | Günlük ve gizlilik | Tek deney girdisi; kaynak/ayar/özet/kayıt mühürleri doğru; incelenen genel çıktılarda ham metin, klip kimliği veya özel dosya yolu bulunmadı. |

   Doğrulanan sonuç: **10.137 hata / 71.767 referans kelime = %14,124876 WER**.
   Hatalar 5.303 değiştirme, 3.224 silme ve 1.610 eklemedir. Toplam ses
   34.852,1 saniye; sıfır hatalı klip 148, klip medyan WER'i %12,5'tir.
   Koşullu klip tekrar örnekleme aralığı %13,701550–%14,557571 olarak doğrulandı.

3. Maddeler:

   **KUSUR**

   M1 İlk denetçi kodundaki Türkçe harfler PowerShell native stdin kodlamasında soru işaretine dönüştü; yalnız denetçi ASCII Unicode kaçışlarıyla düzeltildi. [İlk başarısız denetim](mediaspeech-independent-audit.json) korunur; ürün/model kusuru veya alternatif doğruluk skoru değildir.

   **TUZAK**

   M2 Klip düzeyindeki S/D/I eşit uzaklıklı hizalarda değişebilir; bağımsız geriye izleme yayımlanan köşegen, silme, ekleme önceliğini izledi ve aynı toplamları verdi.

   M3 Son rapor 21.931 değişmemiş kaynak kontrolü ile 17.073 yeniden hesaplanan kontrolü birleştirir; aynı sesler yeniden modelden geçirilmedi veya yeni bağımsız örnek sayılmadı.

   **GÖZLEM**

   M4 Özel sonuç SHA-256 `3deda87a9a14d0e6c5744c8c26fb0309e091f910eba21300078bdaea43b2776f`; günlük girdisi `tr-mediaspeech-expanded-optimized-20260913` ve kayıt mührü `fc39015f7f9265d85244c2bdcef331be2107cee72721bc5fbae1fed0ecc11263` doğrulandı.

   M5 Değerlendirici kaynak hash'i `c6df5fa1c158db423df324f50900bd495a9ddef6ab54b7dbd606d259e5821310`, model sürümü ve manifest/ayar bağları kayıtlı gerçek deneyle eşleşti.

   **AÇIK**

   M6 Bu kaynak haber konuşmasıdır; kalıcı kişi/oturum bağımsızlığı, toplantı ayırma veya 50 kişi başarısı ölçülmez. Kaynağın insan transkripsiyonu ayrıca yerel insan hakemli doğrulamadan geçirilmedi.

   M7 Tekrar örnekleme aralığı yalnız eldeki kliplerin örneklenmesine koşulludur; bağımsız kişi, oturum veya tüm Türkçe toplantı nüfusu için güven aralığı değildir.

   **YAN-ETKİ**

   M8 Yalnız üç yeni anonim kanıt dosyası yazıldı: ilk/son denetim JSON'u ve bu rapor. Kaynaklar, model, kod, günlük, özel sonuç ve dağılım kanıtı değiştirilmedi.
