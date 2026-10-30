# PRD — Gerçek Türkçe toplantı ölçümü

Status: Draft

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [024 — turkish-meeting-measurement](../../roadmap.md)
Profil: `kt-vibecoding-python-web-v2`; şema profili `sqlalchemy-alembic`.
Kaynak (30 Ekim 2026): Kullanıcıyla belirlenen hedeflerde Türkçe toplantı doğruluğunun ölçülmesi birinci
önceliğe alındı.

## Amaç ve önceki durum

Bugünkü Türkçe sonuçlar üç ayrı parçadır: MediaSpeech ve FLEURS toplantı olmayan kliplerde yazıya çevirmeyi
ölçer; Real-TurnTurk iki kişilik görüşmeleri otomatik ve insanca doğrulanmamış etiketlerle ölçer (015, 009);
AMI toplantıları İngilizcedir. Üç veya daha çok kişinin konuştuğu gerçek Türkçe toplantıda, insan etiketine
karşı ölçüm yoktur. Hedef: az sayıda izinli toplantıyla konuşmacı ayırma, yazıya çevirme, "kim ne dedi" ve kişi
tanıma için güvenilir taban çizgisi. Bu PRD ürün davranışını değiştirmez.

## Kararlar

Decision 1: Veri, 3–5 gerçek Türkçe toplantıdır: toplantı başına en az 3 konuşan kişi ve en az 20 dakika. Her
katılımcının ölçüm amaçlı kullanım için yazılı izni gerekir. Kurum verisi yalnız kurum ağında işlenir; ses ve
etiketler depoya girmez, `outputs/` altında özel dosyalardadır. `results.md`'ye yalnız toplu sonuç yazılır.

Decision 2: Etiket biçimi toplantı başına bir CSV dosyasıdır: `start`, `end`, `speaker`, `text`. Süreler saniye,
`speaker` takma addır (örnek `K1`); gerçek ad yazılmaz. Örtüşen konuşmalar ayrı satırdır. Duyulamayan kelime
`[anlaşılmıyor]` olarak yazılır ve metin puanının dışında kalır.

Decision 3: Etiketleme, uygulama çıktısının dışa aktarılmış CSV'sini sesi dinleyerek düzeltme yoluyla yapılır, çünkü
sıfırdan yazmaktan çok daha kısadır. Bu yöntem etiketi uygulamaya yaklaştırabilir; bu yüzden en az bir
toplantının en az 10 dakikası ikinci bir kişi tarafından uygulama çıktısı görülmeden etiketlenir ve iki etiketin
uyumu raporlanır.

Decision 4: Ölçütler: DER ve JER (collar 0 ve ±0,25 sn), kelime hata oranı (`turkish-words-v1`), `cpWER` ("kim ne
dedi" hatası), yanlış kişi, tanıma oranı ve yabancıyı tanıdık sanma. Kişi tanıma için izin veren katılımcılardan 017
mikrofon profili alınır; otomatik kayıt kapalıdır (021 Decision 7). En az bir katılımcı profilsiz bırakılır.

Decision 5: Taban çizgisinden sonra karşılaştırılacak öneri hedefler: DER %20 altı, kelime hatası %15 altı, yanlış kişi
0. 3–5 toplantının bu oranları kesin kanıtlamadığı, güven aralığıyla raporlanır.

## Gereksinimler

Requirement 1: `scripts/` altında etiket doğrulayıcı (biçim, sıralama, süre sınırı, gerçek ad uyarısı) ve CSV'den
RTTM ile metin referansı üreten hazırlayıcı; testleriyle.

Requirement 2: Uygulama sonucunu CSV olarak dışa aktaran değerlendirme aracı; mevcut API ile çalışır.

Requirement 3: `run-ami-evaluation.py` puanlama fonksiyonları ve `score-meeting-transcript.py` yeniden kullanılarak
toplu rapor; ham metin ve kişi eşlemesi özel dosyalarda kalır. Toplu sonuç `results.md`'ye işlenir.

Requirement 4: Kullanım rehberi (`docs/`): izin, kayıt, etiketleme ve koşum adımları.

## Katmanlar

Şema, API, ön yüz, worker, vektör ve Kubernetes: N/A — ürün davranışı değişmez, yalnız değerlendirme araçları ve belge
eklenir. Gözlemlenebilirlik: N/A — ayrı araçlar, yeni sinyal yok.

## Kabul ölçütleri

- [ ] Araç testleri ve tam kalite kapısı geçer.
- [ ] En az 3 etiketli toplantı koşulur; ölçütler güven aralığıyla `results.md`'de.
- [ ] Etiket uyumu raporlanır; özel veri depoya girmez.

Open Question 1 (kapandı, 30 Ekim 2026): Kayıtlar şimdilik bu makinede işlenir; kurum içi işleme kullanıcı tarafından
sonraya bırakıldı. Decision 1'deki kurum ağı koşulu kurum verisi için geçerli kalır.

Open Question 2: Etiketlemeyi kim yapacak? Toplantı süresinin tahminen 3–5 katı insan zamanı gerektirir.
