# Bağlamsal sözcük kontrolü — 13 Eylül 2026

Tamamlanmış toplantı satırındaki **Bağlama göre kontrol et** eylemi, komşu
konuşmalarla yerel `qwen3.5:27b` modelinden küçük sözcük önerileri ister.
Orijinal metin, zamanlar ve konuşmacı hafızası değişmez; sonuç geçici bir
önizlemedir. Mevcut Windows kurulumunda özellik açıktır. Başka kurulumlarda
[yerel model doğrulama yardımcısı](../../TEXT_REVIEW_RUNTIME.md) kullanılır.

| Kanıt | Sonuç |
|---|---|
| [Model deneyi](model-report.md), [deney günlüğü](../../../results.md) | 59 tamamlanmış eşlenmiş istek; 40 farklı örnek, tekrarlar bağımsız sayılmadı |
| Gerçek Türkçe veri | MediaSpeech/FLEURS'tan 24 klip, 532 referans kelime; kelime hata oranı %6,77 → %6,77 |
| Kontrollü geliştirme | Son yönergede 16 örneğin kelime hatası 4 → 2; 12 temiz örnek korundu, hatalı bir satırda gereksiz kelime değişikliği de gözlendi |
| [Tam kalite kapısı](quality-handoff-report.md) | 967 başarılı test; 780 backend + 187 frontend |
| [Normal rol HTTP](live-http-report.md) | 30 gerçek istek, iki hesap/tenant, iki model yanıtı; kaynak ve iş verileri değişmedi |
| [Gerçek arayüz](browser-report.md) | TR/EN, iki genişlik; dört işlevsel varyant başarılı |
| [Uzun yanıt](runtime-timeout-report.md) | Yerel ve Spark proxy fikstürü 65 saniyelik yanıtı iletti |

Bu sonuçlar genel bir doğruluk artışını kanıtlamıyor; otomatik kalıcı düzeltme
açılmadı. RTX 4060'ta son bellek bırakma ayarıyla yeniden model yüklenen iki
kontrollü istek yaklaşık 33–35 saniye sürdü. Model yanıt sonunda bellekten
çıkar; eşzamanlı ağır ses ve metin kapasitesi ölçülmedi.

Uygulama katmanlarının otomatik kapısı ve seçili işlevlerin gerçek HTTP/tarayıcı
gözlemleri mevcut. Güvenlik kapısı eksik `gitleaks` nedeniyle tamamlanamadı;
bu yüzden bütün güvenlik kontrolleri geçmiş veya koşulsuz L1/L2 tamamlanmış
iddiası yok. Dar ekran görsel yakalama, diğer canlı sonuç dalları, headless
senaryo yürütümü, Spark/Apple, canlı Kubernetes ve L3 kullanıcı kabulü açık
kanıt sınırlarıdır. Ayrıntıları ilgili koşum raporları taşır.

Üretilmiş OpenAPI/tipler, TR/EN rehberler ve kalıcı tarayıcı senaryosu güncel.
Şema veya migration eklenmedi; ASR/ses kimlik modelleri değiştirilmedi.
Özel transkript/model cevapları ve hesap bilgileri Git dışındaki `outputs/`
alanında kaldı. Değişiklikler commit edilmedi veya yayımlanmadı.

Kaynak: [Accepted PRD](../../../specs/speaker-identity/PRDs/012-contextual-transcript-review/PRD.md),
[görevler](../../../specs/speaker-identity/PRDs/012-contextual-transcript-review/tasks.md).
