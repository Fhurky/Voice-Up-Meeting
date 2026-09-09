# Ürün dokümantasyonu

Ürüne özgü, son kullanıcıya açık dokümantasyonu burada tutun. Mühendislik kuralları `rules/`, kabul
edilmiş gereksinimler ile teslim plan/task belgeleri `specs/<domain>/PRDs/` altında kalır. Bu
kaynakları ikinci bir sözleşme olarak kopyalamayın.

Önerilen yapı:

- `README.md`: hedef kitle, ürün amacı ve navigasyon;
- `hizli-baslangic.md`: ilk giriş ve en küçük faydalı kullanıcı yolculuğu;
- `kabiliyetler/`: kabul edilmiş iş kabiliyetine göre davranış;
- `operasyon/`: kullanıcıyı etkileyen destek ve kurtarma işlemleri;
- `surum-notlari/`: kullanıcının gözleyebildiği değişiklikler.

Her davranış iddiası kabul edilmiş PRD'ye bağlanır ve ürün kullanıcısının diliyle yazılır. İç secret,
altyapı adresi, ajan transcript'i ve kabul edilmemiş roadmap maddesi burada yer almaz. Ürün iki dil
yayımlıyorsa bu Türkçe ağacı `../en/` ile eşlenik tutun.

Repo çalışma akışı: [spesifikasyonlar](../../specs/README.md). Platform ilk çalıştırma:
[kök README](../../README.md).
