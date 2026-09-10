# Yaklaşık 50 kişide yüksek konuşmacı tanıma doğruluğu

Tarih: 10 Eylül 2026. Durum: araştırma ve deney önerisi; yeni model/kalite politikası
henüz seçilmedi veya üretime alınmadı. [Decision 11](../specs/speaker-identity/PRDs/001-local-speaker-pilot/PRD.md)
50 kişi kotasını kaldırır; bu belge doğruluk çalışmasının adaylarını karşılaştırır.
Sabit teknoloji profili `kt-vibecoding-python-web-v2` korunur.

## Mevcut model ve ölçülmüş darboğaz

Uygulamanın modeli `speechbrain/spkrec-ecapa-voxceleb` ECAPA-TDNN, revision
`0f99f2d0ebe89ac095bcc5903c4dd8f72b367286`, 192 boyutlu normalize ses vektörüdür.
Profiller ve doğrulanmış örnekleri PostgreSQL'de tutulur; yeni kişi eklemek model
ağırlıklarını yeniden eğitmez. Karar eşikleri 0,55 / 0,45 / 0,10'dur. Model kartı
VoxCeleb1+2 eğitimini ve Apache-2.0 lisansını bildirir; kendi iki-kayıt doğrulama
sonucu bizim 50 kişilik açık küme doğruluğumuz değildir. [Resmî model kartı](https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb).

10 Eylül canlı `/ready` yanıtı aynı model/revision, 192 boyut ve `cuda:0` döndürdü.
İlk kontrolde durmuş SSH tüneli nedeniyle 502 vardı; mevcut `spark-tunnel.ps1 -Action Start`
ile tünel yeniden hazırlandı. Model veya ağırlık değişmedi.

| Ölçü | Son temiz İngilizce grup | Kalibrasyon |
| --- | ---: | ---: |
| Başarılı ilk profil | 40/50 | 40/50 |
| Bütün planlı bilinen sorgularda doğru kimlik | 116/150 (%77,33) | 111/150 (%74,00) |
| Profili oluşan kişilerde koşullu doğru tanıma | 116/120 (%96,67) | 111/120 (%92,50) |
| Profili oluşmayan kişilerin kayıp sorguları | 30/34 kayıp (%88,24) | 30/39 kayıp (%76,92) |
| Kayıtlı kişilerde kalan kayıplar | 4 tutarlılık reddi | 9 tutarlılık reddi |

Kaynak: değiştirilmeyen [önceki ölçüler](../docs/evidence/2026-09-09-speaker-metrics/README.md)
ve bu turdaki [anonim ayrıştırma](../docs/evidence/2026-09-10-speaker-quality-target/diagnosis-report.md).
İlk on profil reddinin tamamı `inconsistent_audio` nedenlidir. Temiz gruptaki 22
`unknown` ve iki `ambiguous` sonucu, profili oluşmayan on kişidendir. Seçilmiş
kayıtlı alt grubun %96,67 oranı genel %77,33 yerine kullanılamaz; başarı sorunu
yalnız yanlış kimlik vermek değil, doğru kişiyi hiç kaydedememektir.

Sorgu kalite retleri değişmezse yalnız ilk kayıtları onarmanın temiz gruptaki
matematiksel tavanı 140/150=%93,33 olur; bu kazanım ölçülmedi. Dolayısıyla hem
kayıt hem sorgu tutarlılık filtresini araştırmak gerekir. Önceki karışık kişi
negatiflerinde gevşek birleştirme yanlış kabulleri artırmıştı; filtreyi kaldırmak
veya benzerlik eşiğini körlemesine düşürmek kabul edilebilir bir iyileştirme değildir.

## Önerilen deney sırası

1. **İlk kaydı düzeltme deneyi:** yalnız kalibrasyondaki on başarısız kişiye,
   sorgulardan ayrı kaynak/bölümden ikişer alternatif temiz kayıt hazırlamak;
   mevcut modeli ve kimlik eşiklerini sabit tutarak tek-kayıt temelini ve en çok
   üç açık kayıt denemesini karşılaştırmak. İlk deneme ve toplam kayıt kapsamı,
   bütün 150 bilinen/100 bilinmeyen sorgu ve ek kayıt maliyeti ayrı raporlanır.
2. **Tutarlılık filtresini inceleme:** aynı kişide farklı fonetik içerik, kısa
   konuşma blokları ve ses düzeyi değişimini gerçek iki kişi karışımı/üst üste
   konuşmadan ayıran pencere kanıtını incelemek. Yeni kural seçilmeden aynı negatif
   takımda yanlış kabul artmadığı doğrulanır; öneri doğrudan üretim eşiği değişikliği değildir.
3. **Aynı protokolde model karşılaştırma:** mevcut ECAPA, ReDimNet2-B6 ve
   WeSpeaker ResNet293-LM'yi aynı kaynaklardan, model başına kendi ön işlemesi ve
   yalnız kalibrasyonda seçilen eşiklerle karşılaştırmak. Önce kalite/kimlik
   sonuçları; sonra kısa ses, mikrofon/oturum değişimi ve işleme gecikmesi incelenir.
4. **Profil çeşitliliği:** Türkçe gerçek kullanımda kişi başına farklı oturumlarda
   2–3 temiz 20–30 saniyelik örneği tek örnekle karşılaştırmak; daha fazla örneğin
   yararı ölçülür, kendiliğinden garanti sayılmaz. Merkez vektör ve çoklu örnek
   eşleştirmesi ayrı deneylerdir; yeni örnek yanlış kişiye bağlanmamalıdır.
5. **Toplantı koşulları:** 50 gerçekten kayıtlı kişi ve ayrıca kayıt dışı kişilerle,
   farklı gün/mikrofon ve Türkçe seslerde kör test yapmak. Toplam kimlik havuzu
   100/200 olduğunda ve toplantıda bunların 50'si bulunduğunda iki sayı ayrı tutulur.
   Katılımcı listesi kullanılacaksa bilinmeyen kişiyi en yakın kayıtlıya zorla
   bağlamama davranışı korunur. Uzun kaydı konuşmacılara ayırma ve zaman boyunca
   kimlik sürekliliği 002/003 yetenekleriyle ayrıca doğrulanır.

Bu turda incelenen temiz grup artık model seçimi için yeni kör veri değildir.
Son kabul için yeni, ayrık ve uygun izinli kayıt gerekir. Yeni kişinin kayıt/dönüş
deneyi ana galeri puanına eklenmez; başarısız kayıtlar ana paydalardan çıkarılmaz.

## Model adayları: yayımlanmış sonuç ile yerel kanıtın ayrımı

EER, iki kayıt aynı kişiden mi sorusunda yanlış kabul ve yanlış ret oranlarının
eşitlendiği hata oranıdır; `100 − EER`, 50 kişi arasından kimlik bulma başarısı değildir.
Kartlar farklı eğitim/skor işleme koşulları kullanır; aşağıdaki sayılar aday
seçmeye yardımcı olur, tarafımızdan yapılmış adil karşılaştırma değildir.

| Aday | Yayımlanmış bilgi | Bu proje için değerlendirme |
| --- | --- | --- |
| ReDimNet2-B6 | Resmî VoxCeleb2 sürümü Vox1-O'da %0,29 EER; MIT, hazır ağırlıklar. [Kaynak](https://github.com/PalabraAI/redimnet2). | İlk yeni adaylardan biri; checkpoint/hash, sonlu vektör boyutu, ARM64 çalışması ve mevcut veriden ayrıklık paket kabulünde doğrulanmalı. 2026 sürümüdür; yayımlanmış dosyalar [sürüm kaydında](https://github.com/PalabraAI/redimnet2/releases) tarihlenir. |
| WeSpeaker ResNet293-LM | VoxCeleb2 Dev eğitimi, 256 boyut, Vox1-O-clean EER %0,532; ek skor normalizasyonuyla %0,447; CC-BY-4.0. [Kart](https://huggingface.co/Wespeaker/wespeaker-voxceleb-resnet293-LM). | Olgun karşılaştırma adayı; 256 boyut mevcut `VECTOR(192)` ile aynı alan değildir. |
| NVIDIA TitaNet-Large | Resmî kart %0,66 EER ve CC-BY-4.0 bildirir; eğitim kaynaklarında LibriSpeech vardır. [Kart](https://huggingface.co/nvidia/speakerverification_en_titanet_large). | Alternatif aday; mevcut LibriSpeech değerlendirmesi eğitim ayrıklığı doğrulanmadan bu model için kör test sayılamaz. NeMo bağımlılık uyumu ayrıca gerekir. |
| WavLM / W2V-BERT tabanlı doğrulayıcılar | WavLM Large yayımlanmış sonuçları, hazır `wavlm-base-plus-sv` ağırlığıyla aynı model değildir. [Resmî çalışma](https://github.com/microsoft/unilm/blob/master/wavlm/README.md), [hazır kart](https://huggingface.co/microsoft/wavlm-base-plus-sv). WeSpeaker güncel W2V-BERT karşılaştırmaları yayımlar. [Tarif](https://github.com/wenet-e2e/wespeaker/blob/master/examples/voxceleb/v2/README.md). | Daha karmaşık ikinci karşılaştırma hattı; hazır WavLM-SV 512 boyutludur, Libri-Light ön eğitimi ve kartın bağladığı [CC-BY-SA-3.0 lisansı](https://github.com/microsoft/UniSpeech/blob/main/LICENSE) ayrıca kaydedilmeli. Daha büyük ağ tek başına daha iyi Türkçe sonuç garantisi değildir. |

Yeni model vektörleri aynı boyutta olsalar bile eski ECAPA vektörleriyle
karşılaştırılamaz. Aday deneyi mevcut profilleri değiştirmeden ayrı model
popülasyonunda yürür. Üretim geçişi seçilirse tipli adaptör, model revision/hash
kabulü, gerekiyorsa eklemeli şema migrasyonu ve yeniden vektör üretimi gerekir.
Spark'ın kapasitesi birden çok adayı denemeyi kolaylaştırır; ARM64/Python/CUDA
uyumluluğu ve gecikme ölçümü yapılmadan hazır çalışır iddiası verilmez.

## Ölçülebilir başarı hedefi önerisi

PRD'nin atıf yaptığı `docs/EVALUATION_PLAN.md` içindeki 50 kişilik mühendislik
hedefi, uygun tek konuşmacılı sorgularda yanlış kabul ≤%1 iken bilinen doğru
tanıma ≥%95'tir; henüz sağlanmadı.
Kusursuza yakın kullanım için önerilen daha ileri hedefler, kayıt protokolü ve
temsilî veri sabitlendikten sonra ayrıca kabul ölçütüne dönüştürülmelidir:

| Ölçü | Öneri, henüz gerçekleşmiş veya kabul edilmiş garanti değil |
| --- | --- |
| Kimlik precision | ≥%99,5 |
| Bütün planlı bilinen sorgularda recall | ≥%98 |
| Kimlik macro F1 | ≥%98; kişiler arası dağılım ve en zayıf kişiler ayrıca görünür |
| Bilinmeyende yanlış kimlik kabulü | ≤%0,5; başarısız/kararsız sonuçlar gizlenmeden |
| Profil oluşturma | İlk deneme kapsamı ayrı; tanımlı en çok üç kayıt denemesi sonunda ≥%98 |

VoiceUp Score özet olarak kalır; düşük yanlış kabul, yüksek kayıt kapsamı ve
yüksek recall ayrı ayrı gerekli olduğundan yalnız tek skora bakılarak kabul
verilmez. Güven aralıkları ve konuşmacı/oturum bağımlılığı raporlanır. 100
bilinmeyen sorguda sıfır yanlış kabul çok küçük hata oranını kanıtlamaz; örnek
sayısı ve farklı kişi/oturum sayısı hedefe göre artırılmalıdır.
