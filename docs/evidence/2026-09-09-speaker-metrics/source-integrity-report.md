# Koşum raporu — 2026-09-09 · Yeni ölçüler öncesi kaynak bütünlüğü ve eski kanıt anlık görüntüsü

1. Sonuç: Üç gerçek kaynak raporu ve manifest bağı tutarlı bulundu; eski raporlayıcının üç bozuk girdi tuzağı ayrı bellek kopyalarında gösterildi — birim 0 başarılı / tarayıcı 0 başarılı / alan ve bütünlük kontrolü 12432 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`, kabul edilmiş 001 / Decision 9; yalnız yerel JSON, kaynak ve dosya hash okuması. Denetim sayıları, üç rapor/manifestin tam dosya ve canonical hashları ile 98 dosyalık başlangıç envanteri [kaynak bütünlüğü kaydındadır](source-integrity.json).

   | Mevcut koşum | İşlem | Planlı ilk kişi / başarılı kayıt | Bilinen / bilinmeyen sorgu | Başarılı / başarısız iş | Eksik / yinelenen işlem |
   | --- | ---: | ---: | ---: | ---: | ---: |
   | Kalibrasyon | 302 | 50 / 40 | 150 / 100 | 267 / 35 | 0 / 0 |
   | Tarihsel | 302 | 50 / 29 | 150 / 100 | 236 / 66 | 0 / 0 |
   | Yeni grup | 302 | 50 / 40 | 150 / 100 | 277 / 25 | 0 / 0 |

3. Maddeler:

   **KUSUR** — yok

   **TUZAK**

   M1 Eski raporlayıcı, bir eksik sorgunun yerine başka sorgunun kopyası konduğunda toplam satır sayısına bakarak aşamayı tamamlanmış kabul etti. Gerçek üç raporda işlem kimliği, iş kimliği ve aşama/amaç/kayıt anahtarı yinelenmiyor.

   M2 Eski raporlayıcı, değiştirilmiş hazır sayaçları ve olanaksız oranı yeniden doğrulamadan kopyaladı. Gerçek kaynakların mevcut sayaçları bağımsız döngüyle, oranları bu sayımlardan yeniden hesaplanarak doğrulandı.

   M3 Ayrı `return_phase` kopyası ana `operations` listesinden farklı hale getirildiğinde eski raporlayıcı kabul etti. Gerçek üç raporda bu liste ana işlemlerin `stage=return` alt kümesiyle birebir aynı.

   M4 Bu üç örnek yalnız bellekte değiştirilmiş kopyalardı; gerçek sonuç veya eski kanıt dosyası değiştirilmedi. Bunlar yeni ölçü yolunun doğrulama gereksinimleridir, mevcut sonuçların bozuk olduğuna dair kanıt değildir.

   **GÖZLEM**

   M5 Her koşum tek 50 kişilik galeri, 50 ilk kayıt, 150 bilinen sorgu, 100 bilinmeyen sorgu ve ayrı 1 yeni kayıt/1 dönüş içeriyor. Toplam 906 benzersiz iş terminal ve tek denemeli; üç manifestin seçilmiş kişileri birbirinden ayrık.

   M6 Kayıtların manifestteki kişi/rol/kaynak/bölüm/ifade/süre/hash bilgileri, başarılı kayıttan profil-kişi eşlemesi ve gerçek karar/tahmin karşılıkları doğrulandı. Raporların state bağları ve işlemleri de eşleşiyor; başarısız ilk kayıtlar bilinen sorgu paydasından çıkarılmadı.

   M7 Başlangıç görüntüsü eski konuşma kurtarma kanıtındaki 92 dosya ile 3 ham rapor ve 3 manifesti kapsar. Toplam 98 dosyanın canonical envanter SHA256 değeri `23f46a697cac57aa0f9b5eb17295aba7020f373ea93209ee49f44926cf6acbac`.

   M8 JSON kaydında yalnız anonim toplu sayılar, dosya yolları ve hashlar bulunur. İş/konuşmacı/profil/tenant kimlikleri ile profil adlarının çıktıya taşınmadığı ayrıca kontrol edildi.

   **AÇIK**

   M9 Yeni precision, recall, F1 veya bileşik skor bu denetimde hesaplanmadı. Ölçü üretimi sonrası eski 98 dosyanın değişmediği ve yeni çıktıların gizliliği ayrı son denetimle gösterilecek.

   M10 Bu denetim kayıtlı kararlar ve metadata üzerindedir; ses dosyalarını yeniden çözümleme veya yeni model çıkarımı kanıtı değildir. Veri kümelerinin temsil sınırları değişmez.

   **YAN-ETKİ**

   M11 Yalnız bu yeni rapor ve `source-integrity.json` oluşturuldu. Eski kanıtlar, ham raporlar, manifestler, kaynak, hesap, model ve veri tabanı değiştirilmedi; paket kurulmadı, ağ veya çıkarım çağrısı yapılmadı.
