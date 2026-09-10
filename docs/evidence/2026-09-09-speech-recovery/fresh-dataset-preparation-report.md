# Koşum raporu — 2026-09-09 · Bağımsız açık veri havuzunun hazırlanması

1. Sonuç: Windows hazırlama kontrolleri geçti ve 302 kayıt model çıkarımı yapılmadan hazırlandı — birim 33 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`, Windows / Python 3.13; aşağıdaki hazırlama ve dosya doğrulamaları gözlendi.

   | Kontrol | Gözlenen sonuç | Kanıt |
   | --- | --- | --- |
   | `tests/test_public_speaker_dataset.py` | 33 başarılı, 0 başarısız, 0 atlanan | [Windows JUnit](fresh-dataset-windows-tests.xml), [JUnit'ten türetilmiş özet](fresh-dataset-windows-tests.txt) |
   | `prepare-public-speaker-dataset.py --protocol fresh-holdout-v2 --exclude-root data/public-speaker-evaluation --download` | Çıkış 0; 50 kayıt adayı, 20 bilinmeyen kişi, 302 WAV | [Yakalanmış hazırlama çıktısı](fresh-dataset-preparation.txt), [anonim hazırlık kaydı](fresh-dataset-readiness.json) |
   | Son kaynak koduyla deterministik yeniden üretim | 302 PCM dosyası ve manifest baytları birebir aynı | [Yeniden üretim ve kaynak özetleri](fresh-dataset-readiness.json) |
   | Gerçek dosyalarla `evaluate-public-speakers.py::validate_manifest` | Boyut/hash, roller, kaynak tekrarları, bölüm ayrımı ve 5/10/20/50 galeri ön kontrolü geçti | [Hazırlık kaydı](fresh-dataset-readiness.json) |
   | Eski verinin korunması | 2 manifestin SHA-256 değeri ve 604 kaydın kişi/rol/bölüm/kaynak seçimi değişmedi | [Koruma gözlemleri](fresh-dataset-readiness.json) |

   Kaynak, [OpenSLR SLR12](https://www.openslr.org/12) kapsamındaki temiz İngilizce okuma verisidir ve [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) lisansındadır. Atıf: Vassil Panayotov, Guoguo Chen, Daniel Povey ve Sanjeev Khudanpur, “LibriSpeech: an ASR corpus based on public domain audio books”, ICASSP 2015. Lisans ve kaynak belgeleri indirilen veriyle korundu.

   [Resmi train-clean-100 arşivi](https://www.openslr.org/resources/12/train-clean-100.tar.gz) tam **6.387.309.499 bayt** olarak alındı. [Resmi MD5](https://www.openslr.org/resources/12/md5sum.txt) `2a93770f6d5c6c964bc36631d331a522` doğrulandı; yerel arşiv SHA-256 değeri `d4ddd1d5a6ab303066f14971d768ee43278a5f2a0aa43dc716b0e64ecbbbf6e2`. Açılan 28.539 FLAC dahil 29.129 normal dosya toplam **6.618.476.609 bayt** tuttu. Yeni arşiv için 12 GiB / 60.000 üye, dosya başına 20 MiB; aktarım için 30 saniye ağ zaman aşımı ve 1.800 saniye toplam süre sınırı korundu. Eski arşivlerin 2 GiB / 20.000 üye sınırları değişmedi.

3. Maddeler:
   **KUSUR**
   M1 Yeni protokol/dışlama davranışları önce beklenen kırmızı testlerle gösterildi, ardından düzeltildi; son Windows paketinde 33 test geçti (`tests/test_public_speaker_dataset.py`).
   **TUZAK**
   M2 Kaynakta 251 kişi vardır; 209 kişi bölüm/süre bakımından kayıt adayı, 251 kişi bilinmeyen sorgular için uygundur. Sabit `voiceup-librispeech-open-set-v2` tohumu 50 + 20 kişiyi model puanı kullanmadan seçer; bunlar başarılı uygulama kaydı veya tanıma sayıları değildir.
   M3 Kayıt ve sorgu bölümleri ayrıdır; yeni kişinin bilinmeyen/kayıt/geri dönüş rolleri üç ayrı bölüm kullanır. Aynı kişiye ait sorgular ilişkili olabilir; yalnız temiz kaynak içeren bu havuz eski temiz/zor karışımıyla doğrudan iyileşme yüzdesi olarak karşılaştırılmaz.
   M4 Windows pytest standart çıktısı ayrı dosyaya kaydedilmemiştir; metin özeti JUnit'ten türetilmiş olarak açıkça etiketlendi. Hazırlama konsolu gerçek yakalanmış çıktıdır; yeni test veya çıkarım çalıştırılmadı.
   **GÖZLEM**
   M5 Önceki dört bölümdeki 146 kişinin tümü dışlandı; yeni seçimin kesişimi sıfırdır. Dışlama kimlikleri yayımlanmadı; yalnız listenin SHA-256 özeti korundu. 302 kayıt 605 tekrarsız kaynak ses parçasından üretildi.
   M6 [Linux birleşik kanıtı](reference-and-evaluation.xml) 349 başarılı ve yalnız `test_windows_junction_cannot_redirect_output` için 1 platform atlaması içerir; aynı vaka [Windows'ta geçti](fresh-dataset-windows-tests.xml).
   M7 Windows'taki 33 vakanın tamamı Linux'taki 350 vakanın alt kümesidir: bu iki kanıtın birleşimi **350 benzersiz başarılı vaka** sağlar. Windows 33 sonucu toplam sayıya ikinci kez eklenmez; yalnız platform atlamasını kapatır.
   **AÇIK**
   M8 Bu hazırlık anında yeni havuzda uygulama çıkarımı yapılmadı; sonraki aday ölçümleri ayrı kanıtlardır. Türkçe toplantı doğruluğu, bağımsız mikrofon/oturumlar ve model eğitimindeki kişi düzeyinde ayrıklık bu veriyle doğrulanmış sayılmaz.
   **YAN-ETKİ**
   M9 Hazırlayıcı, testleri ve protokol belgesi genişletildi; yeni veri ayrı, yok sayılan dizinde tutuldu. Bu kanıt kapatma adımı yalnız anonim JSON/rapor, makine adı çıkarılmış JUnit ve etiketli çıktı belgelerini ekledi; ses, kişi satırı veya uygulama verisi yayımlanmadı.
