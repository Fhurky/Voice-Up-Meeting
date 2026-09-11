# Toplantı doğruluğunu ölçme

Bir toplantıda doğru kişi sayısını bulmak, konuşulan her şeyi doğru kişiye
yazdığımızı tek başına göstermez. Kişi tanıma, konuşmacı aralıkları ve metin
hatalarını ayrı ölçeriz. Mevcut model zinciri Community-1 konuşmacı ayrımı,
WeSpeaker 256 boyutlu toplantı kimliği, bağımsız ECAPA 192 boyutlu kimlik denetimi
ve Whisper large-v3 metin çıkarımı kullanır. Yeni kişi kaydı bu modelleri yeniden
eğitmez; doğrulanmış ses örneğini ve modele özgü temsilleri saklar.

Kalıcı kişi tanımada, değerlendirmeye girecek kayıtlı kişiler ve sorgular
önceden sabitlenir. Her bilinen kişinin doğru kimlikle tanınması doğru kabul;
yanlış kimlikle tanınması hem yanlış kabul hem kaçırmadır. Bilinen kişinin
belirsiz veya kullanılamaz kalması da kaçırmadır. Galeri dışındaki bir kişinin
kayıtlı kimliklerden birine bağlanması yanlış kabuldür.

- **Precision (kesinlik):** Doğru kimlikle tanınan sorguları, doğru ve yanlış
  kimlik kabullerinin toplamına böleriz.
- **Recall (yakalama):** Doğru kimlikle tanınan bilinen sorguları, planlanan
  bütün bilinen sorgulara böleriz; profili oluşturulamayan kişiler paydada kalır.
- **F1:** Doğru kabullerin iki katını, doğru kabullerin iki katı ile yanlış
  kabuller ve kaçırmaların toplamına böleriz; kesinlik ve yakalamayı birlikte ölçer.
- **İlk kayıt kapsamı:** Gerçekte oluşturulabilen doğrulanmış profil sayısını,
  kaydedilmesi planlanan kişi sayısına böleriz.
- **Yanlış yabancı kabulü:** Galeri dışındaki kişilerden herhangi bir kayıtlı
  kimliğe bağlanan sorguları, bütün galeri dışı sorgulara böleriz.

Gerçekte kaydedilmiş kişilere koşullu yakalama da ayrıca verilebilir; bu sayı
ilk kayıt başarısızlıklarını içermediği için toplam yakalama yerine geçmez.
Bir payda boşsa skor üretilmez. Aynı sorguların 5/10/20/50 kişilik galerilerde
tekrar denenmesi bağımsız yeni ses örnekleri oluşturmaz; bu sonuçlar ayrı verilir.
Galeri büyüdükçe aynı sorguların bilinen/yabancı oranı da değişiyorsa precision
ve F1 değişimini yalnız galeri büyüklüğüne bağlayamayız; her aşamanın bilinen
ve yabancı sorgu sayısını ayrıca gösteririz.
Tek tek temiz kliplerle yapılan galeri ölçümü, uzun toplantının konuşmacı
ayrımı ve otomatik yeni kişi kaydıyla aynı uçtan uca deney değildir.

`cpWER`, her kişinin bütün sözlerini zaman sırasıyla birleştirip kişi etiketleri
arasında en düşük kelime hatası veren eşlemeyi bulur; değiştirme, silme ve ekleme
sayısının toplamını bütün referans kelimelerine böler. Eksik kişinin sözleri
silme, fazla kişinin sözleri ekleme olarak sayılır. Kelime hata oranı yüzde
100'ü aşabilir. Bu ölçü, isim verilmiş kalıcı kişilerin sonraki toplantıda aynı
kimlikle tanındığını kanıtlamaz. Tanım, [MeetEval'in kişi eşlemeli metin
değerlendirmesine](https://github.com/fgnt/meeteval) dayanır.

Kişisi belirsiz bütün metin ayrı bir akış olarak korunur. `assigned_only`, bu
akışı gerçek bir kişiye eşlemeyen ek bir hata ölçüsüdür; belirsiz kelime oranı
da ayrıca yazılır. Eksik referansta sıfır hata uydurulmaz. Tam referans olmayan
kesitler için metin puanı üretilmez. Kaynak aralığı uyuşması, kelime hata oranı
veya elle işaretlenmiş konuşmacı ayrım hatası olarak sunulmaz.

Çevrimdışı komut şu biçimde çalışır:

```powershell
.venv/Scripts/python.exe scripts/score-meeting-transcript.py --input evaluation.json --output metrics.json
```

Girdi her kişinin zaman sırasındaki bütün metnini bir kez içerir:

```json
{
  "schema_version": 1,
  "source_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "reference_complete": true,
  "reference": [{"speaker_id": "reference-1", "text": "Toplantıya başlayalım"}],
  "hypothesis": [{"speaker_id": "observed-1", "text": "Toplantıya başlayalım"}]
}
```

Örnekteki hash yerine gerçek kaydın SHA-256 özeti yazılır; komut girdi dosyasının
hashini ayrıca hesaplar, kaynak sesi yeniden açmaz. Referansın gerçekten tam
olması ve zaman sırasının doğruluğu veri hazırlayıcısının sorumluluğundadır.
Belirsiz hipotez `speaker_id: null` kullanır. Çıktıda ham metin ve kişi adı yoktur;
mevcut çıktı dosyasının üzerine yazılmaz.

Sabit `unicode-words-v1` normalizasyonu Unicode NFKC ve küçük harf dönüşümü
uygular; harf, rakam, birleştirici işaret ve kelime içi kesme işaretini korur.
Noktalama ayırıcıdır; sayılar açılmaz ve kelimeler anlamına göre düzeltilmez.
Her tarafta en fazla 200 kişi akışı ve 50.000 kelime, çiftler toplamında en fazla
50 milyon karşılaştırma hücresi kabul edilir. Her tarafın toplam metni hem ham
hem Unicode dönüşümü sonrasında en fazla iki milyon karakter olabilir. Sınır aşımı hata verir; kelime veya
kişi sessizce kesilmez.

Model seçimini etkileyen önceki kayıtlar regresyon verisi olarak adlandırılır.
Yeni değerlendirme kişileri, parçaları ve hashleri onlardan ayrılır; seçim ve
normalizasyon sonuçlara bakılmadan sabitlenir. Kalite nedeniyle kaydedilemeyen
kişiler ve belirsiz sorgular paydada kalır. İngilizce sesli kitap ölçümü, doğal
Türkçe toplantı doğruluğu kabulü yerine geçmez.

Saklanan örnek ile toplantıdaki bütün konuşmacı grubu da ayrı değerlendirilir.
Bir kişinin temiz örneği korunurken, gruba yanlış bağlanan başka bir kişinin
sözleri aynı isimle gösterilebilir. Elli kişilik B/C denemelerinde 37 örneğin
tamamı değişmeden ve temiz kaldı; buna rağmen bazı tanınmış gruplarda yabancı
kaynak aralıkları bulundu. Bu nedenle örnek saflığı kimlik doğruluğu olarak
sunulmaz; bütün tanınmış satırlar, doğrulanamayan atamalar ve bütün 50 kişi
sonuçlarda görünür kalır.

Ek kaynak-süre ölçümü, kimlik atanmış her grubun sahip olduğu kaynak aralıklarını
profilin doğrulanmış sahibiyle karşılaştırır. Doğru sahip, başka kaynak, etiketsiz
eklenmiş boşluk ve yinelenen atama süreleri ayrı sayılır. Referanslar tam kaynak
cümlelerini ve iç sessizlikleri kapsadığı için bu ölçüm insan etiketli konuşmacı
ayrım hata oranı değildir. İlk tarif B görüldükten sonra keşif için oluşturuldu,
C sonucu görülmeden sabitlendi; [B raporu](evidence/2026-09-11-accuracy-audit/capacity50-native-b-memory-report.md)
ve [C raporu](evidence/2026-09-11-accuracy-audit/capacity50-native-c-memory-report.md)
ilk katı kişi eşleme sayılarıyla birlikte her iki ölçümü korur.
