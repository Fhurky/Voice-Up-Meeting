# Koşum raporu — 2026-09-13 · FLEURS sonucu ve deney günlüğünün bağımsız doğrulaması

1. Sonuç: Tam 743 kliplik gerçek deneyin kaynakları ve skorları doğrulandı —
   birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
   **12.736 dosya ve hesap kontrolü başarılı, 0 başarısız**; ayrıca önceki
   18 deneyin korunduğu eski bütün-dosya SHA-256 değeriyle kanıtlandı.
   Kontrol sayısı bağımsız ses, kişi veya birim testi sayısı değildir.
2. Koşulan: Windows yerel Python; yalnız kaynaklar ve kayıtlı deney kanıtları
   okundu. Model veya üretim skor fonksiyonu yeniden çalıştırılmadı. Kanıtlar:
   [FLEURS bağımsız denetimi](fleurs-independent-audit.json) ve
   [günlük koruma denetimi](ledger-preservation-audit.json).

   | İnceleme | Sonuç |
   | --- | --- |
   | Kaynak arşiv ve TSV | Resmî revision, boyutlar ve sabit hashler doğrulandı; tam test bölümü 743 satır. |
   | Ses, metin ve sıra | 743/743 ses hash'i, metin hash'i, özgün TSV referansı, satır sırası, örnek sayısı ve mono 16 kHz float32 biçimi eşleşti. |
   | Dayanıklı sonuç ve provenance | Bütün 743 klip checkpoint'i son raporla aynı; model, manifest, kaynak ve ayar bağları doğrulandı. |
   | Bağımsız edit-distance | ASCII Unicode kaçışlarıyla Türkçe sözcükleme ve tam uzaklık matrisi/geriye izleme; bütün kliplerin hata türleri, kelime sayıları ve oranları eşleşti. |
   | Toplam ve dağılım | Bütün toplamlara ek olarak medyan/p90/p95, sıfır/yüksek hata sayıları ve 2.000 tekrar örnekleme aralığı bağımsız hesapla eşleşti. |
   | Genel çıktı gizliliği | Ham referans/çıktı metni, klip kimliği, özel yol ve gizli bilgi alanları incelenen genel artefaktlarda yok. |
   | Son günlük | 24 benzersiz deney ve 24 sürüm: 18 tamamlanmış, 4 tarihsel skorsuz, 2 adet 0/2.433 kapsamlı eksik kurulum denemesi. |
   | Önceki günlüğün korunması | İlk 18 sürüme kadar olan bölümden yalnız yeni 407 baytlık açıklama bellekte çıkarıldı; 48.155 baytlık özgün günlük aynı eski SHA-256 değerini verdi. |

   Doğrulanan sonuç: **840 hata / 12.914 referans kelime = %6,504569 WER**.
   Hatalar 676 değiştirme, 56 silme ve 108 eklemedir. Toplam ses 9.380,22
   saniye; 321 klip sıfır hatalı, klip medyan WER'i %4,761905'tir. Koşullu
   klip tekrar örnekleme aralığı %5,901085–%7,140147 olarak doğrulandı.

3. Maddeler:

   **KUSUR** — yok

   **TUZAK**

   M1 Resmî 743 test kaydı yalnız 329 metin kimliğini içerir ve tamamı kaynakta `MALE` etiketlidir; 743 bağımsız metin veya kişi ve cinsiyetler arası temsil iddiası kurulmaz.

   M2 Koşullu tekrar örnekleme aralığı eldeki kliplerin dağılımını özetler; metin, kişi, oturum veya bütün Türkçe toplantı nüfusu bağımsızlığı sağlamaz.

   M3 Günlüğün yeni açıklama paragrafı bütün dosyanın hash'ini değiştirir; yalnız bu paragrafı bellekte kaldıran karşılaştırma eski 18 deneyin metin ve makine bloklarıyla aynen korunduğunu kanıtladı. Günlüğe hiçbir yazma yapılmadı.

   **GÖZLEM**

   M4 Özel sonuç SHA-256 `b8fdff098788ca4a1daaa247b92500ca226c6b40e2c249561702dac4da3e28b5`; deney `tr-fleurs-test-20260913`; kayıt mührü `7ee39128474b879946f0860dba50f43e68637e3ab4bf0c24ddd2e04df4cc0fd6` doğrulandı.

   M5 Önceki 18 deneyin yeniden elde edilen günlük hash'i `9e0f0e76039e68e04eb0443fa3fba3d4f28299e0a3743c85db654b54e7191f9a`; gözlenen son günlük hash'i `11bba77d094b28c657abd18b6ea1613a48755bd153dcc499997eebe46357d6d5`.

   **AÇIK**

   M6 FLEURS okuma konuşmasıdır; bu ASR sonucu toplantı içi konuşmacı ayırma, kalıcı kişi hafızası veya 50 kişi başarısının ölçümü değildir. Kaynak referansları ayrıca yerel insan hakemince incelenmedi.

   **YAN-ETKİ**

   M7 Yalnız FLEURS denetim JSON'u, günlük koruma JSON'u ve bu rapor oluşturuldu; model, kaynak, yapılandırma, kod, günlük ve mevcut deney çıktıları değiştirilmedi.
