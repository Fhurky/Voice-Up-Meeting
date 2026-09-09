# Konuşmacı tanıma: model araştırması ve başlangıç kararı

Araştırma ve kaynaklara erişim tarihi: **8 Eylül 2026**. Aşağıdaki performans sayıları kaynak sahiplerinin bildirdiği sonuçlardır; bu projede henüz gerçek ses üzerinde ölçülmüş sonuç değildir.

## Karar

Spark güncellemesi: ECAPA korunmuş karşılaştırma referansıdır. 128 GB ortak belleğe sahip
DGX Spark hedefinde **WeSpeaker ResNet293-LM ve ERes2NetV2** ilk karşılaştırma grubuna
alınmıştır. Model seçimi 8 GB dizüstü GPU sınırına göre yapılmayacak; aynı Türkçe açık
küme protokolündeki sonuçlar belirleyici olacak. Hedef runtime ve deney sırası
[DGX_SPARK_PLAN.md](DGX_SPARK_PLAN.md) içindedir.

İlk sürümde **SpeechBrain ECAPA-TDNN ile konuşmacı embedding'i, kalıcı profil deposu ve bilinmeyen kişiyi reddedebilen eşleştirme** geliştirilecek. Karışık toplantı kaydını konuşmacılara bölmek için **pyannote Community-1** ayrı bir adaptör olacak. ECAPA, kolayca doğrulanabilir bir başlangıç referansıdır. Kalıcı model seçimi, Türkçe toplantı değerlendirmesinde ECAPA ile **WeSpeaker ResNet293-LM** ve **3D-Speaker CAM++ / ERes2NetV2** karşılaştırıldıktan sonra yapılmalı. NeMo TitaNet de karşılaştırma adayıdır.

Bu seçim “ECAPA en iyi modeldir” iddiası taşımaz. Hedefimiz aynı veri, süre, donanım ve hata kabul koşullarında en iyi çalışan sistemi seçmektir. Türkçe, mikrofon değişimi, kısa konuşma, benzer sesler ve kayıtlı kişi sayısının büyümesi test edilmeden onlarca kişi için doğruluk sözü verilemez.

## Birbirinden ayrı üç problem

| İş | Çıktı | Bu projedeki karşılığı |
| --- | --- | --- |
| Diarization | Bir kayıtta kimin ne zaman konuştuğunu belirten yerel etiketler | `meeting_A/SPEAKER_00` zaman aralıkları |
| Kalıcı konuşmacı tanıma | Yeni sesi kayıtlı kişilerle karşılaştırma; bilinen/bilinmeyen/belirsiz kararı | Toplantılar arasında aynı `speaker_id` |
| Konuşmayı yazıya çevirme, ASR | Söylenen sözcükler ve zamanları | Sonraki aşamada konuşmacıya bağlanan transkript |

Community-1 model kartı dosya bazında diarization çıktısı gösterir. Bu çıktının yerel etiketini başka toplantıdaki aynı etiketle eşitlemek kalıcı kimlik tanıma sağlamaz; ayrı profil eşleştirme katmanı bizim mimari kararımızdır. Karttaki `exclusive_speaker_diarization` transkript hizalamayı kolaylaştırır; gerçek eşzamanlı konuşmaları değerlendirmek için normal diarization çıktısı korunmalıdır. [Community-1 model kartı](https://huggingface.co/pyannote/speaker-diarization-community-1)

Bir kişinin sisteme eklenmesi için her defasında ağırlıkları yeniden eğitmek gerekmiyor. Önerilen başlangıç yöntemi, temiz konuşma örneklerinden çıkarılan sayısal ses temsillerini ve bunların kökenini saklamak, yeni örnekleri bu profillerle karşılaştırmaktır. İsim bilinmiyorsa kalıcı bir `Katılımcı 6` kimliği kullanılabilir; ses modelinin kişinin gerçek adını kendi başına bilmesi beklenmez.

## İncelenen aileler

| Aile ve somut aday | Rol ve seçim nedeni | Sınır / dikkat edilmesi gereken nokta |
| --- | --- | --- |
| SpeechBrain `spkrec-ecapa-voxceleb` | Embedding çıkarımı; belgelenmiş Python arayüzü ve kosinüs karşılaştırması. İlk çalışan referans. | VoxCeleb üzerinde eğitilmiş; Türkçe toplantı başarısı ayrıca ölçülecek. Tensor girişinde 16 kHz tek kanal sağlanmalı. [Model kartı](https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb) |
| pyannote `speaker-diarization-community-1` | Karışık kayıtta konuşmacı zaman aralıkları ve sayısını tahmin eden yerel pipeline. | Kimlik veritabanı olarak kullanılmayacak. İlk indirmede HF hesabı, erişim koşullarının kabulü ve token gerekiyor; indirilince offline çalışabilir. [Model kartı](https://huggingface.co/pyannote/speaker-diarization-community-1) |
| WeSpeaker `wespeaker-voxceleb-resnet293-LM` | Daha güçlü aday olarak embedding karşılaştırması; ResNet ailesinin farklı boyutları ve ONNX çıktıları mevcut. | Büyük modelin hız/bellek bedeli ölçülecek. `LM` ve AS-Norm sonuçları çıplak kosinüs sistemine aynen taşınamaz. [ResNet293-LM](https://huggingface.co/Wespeaker/wespeaker-voxceleb-resnet293-LM), [ön eğitimli modeller](https://github.com/wenet-e2e/wespeaker/blob/master/docs/pretrained.md) |
| 3D-Speaker CAM++ / ERes2NetV2 | Hız/doğruluk alternatifleri. `iic/speech_campplus_sv_zh-cn_16k-common` ve `iic/speech_eres2netv2_sv_zh-cn_16k-common` somut adaylar. | Bu checkpoint'ler yaklaşık 200 bin konuşmacılı Çince veriyle eğitilmiş; repo içindeki VoxCeleb tarifinin skoru bu checkpoint'in Türkçe skoru değildir. [Resmî repo](https://github.com/modelscope/3D-Speaker), [CAM++ kartı](https://modelscope.cn/models/iic/speech_campplus_sv_zh-cn_16k-common/summary) |
| NVIDIA NeMo TitaNet / Sortformer | TitaNet-Large embedding için ek karşılaştırma adayı. Sortformer canlı diarization için ileride değerlendirilebilir. | İncelenen `diar_streaming_sortformer_4spk-v2` en fazla 4 konuşmacı çıkarır; 5 ve üzerindeki kayıtlarda performans düşüşü belgelenmiştir. Bu checkpoint onlarca konuşmacı hedefinin ana diarizer'ı olmayacak. Bu sınır TitaNet profil veritabanına ait değildir. [TitaNet](https://huggingface.co/nvidia/speakerverification_en_titanet_large), [Sortformer 4spk-v2](https://huggingface.co/nvidia/diar_streaming_sortformer_4spk-v2) |

## Kod lisansı ve ağırlık lisansı ayrı izlenecek

Bu tablo resmî kaynakların lisans beyanlarını kaydeder. Belirli bir checkpoint indirildiğinde revision, dosya özeti, kart ve lisans metni de kayıt altına alınmalı; kütüphanenin lisansından bütün ağırlıkların lisansı çıkarılmamalı.

| Bileşen | Kütüphane / kod | İncelenen ağırlık |
| --- | --- | --- |
| SpeechBrain ECAPA | [Apache-2.0](https://raw.githubusercontent.com/speechbrain/speechbrain/develop/LICENSE) | Kartta [Apache-2.0](https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb) |
| pyannote Community-1 | pyannote.audio [MIT](https://raw.githubusercontent.com/pyannote/pyannote-audio/develop/LICENSE) | [CC-BY-4.0 ve erişim koşulları](https://huggingface.co/pyannote/speaker-diarization-community-1) |
| WeSpeaker ResNet293-LM | WeSpeaker [Apache-2.0](https://github.com/wenet-e2e/wespeaker) | Seçilen checkpoint [CC-BY-4.0](https://huggingface.co/Wespeaker/wespeaker-voxceleb-resnet293-LM); diğer modeller için [veri kümesine bağlı lisans açıklaması](https://github.com/wenet-e2e/wespeaker/blob/master/docs/pretrained.md) |
| 3D-Speaker CAM++ / ERes2NetV2 | 3D-Speaker [Apache-2.0](https://github.com/modelscope/3D-Speaker) | ModelScope kartları Apache-2.0 beyan ediyor: [CAM++](https://modelscope.cn/models/iic/speech_campplus_sv_zh-cn_16k-common/summary), [ERes2NetV2 kart başlığı](https://www.modelscope.cn/models/iic/speech_eres2netv2_sv_zh-cn_16k-common/feedback/issueDetail/42751). ERes2NetV2 tam kart içeriği bu araştırmada yüklenemedi; indirilen revision'ın lisans dosyası ayrıca kontrol edilecek. |
| NeMo TitaNet / Sortformer | NeMo [Apache-2.0](https://raw.githubusercontent.com/NVIDIA/NeMo/main/LICENSE) | İncelenen [TitaNet](https://huggingface.co/nvidia/speakerverification_en_titanet_large) ve [Sortformer 4spk-v2](https://huggingface.co/nvidia/diar_streaming_sortformer_4spk-v2) kartlarında CC-BY-4.0 |

## Yayınlanmış skorları nasıl okuyacağız?

| Örnek | Kaynağın bildirdiği sonuç | Neden doğrudan ürün doğruluğu değil? |
| --- | --- | --- |
| SpeechBrain ECAPA | VoxCeleb1-test cleaned EER %0,80 | İki kayıt arasındaki doğrulama değerlendirmesi; 50 kişilik açık küme tanıma ölçümü değil. [Kaynak](https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb) |
| WeSpeaker ResNet293-LM | Vox1-O-clean EER %0,447; LM ve AS-Norm açık | Normalizasyon ve değerlendirme tarifi sonucu etkiliyor. [Kaynak](https://huggingface.co/Wespeaker/wespeaker-voxceleb-resnet293-LM) |
| 3D-Speaker CAM++ / ERes2NetV2 | Repo tablosunda VoxCeleb1-O EER sırasıyla %0,65 / %0,61 | Farklı veri/tarif ile eğitilmiş 200k Çince checkpoint'ine aynı sayı atfedilemez. [Kaynak](https://github.com/modelscope/3D-Speaker) |
| NeMo TitaNet-Large | VoxCeleb1 cleaned EER %0,66 | Karttaki diarization skorları ayrıca oracle VAD koşulunda; otomatik VAD pipeline'ıyla doğrudan karşılaştırılamaz. [Kaynak](https://huggingface.co/nvidia/speakerverification_en_titanet_large) |
| pyannote Community-1 | AMI IHM DER %17,0; SDM DER %19,9 | Tam otomatik, collar=0, overlap dahil. EER'den farklı bir hata türünü ölçer. [Kaynak](https://huggingface.co/pyannote/speaker-diarization-community-1) |

**EER ve DER aynı ölçek değildir.** EER, doğrulamada yanlış kabul ve yanlış ret oranlarının eşitlendiği çalışma noktasını özetler. DER, konuşma zamanının tespiti ve kime atandığını değerlendirir. Farklı konuşmacı sayısı, deneme listesi, eğitim verisi, VAD, collar, overlap ve skor normalizasyonu olan tablolar tek bir sıralamaya dönüştürülmeyecek. Proje karşılaştırmasının protokolü [EVALUATION_PLAN.md](EVALUATION_PLAN.md) içinde tanımlıdır.

## Kalıcı profil tasarımına etkisi

Önerilen akış: kaliteli tek konuşmacılı örnek → embedding → kayıtlı profillerle karşılaştırma → eşik ve ilk iki aday arasındaki fark kontrolü → bilinen / bilinmeyen / belirsiz kararı. Kosinüs skoru yüzde güven değildir; eşik ve karar farkı doğrulama verisinden kalibre edilecek.

Yeni olduğu düşünülen kişinin ilk kısa veya örtüşen parçası doğrudan güvenilir kalıcı profil olmayacak. Birden fazla temiz parçanın aynı kişiye ait olduğuna dair yeterli kanıtla aday profil oluşturulacak; belirsiz eşleşmeler profili değiştirmeyecek. Profil ekleme ve güncelleme kayıtları geri alınabilir olmalı. Böylece bir yanlış eşleştirmenin sonraki toplantılara yayılması ölçülebilir ve düzeltilebilir.

Embedding'ler model kimliği, revision ve ön işleme ayarlarıyla birlikte saklanmalı. Model değişince eski ve yeni embedding'ler aynı uzaydaymış gibi karşılaştırılmamalı. İlk aşamada çevrim içi fine-tuning yerine denetlenebilir örnek biriktirme kullanılacak; fine-tuning ihtiyacı ancak gerçek toplantı hata analiziyle kararlaştırılacak.
