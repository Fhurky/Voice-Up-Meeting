# Koşum raporu — 2026-09-11 · Toplantı ses merkezinin kaynak ağırlığını koruma

1. Sonuç: Decision 19 düzeltmesi dar otomatik denetimleri ve kayıtlı model çıktılarının yeniden oynatılmasını geçti — birim 46 başarılı / PostgreSQL 28 başarılı / yeniden oynatma 5 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`; birim ve statikler yerel Windows/Python 3.13.14, gerçek PostgreSQL testleri mevcut Linux arka uç konteyneri ve yalnız bu koşuma ait geçici `_test` veritabanında çalıştı.

   | Denetim | Gerçek kapsam | Sonuç |
   |---|---|---|
   | İlk başarısız PostgreSQL koşumu | `tests/integration/test_meeting_centroid.py`, üretim bağlaması eklenmeden | 10 başarısız / 0 başarılı |
   | Birim | `tests/unit/test_meeting_centroid.py` + `tests/unit/test_meeting_identity.py` | 46 başarılı / 0 atlanan |
   | Son PostgreSQL | `tests/integration/test_meeting_centroid.py`, `test_meeting_tracking.py`, `test_meeting_candidates.py` | 28 başarılı / 0 atlanan |
   | Kayıtlı gerçek model çıktıları | V8 A/B/C/D ve long3600: 16 işlem adımı, 27 son konuşmacı satırı | 5 karşılaştırma başarılı |
   | Statikler | Değişen 4 kaynak/test dosyasında Ruff, Black, isort; arka uçta Mypy | Başarılı; Mypy 78 kaynak |
   | Çalışma ağacı | `git diff --check` | Başarılı; yalnız mevcut CRLF→LF bildirimi |

   Birim komutu: `.venv/Scripts/python.exe -m pytest tests/unit/test_meeting_centroid.py tests/unit/test_meeting_identity.py -q` (arka uç çalışma dizini). PostgreSQL komutu mevcut `scripts/stack.sh exec -T backend` üzerinden, geçici veritabanı adresi ve `RUN_POSTGRES_INTEGRATION=1` ile `pytest tests/integration/test_meeting_centroid.py tests/integration/test_meeting_tracking.py tests/integration/test_meeting_candidates.py -q --tb=short` oldu.

   İsim, kimlik, metin veya vektör içermeyen [makine özeti](resultant-replay-results.json), kaynak/kod/deneme özeti karmalarını ve 27 satırın sayısal farklarını içerir. Yerel ham test belgeleri `outputs/2026-09-11-resultant-correctness/{unit-green,integration-red,integration-final}.xml`, yeniden oynatma çıktısı aynı dizindeki `replay-results.json` içindedir.
3. Maddeler:
   **KUSUR**
   M1 Normalize edilmiş eski merkezin toplam süreyle tekrar ağırlıklandırılması vektör toplamının büyüklüğünü kaybediyordu; ayrı 192/256 toplam ağırlık ve norm durumu eklendi (DÜZELTİLDİ, `meeting_centroid.py`, `meeting_chunks.py` ve iki yeni test dosyası).
   M2 Eşit ağırlıklı 0°/35°/70° kanıtları eski kodda sıraya göre 34.415099°/35.584901° merkez üretiyor, aynı 92° sorgusu belirsiz/tanınmış oluyordu; iki boyutta yeni merkez 35° ve iki karar da belirsizdir.
   M3 Vektörü bulunmayan ses süresi geçmiş ağırlığı şişirebiliyordu; her model yalnız kendi vektörlü, benzersiz kaynak saniyelerini toplar. Bozuk mevcut durum sessizce sıfırlanmaz, tüm işlem `model_mismatch` ile geri alınır.
   **TUZAK**
   M4 Eski satırın kaybolmuş normu geri getirilemez: ilk gerçek yeni katkıda kayıtlı süre tek başlangıç gözlemi sayılır; `legacy_centroid_seed` kökeni korunur. Eski geçmiş için tam matematiksel yeniden kurma iddiası yoktur.
   M5 PostgreSQL vektörü float32 saklar; her işlem ayrı oturumda okunmuştur. İdeal toplam karşılaştırması için tolerans `2e-7`, durum sınırında bağıl tolerans `1e-6` kullanılır; sıfır katkıda mevcut vektör ve durum aynen korunur.
   M6 İlk XML yolu Git Bash tarafından Windows yoluna çevrildi; yalnız bu koşumun tek dosyası doğrulanıp yok sayılan çıktı dizinine taşındı. Son koşumda `/tmp` ve `--junitxml=` dönüşümü kapatıldı.
   **GÖZLEM**
   M7 Eski `a096cf8` kodu gerçek kayıtlardaki 27 merkezi en fazla `2.2663e-8` L2 farkıyla yeniden üretti; eski/yeni 16 kaynak aralığı eşlemesi ve 175 sabit politika sorgusu aynı kaldı.
   M8 A/B/C/D konuşmacı sayıları 5/5/6/6, 3.600 saniyelik kayıt 12 parçada 5 olarak korundu. En büyük yeni/eski merkez farkı 192 boyutta `0.0318541`, 256 boyutta `0.0171293`; fark eşleme değişikliği değildir.
   M9 Birim testi her iki boyutta altı kanıt sırasını bağımsız ağırlıklı toplamla karşılaştırır; gerçek 601 saniyelik yükleme/işçi testi üç işlemde 300/300/1 saniyeyi sayar ve her seferinde yeni işçi kullanır.
   **AÇIK**
   M10 Bu dar L1 kanıtı yeni model çalıştırmaz; metin ve kalıcı profil eşleşmesi tekrar hesaplanmamıştır. 50 bağımsız kişi, yeni canlı uygulama koşumu, tam kalite kapısı ve güvenlik taraması bu raporun kapsamındaki kanıt değildir.
   M11 Hareketli merkez üzerinden zincirleme birleşme hâlâ sıraya bağlı olabilir: 0°/55°/80° bir, 80°/0°/55° iki iz verebilir. Sonuç normunu korumak bu ayrı gruplama sorununu çözmüş sayılmaz.
   M12 192/256 birleşik kararın çekimserliği ve kalıcı belirsizlik işareti kabul edilmiş korumalardır; eşikler veya işaret temizliği bağımsız yanlış kabul/bölünme kanıtı olmadan değiştirilmedi.
   **YAN-ETKİ**
   M13 Bir saf alan yardımcısı, mevcut işçiye bağlama ve iki test dosyası eklendi; özel `props` alanında sürümlü durum tutulur. Şema, API, model kimliği, eşikler ve kalıcı profil örnekleri değiştirilmedi.
   M14 Orijinal kayıtlar salt okunur işlemle alındı; model hesaplaması 0, ses/metin dışarı aktarımı 0. Yeniden oynatma yalnız geçici test veritabanına yazdı ve sonunda o veritabanı silindi.
