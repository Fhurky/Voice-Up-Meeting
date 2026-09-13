# Koşum raporu — 2026-09-13 · Yayına aday dosyaların sınırlı gizlilik ve kanıt bağlantısı incelemesi

1. Sonuç: İncelenen adaylarda gizli veri veya yayın engeli bulunmadı; yerel çıktı bağlantıları açıklığa kavuşturuldu, commit ve push henüz doğrulanmadı — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`; Windows PowerShell ve mevcut araştırma Python ortamında salt okunur Git envanteri, dosya içeriği ve bağlantı incelemesi; yeni test, model, ağ veya Git yazma işlemi çalıştırılmadı.

   | İnceleme | Gözlenen sonuç |
   |---|---|
   | `git diff --name-only` ve `git ls-files --others --exclude-standard` birleşimi | Son belge düzeltmesinden sonra, 18:12:42 UTC anında 314 dosya ve 2.590.993 bayt; en büyük dosya `specs/openapi/voiceup-api.yaml`, 137.820 bayt. Bu rapor henüz envanterde değildi. |
   | Aday içeriklerinin özeti | Sıralı yol, sıfır ayırıcı ve dosya SHA-256 satırlarının birleşik SHA-256 değeri: `ec55bb829cbd887f0364098176b0e391ff095ba6d1ceaaec2708fc266cf98d85`. |
   | Yerel sır karşılaştırması, 18:10:45 UTC | İki yerel `.env` dosyasındaki beş dolu sır/bağlantı değeri yalnız bellekte aday dosyaların baytlarıyla karşılaştırıldı; eşleşme 0. İnceleme dışında kalan kısa veya boş sır değeri yoktu; değerler çıktıya yazılmadı. |
   | Sınırlı içerik taraması | Bilinen erişim tokeni, özel anahtar, JWT ve yerel makine kimliği deseninde eşleşme 0; ikili dosya ve 1 MB üzeri aday 0; kamu JSON belgelerinde ham konuşma, model yanıtı, kaydetme tokeni veya hesap metni alanı 0. |
   | Kamu belgeleri ve bağlantılar | Bozuk JSON 0; bulunmayan Markdown hedefi 0. Yedi eski rapordaki 18 Git dışı çıktı bağlantısı açık yerel kod yolu olarak işaretlendi; bu çıktılara kalan tıklanabilir bağlantı 0. |
   | [Deney defteri](../../../results.md) | 45 tarihsel kayıt, 34 ayrı deney; en son sürümlerdeki 25 kamu kanıtı hedefinin tamamı mevcut ve kaydedilmiş SHA-256 ile eşleşiyor. Eski sürümler değiştirilmedi. |

3. Maddeler:

   **KUSUR**

   M1 Yedi eski rapordaki 18 yerel çıktı bağlantısı GitHub'da varmış gibi tıklanabiliyordu; mevcut etiket ve tam yol korunarak “Git dışı yerel çıktı” kod yoluna çevrildi (DÜZELTİLDİ).

   M2 Üç eski rapordaki kullanıcıya özgü Windows araç yolu genel kullanıcı profili ifadesiyle değiştirilmiş; güncel TR/EN çalışma ortamı rehberleri 110 saniyelik sınırın her iki öneri yoluna uygulandığını doğru belirtiyor (DÜZELTİLDİ).

   **TUZAK**

   M3 Bu sınırlı yayın incelemesi güvenlik tarayıcısı değildir; desen veya tam değer eşleşmesi bulunmaması bütün gizli veri türlerinin yokluğunu kanıtlamaz. `gitleaks` eksikliği ayrıca raporlanır.

   M4 Envanter bir çalışma ağacı anına aittir; diğer teslim belgeleri sonradan eklenebilir. Son aşamadaki Git indeksi ve uzak commit doğrulaması bu raporun kanıtı değildir.

   **GÖZLEM**

   M5 Kamu kanıtları sayılar, durumlar, sınırlı açıklamalar ve özet değerleri içeriyor; sesler, modeller, veritabanı dosyaları, ham metinler ve yerel `.env` dosyaları yayına aday listede bulunmadı.

   M6 [TR](../../TEXT_REVIEW_RUNTIME.md) ve [EN](../../TEXT_REVIEW_RUNTIME_EN.md) çalışma ortamı açıklamaları `correction-preview` ile `correction-suggestion` yollarını birlikte kapsıyor; [kullanım rehberi](../../tr/contextual-transcript-review.md) ayrı kullanıcı onaylı sürümü açıklıyor.

   **AÇIK**

   M7 Yerel test günlükleri Git dışında kalır ve başka bir klonda bulunmaz; kamu raporundaki sonuç özetleri bunların yerini almaz. Bu inceleme kapsamında ham çıktılar yayımlanmadı.

   M8 Tam kalite/güvenlik kapısı, canlı tarayıcı, commit ve GitHub push sonuçları bu incelemede çalıştırılmadı veya doğrulanmadı; ana teslimin ayrı kanıtı bekleniyor.

   **YAN-ETKİ**

   M9 Yalnız bu rapor ve yedi eski rapordaki yerel bağlantı gösterimi değişti; ölçüm sayıları, test iddiaları, `results.md`, ürün kodu, özel çıktılar ve Git indeksi değiştirilmedi.
