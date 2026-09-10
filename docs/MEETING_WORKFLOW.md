# Toplantı kaydından konuşmacılı döküme

Durum: 10 Eylül 2026'da istenen ve [002 PRD](../specs/speaker-identity/PRDs/002-long-recording-analysis/PRD.md)
içinde kabul edilen hedef akış. Henüz uygulanmış özellik değildir. Mevcut web
uygulaması tek konuşmacının profilini kaydeder ve başka tek konuşmacılı kaydı
ECAPA ile karşılaştırır; mikrofon, çok kişili döküm ve otomatik yeni kişi hafızası yoktur.

## Kullanıcının izleyeceği akış

1. `Toplantılar` ekranında dosya seç veya mikrofonla kaydı başlat.
2. Dosya aktarımı tamamlanınca ya da mikrofon kaydını durdurunca analizi başlat.
3. Sistem uzun kaydı sınırlı parçalarda işler; kişi etiketlerini parçalar arasında birleştirir.
4. Sonuçta zaman, konuşmacı ve söylenen metin satırlarını gör.
5. Tanınan kişi mevcut adıyla görünür. Yeterli temiz kanıtı olan yeni kişi kalıcı
   geçici adla kaydedilir; sonraki kayıtta aynı kimlikle tanınabilir.
6. Kişiye mevcut profil ekranından isim verebilirsin. Model gerçek ismi sesten çıkarmaz.

Örnek çıktı yalnız gösterim içindir, modelin ürettiği bir sonuç değildir:

| Zaman | Konuşmacı | Söylediği |
| --- | --- | --- |
| 00:05–00:09 | Ayşe | Bugünkü gündemin ilk maddesi yeni tasarım. |
| 00:10–00:14 | Konuşmacı 2 · yeni kaydedildi | Ben önce test sonuçlarını paylaşayım. |
| 00:16–00:20 | Ayşe | Tamam, ardından tasarıma geçelim. |

## Model görevleri ve doğru hafıza davranışı

| İş | Seçilen ilk model |
| --- | --- |
| Kimin ne zaman konuştuğunu ayırma | pyannote Community-1 |
| Konuşmayı özgün dilinde yazıya çevirme | Whisper large-v3 |
| Önceki kayıtlardan kişiyi tanıma | Mevcut SpeechBrain ECAPA-TDNN |

İlk iki model Spark'a henüz hazırlanmadı. Community-1'in indirilmesi model
sahibinin Hugging Face koşullarını kullanıcı hesabında kabul etmeyi ve yetkili
okuma tokenini gerektirir. Token yalnız ilk hazırlıkta kullanılır, ses kayıtları
buluta gönderilmez. Çalışma sırasında model/bağımlılık indirilmez.

Spark'ta yeni diarization paketinin ARM64/TorchCodec uyumu da hazırlanmalıdır;
model erişimi tek başına bütün kurulumu tamamlamaz. Mevcut çalışan pilot bu hazırlık
sırasında değiştirilmedi.

Yeni kişi hafızası, model ağırlıklarının her seferinde yeniden eğitilmesi değildir.
Temiz ses örneği, model sürümü ve kişi vektörü mevcut tenant hafızasında tutulur.
Kısa, tutarsız veya üst üste konuşma yanlış bir kalıcı profile çevrilmez; böyle bir
kişi toplantı içinde etiketlenebilir fakat hafızaya kaydedildi olarak gösterilmez.
Yeniden denemede veya eşzamanlı iki toplantıda aynı kişi için çift kayıt önlenir.

Mikrofon kaydı fiziksel giriş cihazının duyduğu sesi alır. Çevrimiçi toplantıdaki
uzak kişilerin sesini otomatik yakalama, toplantı platformu bağlantısının ayrı işidir.
Bu ilk akışta döküm kayıt durdurulunca üretilir. 003 mevcut olarak yalnız canlı
konuşmacı kimliği analizi taslağıdır; canlı transkript bu isteğe eklenmedi.

50 kişi kalite hedefidir, kayıt kotası değildir. Konuşmacı ayrımı, kelime doğruluğu
ve kalıcı kimlik başarısı ayrı ölçülecek; mevcut tek konuşmacı test skorları bu
toplantı akışının doğruluk sonucu olarak kullanılamaz.

Kaynaklar: [Community-1 model kartı](https://huggingface.co/pyannote/speaker-diarization-community-1),
[Whisper large-v3 model kartı](https://huggingface.co/openai/whisper-large-v3).
