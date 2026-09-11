# Koşum raporu — 2026-09-11 · Yüklenen toplantıdan konuşmacılı metne ve kalıcı kişi hafızasına yerel teslim

1. Sonuç: Seçilen RTX 4060 ortamındaki kayıt, isim ve hafıza akışı canlı olarak doğrulandı; bütün ürün için kusursuz doğruluk veya yayına hazır güvenlik iddiası yok — birim 1.839 başarılı / tarayıcı 2 başarılı / atlanan 15 yerel, aynı 15 durum ayrı uygun ortamda başarılı; karar bekleyen: yok.
2. Koşulan: Sabit `kt-vibecoding-python-web-v2`; Python 3.13/FastAPI, PostgreSQL 17/SQLAlchemy/Alembic, React 19/Vite 8, Linux x86_64 CUDA ve RTX 4060 Laptop GPU. Kök araştırma/hazırlama araçları ayrıca destekledikleri yerel Python 3.12 ortamında sınandı.

   | Kanıt | Sonuç |
   | --- | --- |
   | [Son tam uygulama kapısı](full-gate-final-report.md) | `scripts/quality-gate.sh all`: 478 backend + 89 frontend başarılı, 0 atlanan; statik kontroller, benzersiz test DB migrasyonu/temizliği, şema geçmişi/drift, OpenAPI/tipler, yönetişim ve chart geçti |
   | [Kök araç paketi](root-tests-final-report.md) | 1.063 yerel başarılı + [ayrı 13 Docker/2 Linux geçişi](../2026-09-10-meeting-delivery/remaining-platform-coverage-report.md) = 1.078 benzersiz test; ilk Windows atlama kaydı korundu |
   | [Model servisi paketi](../2026-09-10-meeting-delivery/secondary-voice-veto-report.md) | 194 otomatik test; bunlar model doğruluk skoru değildir |
   | [Dondurulmuş gerçek A/B/D/C](../2026-09-10-meeting-delivery/frozen-meeting-flow-report.md) | Normal kullanıcı, gerçek HTTP/model/DB: 5 yeni → aynı 5 → kısa altıncı beklemede → yalnız altıncı eklenir; gerçek servis yeniden başlatma ve yinelenen tamamlama geçti |
   | [Gerçek tarayıcı](../2026-09-10-meeting-delivery/meeting-memory-browser-report.md) | İki senaryo: TR/EN aktarım/izin/devam ve gerçek sesle metin/isim/hafıza; gerçek giriş formu, hata ve dış ağ isteği yok |
   | [Kaynak saflığı ve değişmeyen hafıza](v8-source-purity-memory-report.md) | 6/6 yeni ses örneği en az %99 kaynak saflığı; orijinal WAV'dan yeniden hash eşliği. Ek gerçek B toplantısında 5/5 tanıma, altı profil ve altı örnek önce/sonra aynı |
   | [Kullanıcının Türkçe dosyası](../2026-09-10-meeting-delivery/turkish-source-report.md) | 52,629 saniyelik kaynak: bir konuşmacı, metin ve bir profil; elle referans olmadığı için doğruluk skoru yok |
   | [En büyük özel model penceresi](../2026-09-10-meeting-delivery/private310-gpu-report.md) | 310 saniye, 192 kHz/8 kanal kaynak; 119 MB gerçek aktarım/HTTP 200, 35,19 saniye; worker 203,36 MiB, sıcak model servisi 5,47 GiB RAM, bütün GPU tepesi 2.950 MiB |
   | [Bir saatlik gerçek worker işi](long3600-worker-report.md) | 12/12 parça ve 3.600 saniye tamamlandı; beş kişi tanındı, galeri altı kaldı, profil/örnek hashleri aynı. Tamamlanma gözleminin üst sınırı 600,18 saniye; örneklenen worker tepesi 122,90 MiB. Tekrarlı kaynak dayanıklılık ölçüsüdür, bağımsız doğruluk verisi değildir |

3. Maddeler:
   **KUSUR**
   M1 İlk kayıttaki kişi parçalanması ve yetersiz hafıza kanıtı, kaynak zamanında eşleme/doğal örnekler/çift model kontrolüyle giderildi; v3/v4/v5 ve v6 başarısız ölçümleri silinmedi.
   M2 Uzun zaman aralığına yayılan sözcük yanlış kişiye atanıyordu; [29 zaman çizelgesi testi](../2026-09-10-meeting-delivery/sequential-word-report.md) ve değişmeyen gerçek kayıtlar düzeltmeyi korur. Metin belirsiz olarak tutulur.
   M3 [Yeniden başlatmada Nginx adresi](../2026-09-10-meeting-delivery/stack-restart-report.md), [Spark şablon özeti](../2026-09-10-meeting-delivery/spark-reviewed-template-report.md), [Python arşiv uyumu](archive-compatibility-report.md) ve [yerel test motoru](native-startup-helper-report.md) kusurları gerçek başarısızlıklar sonrasında düzeltildi.
   **TUZAK**
   M4 Profil kaydı model ağırlıklarını yeniden eğitmez; model sürümlü ses temsili saklar. Yeni profil için temiz tekil konuşma 20 saniyeyi aşmalı, üç doğal örnek ve kalite/kimlik kontrolleri geçmelidir; eski bilinen profil otomatik genişletilmez.
   M5 %99 örnek saflığı genel tanıma doğruluğu değildir. Kaynak aralığı eşleşmesi de kimlik F1, kelime hata oranı veya konuşmacı ayrım hatası değildir; belirsiz metin ve başarısız kayıtlar paydadan gizlenmedi.
   **GÖZLEM**
   M6 Model zinciri Community-1, Whisper large-v3/CTranslate2 ve kalıcı kimlikte WeSpeaker 256 + ECAPA 192 kontrolüdür. İki temsil ayrı tutulur; çelişkide otomatik kalıcı kimlik verilmez.
   M7 Son uygulama kapısı ana veritabanına migrasyon uygulamadı; kendine ait `_test` veritabanını kurup kaldırdı. Ana uygulama 8081 üzerinde çalışır; özel çıkarım servisi model hazır olmadan iş kabul ettirmez.
   **AÇIK**
   M8 T02/T02.4 ve T10'un native Spark toplantı kanıtı, yeni toplantı modelinin native Apple ortamı; T11'in [bağımsız güvenlik araç paketi](security-toolchain-audit.md), genel admitted tarayıcı bundle'ı ve gerçek Kubernetes ortam girdileri eksiktir. Gerçek yerel tarayıcı geçişi bu harici kabul kayıtlarını üretmez.
   M9 Bir saatlik gerçek iş geçti; T10'un 2/4 saatlik tam model kapsamı, kesin kayıpsız/çiftsiz sözcük sınırı kabulü ve temsil edici Türkçe/50 kişilik precision/recall/F1, ayrım ve kelime hatası ölçümleri tamamlanmadı. Uzun koşumun ilk gözlem betiği kesildi; aynı uygulama işi yeniden yüklenmeden salt okunur takip edildi, ilk hata kaydı korundu. L3 sahip kabulü alınmadı.
   **YAN-ETKİ**
   M10 Uygulama/API/worker/model adaptörleri, eklemeli migrasyonlar, üretilmiş sözleşmeler, iki dilde ekranlar, senaryolar, kurulum/proxy/chart yüzeyleri ve Accepted plan/görev kanıtları birlikte güncellendi.
   M11 Yalnız ayrı normal kullanıcı/test tenantları ve koşuma ait veriler oluşturuldu; tarayıcı kendi kayıtlarını temizledi. Model ağırlıkları, sesler, ham metin/vektörler ve `.env` Git dışında; ilgisiz `plans/SPEECH_SEGMENT_DIAGNOSIS.md` değişikliğine dokunulmadı.
