# Görevler — Kamuya açık kıyaslarla doğruluk ölçümü

- [x] T01 AMI ses/referans lisans kaydı, sabit manifest ve `prepare-ami-evaluation.py` (testlerle).
- [x] T02 `GET /meetings/{public_id}/speaker-turns`; backend testleri, OpenAPI ve frontend tipleri.
- [x] T03 `run-ami-evaluation.py`: deney tenant'ı, Decision 4 protokolü, devam ettirme, DER/JER ve kimlik ölçütleri.
- [x] T04 AMI taban çizgisi: iki ses koşulu × iki rotasyon; `results.md` kaydı.
- [x] T05 Türkçe FLEURS/MediaSpeech taban çizgisinin bu çalışma profilinde yeniden koşumu.
- [ ] T06 Tam kalite kapısı ve koşum raporu.

29 Ekim 2026 ara kanıtı: sabit commit'teki 34 dev/test toplantısı iki ses koşuluyla
indirildi ve manifestteki boyut/SHA-256 değerleriyle doğrulandı. Hazırlayıcı, koşucu ve
deney günlüğü ve Türkçe değerlendirici testleri 173/173 (2 sembolik bağlantı testi
Windows'ta atlanır); 30 Ekim 2026 tam kapısında `speaker-turns` dahil backend 895/895
gerçek PostgreSQL ile geçti. İki toplantılık gerçek uçtan uca deneme (`eval-ami-smoke2`) API, puanlama ve devam
ettirme akışını doğruladı. İlk taban çizgisi denemesi array1 rotasyon 1'in 9.
toplantısında (`IS1009a`) durdu: 68 AMI dosyasının 17'sinde RIFF parçalarına ait olmayan
fazladan bir bayt var ve API `invalid_audio` döndürüyor. Hazırlayıcı artık ham dosyayı
`raw/` altında doğrulayıp ürüne örnekleri bayt bayt aynı kanonik WAV gönderiyor
(Requirement 1); 68 kopyanın tamamı sunucu kuralını geçti, ham hash'ler değişmedi.
Önceki kısmi koşumlar (`eval-ami-array1-r1/r2`) sonuç olarak kullanılmaz; taban
çizgisi `eval-ami2-*` tenant'larında baştan, JER ile koşuluyor.

30 Ekim 2026 T04 kanıtı: dört koşum da 34/34 toplantıyla tamamlandı ve `results.md`'ye
`eval-ami2-{array1,headset}-r{1,2}` adlarıyla, `x86_64-cu126` profiliyle kaydedildi.
Collar 0 DER array1 %44,57, headset %39,49; iki rotasyon aynı ses koşulunda aynı DER'i
verdi. Yanlış kişi 0/95, yanlış kabul 0/270. Tanıma oranı array1 %73,33 ve %64,29,
headset %82,61 ve %68,97. Headset rotasyon 1 kullanıcı duraklatmasından sonra durum
dosyasından sürdürüldü. Açık bulgu: Community-1 model kartı collar 0 ile AMI SDM %19,9,
IHM %17,0 yayımlıyor; ölçülen DER bunun iki katından fazla. Toplantı kümesi ve referans
farkları ayrıştırılmadı, nedeni henüz bilinmiyor. (Neden: [021](../021-meeting-speaker-reconciliation/PRD.md).)

30 Ekim 2026 T05 kanıtı: `x86_64-cu126` üzerinde `results.md` sürüm 2 kayıtları, MediaSpeech 2433/2433
WER %14,03 (önceki `x86_64-cu128` kaydı %14,12), FLEURS 743/743 WER %6,49 (önceki %6,50). Sürüm 1
kayıtları 0 klipte kaldı: Docker belleği (7,35 GB) çalışan konuşma servisiyle birlikte ikinci
Whisper modelini okumaya yetmedi; koşum servis durdurularak yinelendi.
