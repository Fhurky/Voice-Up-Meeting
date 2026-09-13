# Türkçe ses verisi araştırması ve deney seçimi

Tarih: 2026-09-13. Kapsam: Türkçe toplantı kaydını metne çevirme, toplantı içinde
konuşmacıları ayırma ve farklı toplantılarda aynı kişiyi hatırlama.
Sabit teknoloji profili: `kt-vibecoding-python-web-v2`.
Uygulama gereksinimlerinin otoritesi
[009 Accepted PRD](../specs/speaker-identity/PRDs/009-turkish-evaluation-ledger/PRD.md),
uygulama adımları onun [planı](../specs/speaker-identity/PRDs/009-turkish-evaluation-ledger/plan.md)
ve [görevleridir](../specs/speaker-identity/PRDs/009-turkish-evaluation-ledger/tasks.md).
Bu dosya kaynak araştırmasını ve seçimin gerekçesini saklar; ikinci bir gereksinim
veya tamamlanma otoritesi değildir. Gerçek deney sonuçları [results.md](../results.md)
içinde tutulur.

## Karar

13 Eylül sonraki kapsam genişletmesi [010 PRD](../specs/speaker-identity/PRDs/010-expanded-turkish-benchmark/PRD.md)
altında FLEURS Türkçe test bölümünün tamamını ve MediaSpeech'in önceki 80 klip
dışındaki bütün 2.433 kaydını hazırladı. [Kaynak denetiminde](../docs/evidence/2026-09-13-expanded-turkish/dataset-coverage-report.md)
3.176 yeni klip/12,29 saat ile önceki 80 klip arasında hem dosya hem çözülen
ses örneklerinde tam kopya bulunmadı. FLEURS test metadata'sındaki 743 kaydın
tamamı MALE olarak etiketlidir; 329 cümle kimliği kişi kimliği değildir.
Bu kapsam sınırı [sabit FLEURS kaynak raporunda](../docs/evidence/2026-09-13-expanded-turkish/fleurs-source-report.md)
kaydedildi. Veri hazırlama sonucu model başarısı değildir; gerçek skorların
otoritesi [deney günlüğü](../results.md) ve ilgili koşum kanıtıdır.

İlk yerel deney için **Real-TurnTurk** seçildi: küçük olmasına rağmen gerçek
Türkçe görüntülü görüşmeler, ayrı konuşmacı kanalları ve kayıtlar arasında tekrar
eden kişi etiketleri içeriyor. Bu özellikler, yalnız okunmuş cümlelerden oluşan
büyük bir koleksiyondan daha doğrudan toplantı hafızasını sınar. Bağımsız konuşmayı
metne çevirme (Automatic Speech Recognition, ASR) kontrolü için **FLEURS Türkçe**
ve **MediaSpeech Türkçe** uygun tamamlayıcılardır. Daha geniş eğitim/uyarlama
havuzları **ISSAI Turkish Speech Corpus** ve filtrelenmiş **YODAS Türkçe** olarak
ayrılır. Bunların indirilmesi veya eğitimde kullanılması, bu araştırma dosyasının
yazılmasıyla gerçekleşmiş sayılmaz.

Yaklaşık 50 kişinin farklı toplantılarda yüksek doğrulukla hatırlanması hedefi
korunur. Seçilen açık görüşme paketi altı kişidir; bu veriyle 50 kişi başarısı,
kusursuz doğruluk veya bir model iyileşmesi iddia edilemez.

[Ek kişi hafızası taraması](TURKISH_SPEAKER_MEMORY_SOURCES_ADDENDUM.md)
altı adayın kalıcı kişi etiketlerini, farklı oturum kapsamını ve gerçek erişimini
inceler. Büyük katalog sayıları, indirilebilir ve doğrulanmış Türkçe kişi
eşlemeleri yerine kullanılmaz.

## Tarama yöntemi ve kaynak güveni

Resmî veri kartları, üretici depoları, dağıtıcı katalogları ve araştırmacıların
makaleleri karşılaştırıldı. Toplama listeleri yalnız keşif amacıyla kullanıldı;
aşağıdaki sayısal iddialar doğrudan bağlantılı birincil kaynaklara dayanır.
"Saat" değerlerinde yalnız Türkçe bölüm ve yayımlanan sürüm esas alındı.
Satıcının katalog beyanı bağımsız veri denetimiyle aynı kabul edilmedi.

Üç görevin referans ihtiyacı farklıdır:

- ASR için sesin gerçekten söylediğini karşılayan metin gerekir. Bir modelin
  ürettiği altyazı, insan tarafından doğrulanmış metinle eşdeğer değildir.
- Konuşmacı ayrıştırma için konuşmacı başına başlangıç/bitiş zamanları, sessizlik
  ve üst üste konuşma bölgeleri gerekir. Dosyada yalnız kişi etiketi bulunması
  bu zaman referansını sağlamaz.
- Toplantılar arası hafıza için aynı kişiye farklı kayıtlarda aynı referans
  etiketi verilmiş olmalıdır. Bir kaydın iki parçası iki bağımsız oturum değildir;
  farklı kaynaklardaki `speaker_0` değerlerini yeniden numaralamak da gerçek
  kişilerin farklı olduğunu kanıtlamaz.

Veri kartında belirtilmeyen kişi sayıları, oturum ayrımları ve kalite oranları
tahmin edilmedi. Lisans sütunu incelenen yayının beyanıdır; alttaki ses kaynakları
ve ek erişim koşulları ayrıca korunmalıdır.

## Açık veya erişilebilir Türkçe adaylar

| Veri kümesi | Doğrulanan Türkçe büyüklük | Referans ve oturum niteliği | Lisans / erişim | Projedeki yeri |
| --- | --- | --- | --- | --- |
| [Real-TurnTurk veri kartı](https://huggingface.co/datasets/tugrulbayrak/Real-TurnTurk) | Açık sürüm 1,94 saat, 6 diyalog, 6 kişi; 12 ayrı ses kanalı | Gerçek senaryosuz görüntülü görüşme; kalıcı `p01`–`p06`; bazı kişiler 2–3 kayıtta tekrar eder; zamanlı metin ve otomatik konuşma etkinliği | Apache-2.0; açık dosyalar | İlk gerçek Türkçe hafıza deneyi; referanslar insan altın standardı olarak kabul edilmez |
| [Common Voice 26.0 Turkish](https://mozilladatacollective.com/datasets/cmqinosfq00x4nr07gnk0rdf9) | 135,64 saat; 130,1 saat doğrulanmış; 126.723 klip; 1.829 katılımcı; 2,78 GB | `client_id` var; kısa okunmuş cümleler; ortalama 3,854 sn; gerçek oturum tekrarı belgelenmiyor | CC0-1.0; ayrıca kimlik belirlememe ve yeniden barındırmama koşulları var | ASR çeşitliliği; bu projede kimlik/hafıza testine otomatik kabul edilmez |
| [FLEURS `tr_tr`](https://huggingface.co/datasets/google/fleurs/blob/main/README.md) | 2.526 eğitim, 338 doğrulama, 743 test kaydı; konfigürasyon indirme metadatası yaklaşık 2,74 GB | Şemada kalıcı konuşmacı kimliği yok; `id` kişi kimliği değildir; eğitim konuşmacıları doğrulama/testten farklı | CC-BY-4.0; açık Hugging Face dosyaları | Ayrılmış Türkçe ASR ölçümü; kişi hafızası veya gerçek toplantı ölçmez |
| [MediaSpeech Turkish / SLR108](https://www.openslr.org/108) | 10 saat; Türkçe arşiv 618 MB | Haber videolarından kısa ses parçaları ve insan transkripsiyonları; temel dağıtımda kalıcı kişi referansı yok | CC-BY-4.0; doğrudan TR.tgz; [WAV sürümü](https://github.com/NTRLab/MediaSpeech) de var | FLEURS dışında haber/ortam koşullarında ASR karşılaştırması |
| [ISSAI Turkish Speech Corpus](https://huggingface.co/datasets/issai/Turkish_Speech_Corpus) | 218,2 saat; 186.171 ifade; 21,4 GB | Yayımlanan kart kişi sayısı ve çoklu oturum referansını doğrulamıyor | Kart MIT; açık tek `ISSAI_TSC_218.tar.gz` arşivi | Geniş Türkçe ASR havuzu; arşiv içeriği görülmeden hafıza referansı sayılmaz |
| [ESPnet YODAS](https://huggingface.co/datasets/espnet/yodas) | `tr000`: 588,698 saat; `tr100`: 4.067,68 saat; toplam 4.656,378 saat | İlk grup kullanıcı yüklemeli, ikinci grup otomatik altyazılıdır; kalıcı kişi referansı yok | CC-BY-3.0; dil/parça seçerek erişim | Taramada doğrulanan en geniş açık Türkçe ASR havuzlarından; filtreleme ve insan kontrolü sonrası eğitim/uyarlama adayı |
| [WorldSpeech `tr_tr`](https://huggingface.co/datasets/disco-eth/WorldSpeech) | 1.007,6 saat; TBMM kaynaklı | İnsan kaynaklı ve ASR metni, kaynak zamanları, oturum tarihi var; temel şemada `speaker_id` yok | CC-BY-NC-4.0; kaynak koşulları da geçerli | Araştırmada geniş kurumsal Türkçe ASR; mevcut haliyle kişi hafızası referansı değil |
| [Codyfederer/tr-combined](https://huggingface.co/datasets/Codyfederer/tr-combined) | 221.531 parça; 894 kaynak; bildirilen 2.158 konuşmacı etiketi; 85,2 GB; saat belirtilmemiş | Otomatik metin ve ayrıştırma; kaynak etiketleri çakışmasın diye numaralanmış | Kart CC-BY-4.0; erişim için iletişim bilgisi paylaşma koşulu | Yardımcı havuz; etiket sayısı doğrulanmış farklı kişi sayısı değildir |
| [tr-full-dataset](https://huggingface.co/datasets/umutkkgz/tr-full-dataset) | 41.427 parça; 88 kaynak; bildirilen 222 etiket; 13,4 GB | Otomatik metin/ayrıştırma; kart [ilk yayımlayıcıya](https://huggingface.co/datasets/Codyfederer/tr-full-dataset) atıf yapar | Kart CC-BY-4.0; incelenen türev açık | Daha küçük yardımcı havuz; kaynak ve kişi eşleme denetimi olmadan ana test olmaz |
| [VoxLingua107 Türkçe](https://cs.taltech.ee/staff/tanel.alumae/data/voxlingua107/) | 59 saat; kaynak sayfasında 5,7 GB | Dil tanıma amaçlı YouTube sesleri; ASR metni ve kalıcı kişi referansı sağlamaz | Üretici üniversitenin dil bazlı dağıtımı; seçilecek paketin koşulu ayrıca kaydedilmeli | Dil tanıma incelemesi; toplantı hafızası veya metin doğruluğu için yeterli değil |

Common Voice'un incelenen sürümü `cv-corpus-26.0-2026-06-12` olup dağıtım sayfası
17 Haziran 2026 tarihini gösterir. Bu taramada daha yeni bir Türkçe sürüm
doğrulanmadı; tekrar edinimde sürüm ve hash sabitlenmelidir. Eğitim/doğrulama/test
parçaları sırasıyla 41.401 / 11.868 / 11.869 kliptir. Bu sayılar bütün doğrulanmış
havuzun toplamı değildir. Yalnız lisans başlığını okuyup ek kullanım koşullarını
atlamamak gerekir. [Resmî veri kartı](https://mozilladatacollective.com/datasets/cmqinosfq00x4nr07gnk0rdf9)

ISSAI dağıtımının mevcut otomatik görüntüleyicisi arşiv düzeni nedeniyle hata
veriyor; bu, dosyanın indirilemediğini kanıtlamaz. Genel bir `load_dataset`
çağrısının çalışacağını varsaymak yerine [gerçek arşiv dağıtımı](https://huggingface.co/datasets/issai/Turkish_Speech_Corpus/tree/main)
üzerinden hazırlama gerekir. Şu araştırmada arşiv açılmadı ve içindeki kaynak
karışımı veya kişi eşleştirmeleri doğrulanmadı.

YODAS'ta "manual" altyazı yalnız kullanıcı tarafından yüklenmiş altyazıyı
belirtir; insan tarafından yazıldığı veya denetlendiği garanti değildir.
[YODAS2](https://huggingface.co/datasets/espnet/yodas2) kesilmemiş, 24 kHz ses
sağlayan ayrı dağıtımdır; eski YODAS Türkçe saatleri ona otomatik taşınmamalıdır.
Kalıcı kişi etiketi bulunmadan kaynak video kimliğini kişi kimliği olarak
kullanmak doğru değildir. [YODAS açıklaması](https://huggingface.co/datasets/espnet/yodas)

WorldSpeech'te `human_transcript` ile `asr_transcript` ayrımı korunmalıdır.
Türkçe hizalama/filtreleme hattında Whisper kullanılması, bu verideki sonucun
Whisper'dan tümüyle bağımsız bir test olduğu varsayımını engeller. Kartın
ticari olmayan kullanım koşulu nedeniyle ürün modelini bu veriyle eğitmek
varsayılan seçenek olarak alınmadı. Bu çalışma yalnız verinin mevcut
niteliğini kaydeder. [Veri kartı](https://huggingface.co/datasets/disco-eth/WorldSpeech),
[hazırlama makalesi](https://arxiv.org/html/2605.09167v1)

## Lisanslı ve kurumsal alternatifler

| Veri kümesi | Doğrulanan kapsam | Hedefe katkı ve sınır | Erişim |
| --- | --- | --- | --- |
| [IARPA Babel Turkish, LDC2016S10](https://catalog.ldc.upenn.edu/LDC2016S10) | 213 saat; doğal ve okunmuş telefon konuşması; yedi ağız bölgesi; 8 kHz a-law sphere | Doğal Türkçe ve cihaz/ortam çeşitliliği; resmî katalog kesin kişi sayısını vermiyor; telefon kanalı toplantı mikrofonundan farklı | Özel LDC sözleşmesi; hesap/ücret |
| [Appen TUR_ASR001](https://www.appen.com/data-catalog/audio-catalogue/tur-asr001) | 41,5 saat; 200 görüşme; 100 arayan kişi ikişer arama, biri sabit biri mobil; 100 alıcılık havuz | Oturum ve cihaz değişimiyle 50 kişi hedefi için değerli aday; gerçek kalıcı ID ve tekrar eşleştirme şeması örnek dosyada doğrulanmalı | Ticari katalog; açık tam indirme yok |
| [METU Microphone v1.0, LDC2006S33](https://catalog.ldc.upenn.edu/LDC2006S33) | Resmî katalogda 5,6 saat; 120 kişi; kişi başına 40 cümle; yaklaşık 600 MB; 16 kHz | Kontrollü 50 kişi karşılaştırması için aday; gerçek toplantı veya farklı gün oturumları değil | LDC kullanıcı sözleşmesi; hesap/ücret |
| [Boğaziçi Turkish Broadcast News, LDC2012S06](https://catalog.ldc.upenn.edu/LDC2012S06) | 130 saat VOA radyosu; insan düzeltilmiş segment/metin, konuşmacı sınırı ve arka plan bilgisi | Haber alanında daha güçlü zaman/metin referansı; katalog kalıcı kişi sayısını doğrulamıyor | LDC kullanıcı sözleşmesi; hesap/ücret |
| [MagicHub BigTurkCSC](https://magichub.com/datasets/turkish-conversational-speech-corpus/) | 738 kişi; sayfa başlığı 1.537 saat, açıklaması 1.357 saat | Büyük doğal konuşma havuzu; sayfa içi saat çelişkisi ve oturum/ID şeması doğrulanmalı | Proprietary; satış talebi |
| [SpeechData.ai Turkish](https://www.speechdata.ai/datasets/turkish) | Satıcı beyanı 2.000 saat, 200 kişi; iki kişilik doğal konuşma, ayrı kanal ve zamanlı insan doğrulanmış metin | Hedefe yakın ticari aday; ham veri veya bağımsız kalite denetimi görülmedi | Ticari lisans; örnek/teklif talebi |

Bu kaynakların hiçbirine satın alma, form gönderme veya iletişim başlatılmadı.
Doğrudan veri örneği görülmeden katalog iddiaları doğruluk garantisi olarak
kullanılmamalıdır. Özellikle tekrar eden kişi sayısı, farklı gün/cihaz oturumları
ve izin verilen kimlik değerlendirmesi satın alma öncesi somut dosyayla
doğrulanmalıdır.

METU'nun **Spoken Turkish Corpus** çalışması, yukarıdaki **Microphone v1.0** ile
aynı veri değildir. Birincil araştırma, demo sürümünü 23 kayıt ve 2 saat 27 dakika
olarak açıklar; gündelik etkileşimler ve yayınlar içerir. Resmî site bu taramada
açılamadı; indirilebilir tam paket ve güncel erişim koşulları doğrulanmadığından
ilk otomatik deneyin bağımlılığı yapılmadı.
[ACL araştırması](https://aclanthology.org/W14-49.pdf),
[resmî proje adresi](https://std.metu.edu.tr/en/)

## Yanlış eşleştirmemek gereken kaynaklar

- **VoxPopuli** incelenen resmî dil kapsamına göre Türkçe içermiyor.
  [Resmî depo](https://github.com/facebookresearch/voxpopuli)
- **Multilingual LibriSpeech** sekiz dil içeriyor ve Türkçe bunlar arasında yok.
  [Resmî OpenSLR94](https://www.openslr.org/94/)
- **GigaSpeech2** Tayca, Endonezce ve Vietnamca içeriyor; Türkçe sürümü
  doğrulanmadı. [Resmî depo](https://github.com/SpeechColab/GigaSpeech2)
- **TBMM/GNACT ve ParlaMint metin derlemleri**, konuşmacı dönüşleri içerdiğinde
  bile otomatik olarak ses dosyası ve akustik zaman referansı sağlamaz. Bunlar
  ASR/ayrıştırma test sesinin yerine konamaz.
  [GNACT çalışması](https://aclanthology.org/2026.parlaclarin-1.6/),
  [ParlaMint üretici makalesi](https://pmc.ncbi.nlm.nih.gov/articles/PMC8807381/)
- **Syn-TurnTurk** gibi sentetik konuşma üretimleri, gerçek kişiyi farklı
  toplantılarda hatırlama başarısının kanıtı yapılmamalıdır. Real-TurnTurk kartı
  gerçek görüşme ile sentetik eşini açıkça ayırır.
  [Kaynak açıklaması](https://huggingface.co/datasets/tugrulbayrak/Real-TurnTurk)

## Real-TurnTurk: seçilen sürüm ve edinim kapsamı

Seçilen kaynak `tugrulbayrak/Real-TurnTurk`, sabit revision:
`db8f20f6eb6b215ec75fb466374fc5cc861b91df`.
[Revision kaydı](https://huggingface.co/datasets/tugrulbayrak/Real-TurnTurk/commit/db8f20f6eb6b215ec75fb466374fc5cc861b91df),
[sabit dosya ağacı](https://huggingface.co/datasets/tugrulbayrak/Real-TurnTurk/tree/db8f20f6eb6b215ec75fb466374fc5cc861b91df)

13 Eylül 2026 tarihinde resmî Hugging Face dosya ağacı API'si salt okunur
incelendi. Aşağıdaki bayt değerleri bu revision'ın dosya metadatasından
hesaplandı; ses çözülmüş veya dinlenmiş sayılmaz.

| Kayıt | Sol kanal yolu ve bayt | Sağ kanal yolu ve bayt | Metin CSV bayt | Etkinlik CSV bayt |
| --- | --- | --- | ---: | ---: |
| rec01 | `rec01/rec01__L_p06.webm` — 17.967.198 | `rec01/rec01__R_p03.webm` — 15.275.728 | 26.976 | 807.361 |
| rec02 | `rec02/rec02__L_p04.webm` — 18.210.793 | `rec02/rec02__R_p06.webm` — 19.791.434 | 26.344 | 867.441 |
| rec03 | `rec03/rec03__L_p03.webm` — 22.810.564 | `rec03/rec03__R_p01.webm` — 23.484.117 | 40.642 | 1.260.291 |
| rec04 | `rec04/rec04__L_p01.webm` — 15.660.124 | `rec04/rec04__R_p02.webm` — 16.952.257 | 27.660 | 827.109 |
| rec05 | `rec05/rec05__L_p05.webm` — 24.101.273 | `rec05/rec05__R_p06.webm` — 29.854.761 | 43.403 | 1.319.073 |
| rec06 | `rec06/rec06__L_p04.webm` — 17.853.760 | `rec06/rec06__R_p01.webm` — 16.427.465 | 26.781 | 863.051 |

Her satırdaki CSV yolları `recNN/recNN__text.csv` ve
`recNN/recNN__speech_activity.csv` biçimindedir. Sesler toplam **238.389.474**,
metin CSV'leri **191.806**, etkinlik CSV'leri **5.944.326** bayttır.
16.464 baytlık `README.md` dahil seçilen 25 dosya **244.542.070 bayt**, yaklaşık
233,2 MiB tutar. Animasyonlar 2.802.486.676 bayt ve yüz özellikleri 115.711.585
bayt olduğundan bu göreve alınmaz. Böylece bütün veri deposunu indirmek gerekmez.
[Doğrudan kaynak ağacı API'si](https://huggingface.co/api/datasets/tugrulbayrak/Real-TurnTurk/tree/db8f20f6eb6b215ec75fb466374fc5cc861b91df?recursive=true&expand=true)

WebM dosyaları için API'nin `lfs.oid` alanı içerik SHA-256 değeridir. Normal
CSV dosyalarının `oid` alanı ise Git blob SHA-1 değeridir; dosyanın SHA-256 değeri
gibi kaydedilmemelidir. Hazırlayıcı her indirilen dosyanın gerçek SHA-256 değerini,
beklenen boyutunu, uzak nesne kimliğini, kaynak deposunu, revision'ı ve dosya
yolunu yerel manifestte tutar; bu alanlar sabit kaynak URL'sini belirler.
İndirilen ham ses, metin ve kişi eşleme tablosu Git dışında kalır.

Gerçek CSV başlıkları, resmî `rec01` dosyalarından en fazla 8.192 baytlık salt
okunur okumayla kontrol edildi:

| Dosya | Alanlar | Yorum |
| --- | --- | --- |
| `rec01__text.csv` | `start_time,end_time,speaker,text` | Zaman biçimi `HH:MM:SS.mmm`; konuşmacı `pXX` |
| `rec01__speech_activity.csv` | `recording,frame,t_sec,person,speaking` | Kayıt kimliği, kare indeksi, saniye, kişi ve 0/1 etkinlik |

Bu kontrol ham ses indirmesi değildir. Hazırlayıcı diğer dosyaların şemasını,
geçerli kişi kümesini, sıralamayı, zaman sınırlarını ve bozuk satırları ayrıca
doğrulamalıdır. [Sabit metin dosyası](https://huggingface.co/datasets/tugrulbayrak/Real-TurnTurk/blob/db8f20f6eb6b215ec75fb466374fc5cc861b91df/rec01/rec01__text.csv),
[sabit etkinlik dosyası](https://huggingface.co/datasets/tugrulbayrak/Real-TurnTurk/blob/db8f20f6eb6b215ec75fb466374fc5cc861b91df/rec01/rec01__speech_activity.csv)

## Referans kalitesi ve yayımlanan kapsam farkı

Makale toplam 4,23 saat ve 11 kişilik araştırma derlemini anlatır, ancak bunun
yalnız bir alt kümesinin açık yayımlandığını belirtir. İndirilecek açık sürümün
yerine makaledeki tam büyüklüğü yazmak yanlıştır. Makale ayrıca kişi katkılarının
dengesiz olduğunu ve görüşme bazında ayırmanın kişi bazında tam bağımsızlık
sağlamadığını açıklar. [Üretici makalesi](https://arxiv.org/html/2608.22071v1)

Açık karttaki konuşma etkinliği etiketleri, ayrı kanallarda çalışan **Silero
Voice Activity Detection (VAD)**, yani konuşma etkinliği tespiti, çıktısıdır;
62,5 ms ızgara kullanır. İnsan tarafından denetlenmiş tüm ses başlangıç/bitiş
referansları olarak sunulmaz. Zamanlı metin bulunsa da kart açık bir insan
düzeltme ve hata denetimi protokolü vermiyor. Bu nedenle ilk metin/ayrıştırma
skorları **kaynak referansına göre tanılayıcı ölçüm** olarak etiketlenmelidir.
Otomatik referansa yakınlık insan doğruluğunun garantisi değildir.
[Veri kartı](https://huggingface.co/datasets/tugrulbayrak/Real-TurnTurk)

## İlk deney protokolü

Uygulanan hazırlama protokolü `voiceup-real-turnturk-v1` adını taşır;
yürütülen sürüm ve kapsam gerçek deney manifestinden okunur.
İlk taban çizgisi geliştirme/tanılayıcı deneyidir. Görülen hataya göre ayar
seçilen kayıtlar daha sonra saklı bağımsız test diye adlandırılmaz.

1. Sabit revision'daki seçili dosyaları edin, boyut/hash doğrula ve çözme aracının
   sürümünü kaydet. İnternet yalnız hazırlama adımında kullanılmalı; mevcut yerel
   model servisinin çevrimdışı çalışma sınırı korunmalı.
2. Her görüşmenin ilk 180 saniyesinde iki kanalı aynı başlangıç zamanında, süre
   ve sessizlikleri koruyarak 16 kHz, 16 bit, tek kanallı PCM WAV'a dönüştür.
   Kanalları sabit `(sol + sağ) / 2` kazancıyla karıştır; örnek sırasını ve
   sessizlikleri koru, kaynak zaman damgası kusurlarını ayrıca kaydet. Sessizlik veya örtüşme
   bölgelerini skor iyileştirmek için kesme. Bu işlem aynı gerçek görüşmenin
   kanal karışımıdır; rastgele cümlelerden yapay toplantı oluşturmak değildir.
   Metin referansına yalnız tamamen bu 180 saniyede kalan kaynak cümleleri girer;
   kesme sınırını aşan cümleler sayılır. Bunların ses ve hipotezde kalması, metin
   skorunu kesme sınırında yanlı kılar; skorlar bu nedenle tanılayıcıdır.
3. Uygulamaya yalnız karışık ses ve önceden bilinen aktif konuşmacı sayısını
   ver. Ayrı kanallar, kişi kodları, referans metin ve VAD yalnız değerlendiricide
   kalmalı; model girdisine veya eşik seçimine gizlice taşınmamalı.
4. Aynı deney tenant'ında aşağıdaki sırayı uygula. Yeni kişiye isim verme ve
   kalıcı profile bağlama mevcut ürün akışından geçmeli; gerçek kullanıcı
   profilleri deney verisiyle karıştırılmamalı. Referans kişi etiketleri yalnız
   anonim deney eşleştirmesi içindir.

| Adım | Beklenen kaynak kişiler | Beklenen hafıza davranışı |
| --- | --- | --- |
| rec01 | p06, p03 | İki kişi yeni; yeterli temiz konuşma varsa iki kayıt |
| rec02 | p04, p06 | p06 hatırlanır; p04 yeni |
| rec03 | p03, p01 | p03 hatırlanır; p01 yeni |
| rec04 | p01, p02 | p01 hatırlanır; p02 yeni |
| rec05 | p05, p06 | p06 hatırlanır; p05 yeni |
| rec06 | p04, p01 | İki kişi hatırlanır; yeni kişi kaydı beklenmez |

5. Mevcut kayıt kalite kuralları korunur. Referansın "aynı kişi" demesi modeli
   zorla eşleştirmek veya kısa konuşmayı yeterli kayıt saymak için kullanılmaz.
   Önceki adım kayıt açamadıysa sonraki adımdaki gerçek galeri durumu kaydedilir;
   gerçekte kayıtlı olmayan kişi için hatırlama başarısı uydurulmaz.
6. Konuşmacı sayısı bilinen ve bilinmeyen denemeler farklı deneyler olarak
   kaydedilir. Dil `tr` sabitken alınan sonuç `auto` ile karıştırılmaz. Aynı
   sesin tekrar değerlendirilmesi yeni bağımsız veri sayılmaz.
7. Çalışmayan/yarım kalan adımlar da günlüğe girer. Her deneme planlanan ve
   gözlenen kişi, kayıt, saniye ve metin kapsamını ayırır; tümden başarısız
   denemeye başarılı kalan parçaların skoru tek başına verilmez.

Bu zincirin uygun devamı, örneğin ilk kayıtlarla geliştirme yapıldıktan sonra
henüz açılmamış kayıtları ayrı tutmaktır. Kaynak tekrar eden altı kişiyle sınırlı
olduğundan bu ayrım yeni Türkçe kişilere geniş genelleme kanıtı yaratmaz. Daha
güçlü bağımsız değerlendirme başka gerçek görüşmeler ve başka kişiler gerektirir.

## Ölçüm ve uygulama geliştirme sırası

Mevcut **precision, recall, micro/macro F1, bilinmeyen kişi F1, VoiceUp Score,
kapsam ve yanlış kabul** tanımları korunur. Konuşmacı ayrıştırma hata oranı
(Diarization Error Rate, DER), kelime hata oranı (Word Error Rate, WER), karakter
hata oranı (Character Error Rate, CER) ve konuşmacı eşlemesi sonrası metin skoru
uygun referans varsa ayrı alanlarda raporlanır. İnsan tarafından doğrulanmamış
zaman etiketlerinden çıkan DER'nin referans niteliği açık yazılmalıdır.

Türkçe normalizasyonu `I→ı`, `İ→i`, birleşik/ayrık Unicode eşitliği ve Türkçe
harf ayrımlarını koruyan açık sürümlü seçenek olmalıdır. Ham referans ve hipotez
korunur; eski `unicode-words-v1` sonuçları yeni yöntemle sessizce yeniden
yorumlanmaz. Normalizasyon nedeniyle değişen WER, akustik model kazancı değildir.
`â`, `î`, `û` gibi harfleri körlemesine sadeleştirmemek konusunda Common Voice
Türkçe kartı da uyarır.
[Türkçe veri kartının işleme notları](https://mozilladatacollective.com/datasets/cmqinosfq00x4nr07gnk0rdf9)

Geliştirme sırası şu gerekçeyle seçildi:

- Önce mevcut model hattı ve Türkçe dil ayarıyla dondurulmuş taban çizgisi.
- Ardından hataları metin, konuşma sınırı, konuşmacı kümesi, yanlış kimlik,
  bilinmeyeni reddetme ve gereksiz profil açma olarak ayırma.
- Yalnız görülen hataya yönelik aday değişikliği; aynı geliştirme verisinde
  eşleştirilmiş önce/sonra, süre/bellek ve regresyon ölçümü.
- Ayrılmış değerlendirme verisinde yeniden kontrol; başarısız ve reddedilen
  adayların da `results.md` içinde korunması.
- Eğitim/ince ayar ancak referans kalitesi, kaynak ayrımı ve lisans uygunluğu
  karşılandıktan sonra. Büyük bir havuzu indirmiş olmak model eğitildi veya
  Türkçe doğruluğu yükseldi anlamına gelmez.

## 50 kişilik düzey için açık kalan veri gereksinimi

Elli kişi hedefi iki ayrı sınamayı gerektirir: kalıcı galeride yaklaşık 50 kişi
bulunurken doğru kişiyi seçmek ve tek bir toplantıda çok sayıda aktif konuşmacıyı
doğru ayırmak. Altı kişilik bir zincir veya 50 ayrı okunmuş ses klibi bu iki
durumu birlikte kanıtlamaz.

Güçlü bir hedef pakette yaklaşık 50 farklı Türkçe konuşmacının farklı günlerde,
cihazlarda ve görüşme eşleşmelerinde tekrar ettiği izinli kayıtlar; galeri dışı
yeni kişiler; kısa dönüşler; sessizlik; örtüşme ve farklı akustik koşullar
bulunmalıdır. Kişi/oturum ve metin-zaman referansları insan tarafından
denetlenmeli, aynı kaynak kayıt eğitim/ayar ve testte çakışmamalıdır. Konuşmacı
başına ölçüm ve görüşme bazında belirsizlik raporu, uzun konuşan birkaç kişinin
toplam skoru örtmesini önler.

Bu taramada hem açık indirilebilen hem de bütün bu koşulları doğrulanmış biçimde
sağlayan 50 kişilik Türkçe toplantı paketi bulunmadı. Bu, böyle bir kaynağın
hiç bulunamayacağının iddiası değildir. Gerçek toplantı paketi toplamak veya
oturum tekrarları belgelenmiş lisanslı kaynağı değerlendirmek açık veri açığını
karşılayabilir; mevcut küçük deneyin başarısı bu açığı kapatmış sayılmaz.

## Araştırma çıktısı ve kanıt sınırı

Kaynak araştırmasının ardından [hazırlayıcı](../scripts/prepare-turkish-meeting-evaluation.py)
ile 25 dosya indirildi; boyutları ve sabit Git/LFS nesne kimlikleri doğrulandı.
Her kaynağın SHA-256 değeri özel manifestte tutuldu. PyAV 18.0.0 içeren mevcut
yerel çıkarım imajında, ağ kapalıyken altı karışım üretildi. Her WAV dosyası
180 saniye, 16 kHz, tek kanal, 16 bit PCM ve 2.880.000 örnektir. Toplam ses
18 dakika; seçilen referans 2.341 boşlukla ayrılmış sözcük, sınırı aşan beş
cümledir. Bunlar model başarısı değil, gözlenmiş hazırlama kapsamıdır.

Tam kanal denetimi kaynak kusuru gösterdi: `rec01` kanallarında WebM sunum
zaman damgaları (PTS) birkaç saniye sıçrayıp tekrar ediyor; ilk 180 saniyede
`rec03` sol kanalında da milisaniyelik oynamalar var. PTS'ye kör yerleştirme
konuşma örneklerini üst üste yazacağı için hazırlayıcı önce durdu. Kabul edilen
009 `Decision 10`, `decoded-sample-clock-v1` politikasını kaydetti: her çözülmüş
örnek kendi sırasında korunur ve ilk örnek zaman sıfırıdır; ses eklenmez,
damga kusuru nedeniyle atılmaz, sessizlik kaldırılmaz. Kaynağın kesin çözme
yöntemi açıklanmadığından `unverified-source-timestamps` niteliği korunur.
Faster-whisper'ın resmî ses okuyucusu da FIFO'ya almadan önce paket damgalarını
devre dışı bırakır; bu teknik benzerlik kaynak referansının doğrulandığı
anlamına gelmez. [Resmî ses çözme kodu](https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/audio.py)

Bütün kanallar bellek büyütülmeden sona kadar çözüldü. On iki kanaldan on
birinin örnek süresi, yayımlanan VAD ızgarasının sonuyla 30 ms içinde uyuştu.
`rec02` sol kanalının tam süresi VAD sonundan 2,046 saniye kısa çıktı;
bu kanalın ilk 180 saniyesinde aynı büyük damga kusuru gözlenmedi. PTS
sapmaları, tam ses süresi, VAD/metin bitişi ve farklar kayıt başına manifestte
yer alır. Bitişlerin uyuşması iç zaman hizasını kanıtlamaz. Otomatik referansa
göre ayrıştırma veya metin skoru kesin insan doğruluğu olarak yorumlanamaz.

Ek hizalama tanılamasında, yayımlanan parametrelerle yerel Silero modeli CPU'da
ilk 180 saniyelik tekil kanallara uygulandı; eşik veya zaman kaydırması
aranmadı. On iki kanalda 34.560 kare merkezinin etkinlik etiketi karşılaştırıldı:
ortalama uyuşma %96,4236, kanal aralığı %94,4444–98,75 bulundu. Kaynak modelinin
kesin sürümü ve kareye dönüştürme kuralı belgelenmediğinden bu ölçüm bağımsız
bir insan doğruluğu testi değildir; küçük zamanlama/etiket farkları kalır.
Model hash'i, sabit parametreler ve toplu sayımlar özel
`outputs/2026-09-13-turkish-evaluation/source-alignment-audit.json` dosyasındadır.

Tekrar hazırlamak için depo kökünde standart Python ile yalnız gerekli
dosyaları indirin; mevcut doğrulanmış dosyalar yeniden kullanılacaktır:

```text
python scripts/prepare-turkish-meeting-evaluation.py --download
python scripts/prepare-turkish-meeting-evaluation.py --verify
```

PyAV kurulu, önceden hazırlanmış yerel ortamda aşağıdaki adım ağ gerektirmez:

```text
python scripts/prepare-turkish-meeting-evaluation.py --prepare
```

Windows denemesinde mevcut `voiceup-inference-meeting:local` imajı,
`--network none --pull never` ile başlatıldı ve yalnız çalışma dizini açık
bind mount olarak verildi; çalışan model servisi yeniden başlatılmadı.
Yeni paket veya model indirilmedi. Ham dosyalar
`data/turkish/real-turnturk/<revision>/`, WAV ve `protocol.json` ise
`outputs/2026-09-13-turkish-evaluation/fixtures/` altındadır. `--data-root` ve
`--output` başka yerel konum seçebilir. Var olan farklı içerik üzerine
yazılmaz; aynı çıktı yeniden üretildiğinde aynı içerik kabul edilir.

Kaynak manifest SHA-256:
`02c9494ad9137d642258f7cc3a4720b4f3821b3fc2368d22699d33e08da6ea4b`.
İlk hazırlanan protokol SHA-256:
`483e4810b3cd4559f9f00ce232deb12974e483be280e012f6117324911e7414c`.
Bu araştırma/hazırlama model eğitimi veya doğruluk artışı kanıtı değildir;
gerçek yerel model koşumu ve test kanıtı 009 kapsamındaki ayrı raporlardan
izlenir. Güncel skorun tek kayıt yeri kök [results.md](../results.md) dosyasıdır.
