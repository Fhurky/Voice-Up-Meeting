# Koşum raporu — 2026-09-11 · Bağımsız ses kanıtıyla kaynak ayrımını koruma

1. Sonuç: Decision 23 düzeltmesi dar otomatik sınırları ve sabit model çıktılarının yeniden oynatılmasını geçti — birim 110 başarılı / PostgreSQL 121 başarılı / yeniden oynatma 6 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`; yerel Windows/Python 3.13 birim/statikler ve mevcut Linux arka uç üzerinden ayrı, migrasyon uygulanmış PostgreSQL `_test` veritabanları kullanıldı.

   | Koşum | Dosya/kapsam | Sonuç |
   |---|---|---|
   | İlk birim | Yardımcı eklenmeden `test_meeting_native_exclusions.py` | 1 toplama hatası |
   | İlk PostgreSQL | Üretim bağlaması eklenmeden yeni sözleşmeler | 9 başarısız / 3 başarılı; 8 davranış eksiği, 1 geçersiz kaynak fikstürü |
   | İlk bağlama | Yeni ayrım ve mevcut izleme/hafıza/temizlik sözleşmeleri | 119 başarılı / 0 atlanan |
   | Ek bağlam kusuru | Eşlenen, yalnız bağlamda bulunan kişi için yeni ayrım kanıtı | 1 başarısız; eksik kanıt doğrulandı |
   | Son birim | `test_meeting_native_exclusions.py`, `test_meeting_centroid.py`, `test_meeting_identity.py`, `test_meeting_memory_trace.py`, `test_speaker_identity.py` | 20 yeni + 90 mevcut = 110 başarılı |
   | Son PostgreSQL | `test_meeting_native_exclusions.py`, `test_meeting_tracking.py`, `test_meeting_candidates.py`, `test_meeting_centroid.py`, `test_meeting_memory.py`, `test_meeting_context_memory.py`, `test_meeting_memory_trace.py`, `test_meeting_cleanup.py` | 21 yeni + 100 mevcut = 121 başarılı |
   | Son üretim yeniden oynatması | V8 A/B/C/D, long3600 ve elli kişilik A; 24 gerçek sağlayıcı checkpoint'i | 6 başarılı; tüm native eşlemeler ve kaynak ölçümleri sabit adayla aynı |
   | Statikler | Değişen beş dosyada Ruff/Black/isort; bütün arka uçta Mypy; dar `git diff --check` | Başarılı; Mypy 80 kaynak |

   Test komutu `pytest <tablodaki dosyalar> -q --tb=short`; PostgreSQL koşumlarında mevcut `scripts/stack.sh` ve `scripts/db.sh` ile `RUN_POSTGRES_INTEGRATION=1` kullanıldı. Ham XML/metin belgeleri `outputs/2026-09-11-resultant-correctness/native-*` altında; [makine özeti](native-exclusions-results.json) kaynak ve kanıt karmalarını içerir. Yeniden oynatma imza kısıtlı bellek adaptöründe gerçek `MeetingChunkPersistence` gövdesini ve PostgreSQL okumasına karşılık gelen float32 vektör tipini kullanır; veritabanı veya model çağrısı yapmaz.
3. Maddeler:
   **KUSUR**
   M1 Aynı parçada ayrılan iki native ses mevcut global merkeze birleşebiliyordu; her ikisinin kullanılabilir ECAPA192 benzerliği etkin yeni-kişi eşiğinin altındaysa kazanan engellenir ve karşılıklı kaynak kanıtı saklanır (DÜZELTİLDİ, `meeting_native_exclusions.py`, `meeting_chunks.py`).
   M2 Ayrı global kişilerin ardışık konuşması tek kalıcı profile bağlanabiliyordu; doğrulanan ayrım son atamada da denetlenir, iki bağ kaldırılır ve mevcut profil/örnek değişmez (DÜZELTİLDİ, `meeting_memory.py` ve gerçek PostgreSQL/HTTP testi).
   M3 Önceki parçanın bağlamında eşlenen mevcut kişi yeni ayrım kanıtını kaybediyordu; kanıt saklanır, kaynak süreleri/vektörler/toplam ağırlıklar aynen kalır. Eşlenmeyen bağlam kişisi için yeni satır oluşturulmaz (DÜZELTİLDİ, ek başarısız/başarılı test).
   **TUZAK**
   M4 Koşulsuz native etiket ayrımı reddedildi: V8 A 5→11, C 6→8 kişiye bölünüyordu. Kabul edilen koşullu aday sonuç görülmeden sabitlendi; eşik taraması yapılmadı ve `self.policy.new_threshold` kullanıldı.
   M5 Bütün adaylar sıralanır; engellenen kazanan yerine daha zayıf ikinci adaya atama yapılmaz. Zaman örtüşmesinde eski `overlapping_identity_conflict`, yalnız kaynak ayrımında `inconsistent_audio` korunur.
   M6 Eski eksik kanıt boş kalır; mevcut bozuk, silinmiş, başka tenant'a ait, kaynak değiştirmiş veya asimetrik kanıt `model_mismatch` olur. Geçerli karşılıklı belgenin çıkarım sırasında değişmesi de fingerprint ile durdurulur.
   **GÖZLEM**
   M7 Kritik parçadaki iki ayrı etiketin ECAPA192 kosinüsü `0.4330803508`, ham WeSpeaker256 kosinüsü `0.5567067471` idi; ikinci değer tarihsel global kazanan/fark skoru değildir. Asıl karışık örnek ve 37 profillik başarısız hafıza korundu.
   M8 Koşullu ve son üretim eşlemelerinde V8 A/B/C/D 5/5/6/6, long3600 5 kaldı; elli kişilik A 51→52 oldu. Son üretimde 533 karşılıklı ilişki kanıtının tamamı gerçek sağlayıcı checkpoint'lerindeki kullanılabilir vektörlerle doğrulandı.
   M9 Kritik iki kaynak grubunun sahip olunan süreleri 30.8980625 ve 39.825 saniye, kaynak payları %100 ve %99.957627 oldu; bunlar saklanan son ses örneğinin saflığı değildir. Elli kişilik kaynakta %90 altı baskın kaynak payı olan grup 2→1 kaldı.
   M10 Ayrı saf model yardımcıları, süre/norm koruması ve `fuse_populations` gövdesi korundu; birleşik karar gövdesi `a096cf8` ile soyut sözdizim ağacı düzeyinde aynı. Genel API özel etiket veya ayrım belgesi döndürmez.
   **AÇIK**
   M11 Bu dar L1 kanıtı yeni ses modeli çalıştırmaz. Boş hafızada gerçek elli kişi ve dönüş toplantısı, her son örneğin saflığı, tam kalite kapısı ve güvenlik taraması bu raporda geçmiş sayılmaz; ana koşumun ayrı kanıtları gerekir.
   M12 Bağımsız ikinci-model kanıtı yoksa kısıt kurulmaz; native model veya merkez zinciri hatalarının tümü çözülmüş değildir. Uzun kaydın kaynak kişi referansı sabit iki protokolde bulunmadığından yalnız eşleme ve süre karşılaştırıldı.
   **YAN-ETKİ**
   M13 Özel `props.native_exclusions`, kaynak checkpoint'inin sürümlü ve sınırlı türetilmiş önbelleğidir; en fazla 999 `meeting_speaker_id` karşı kaydı içerir. Ayrı ilişki yaşam döngüsü, SQL JSON join'i, şema veya genel API değişikliği yoktur; aynı transaction içinde tenant/karşılıklılık doğrulanır ve sonuç temizliğinde kaldırılır.
   M14 İlk kaynak-bağlam fikstürünün doğrulanmış aralıkları kendi konuşma dönüşlerine uymuyordu; aralık/süre/pencere sayısı düzeltilerek gerçek sözleşme kullanıldı. Geçici veritabanları her koşum sonunda kaldırıldı; ana uygulama/işçi yeniden başlatılmadı.
