# Koşum raporu — 2026-09-13 · Kullanılabilirlik planı ve kaynak ses inceleme belgeleri

1. Sonuç: İncelenen belgelerde kırık yerel bağlantı veya yeni kabul kapsamıyla çelişen gereksinim bulunmadı; kontrollü galeri tablosunun sorgu paydası açıklığa kavuşturuldu — yerel bağlantı 80 başarılı / uygulama-senaryo yolu 11 başarılı / birim 0 başarılı / tarayıcı 0 başarılı / atlanan 4 dış bağlantı; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`, yerel Windows/Python; 13 belge UTF-8 olarak salt okunur incelendi. Markdown hedefleri belge dizinine göre çözüldü ve gerçek dosya/dizin varlığı kontrol edildi; web adresleri açılmadı, test veya model çalıştırılmadı.

   | Belge grubu | Belge sayısı | Yerel bağlantı |
   |---|---:|---:|
   | [Kullanılabilirlik/doğruluk planı](../../../plans/USABILITY_AND_ACCURACY.md) | 1 | 18 |
   | [011 PRD](../../../specs/speaker-identity/PRDs/011-meeting-audio-review/PRD.md), plan ve görevler | 3 | 5 |
   | [TR rehberi](../../tr/meeting-audio-review.md), [EN rehberi](../../en/meeting-audio-review.md) ve iki dilin README dosyaları | 4 | 12 |
   | [Tarayıcı manifesti](../../../e2e/QUALITY_MANIFEST.md) ve [senaryo rehberi](../../../e2e/speaker-identity/README.md) | 2 | 5 |
   | [Değerlendirme planı](../../EVALUATION_PLAN.md) ve [ölçüm tanımları](../../MEETING_ACCURACY.md) | 2 | 13 |
   | [Domain yol haritası](../../../specs/speaker-identity/roadmap.md) | 1 | 27 |

   Ayrıca PRD/planın dayandığı üç backend dosyası, dört frontend dosyası, OpenAPI, üretilmiş tipler, `09-meeting-audio-review.mjs` ve `run-all.mjs` bulundu. Senaryonun toplu koşucuya eklenmesi, manifest ve rehber kaydıyla karşılaştırıldı. Skorlar mevcut 11/13 Eylül raporlarından kontrol edildi; ham ses veya gizli hesap dosyaları okunmadı.

3. Maddeler:
   **KUSUR**
   M1 Kontrollü 50 kişi tablosundaki `95/100 doğru sorgu` paydanın bilinen sorgular olduğunu açık söylemiyordu; ana görev bunu `95/100 doğru bilinen sorgu; ayrıca 40 yabancı sorguda yanlış kabul yok` olarak düzeltti ve son metin yeniden okundu (DÜZELTİLDİ, `plans/USABILITY_AND_ACCURACY.md`).
   **TUZAK**
   M2 Kontrollü sonuç 49/50 profil, 100 bilinen ve 40 yabancı sorgudur; tam toplantı zincirindeki 37/50 ilk profil, 35/50 dönüş ve ek %99 kaynak koşulundaki 27/50–28/50 ölçümleri aynı payda/başarı tanımı değildir. Plan bunları ayırıyor.
   M3 `EVALUATION_PLAN.md` içindeki Spark işletim ve eski eşik açıklamaları 8–9 Eylül tarihli tarihsel bölümdedir; yeni plandaki RTX 4060 kanıtının güncel cihaz koşumu diye eski metne taşınması veya eski skorun güncel başarı sayılması uygun olmaz.
   **GÖZLEM**
   M4 Yeni plandaki 50 kişilik galeri, 3+ saniye temiz farklı oturum sorgusunda FPIR ≤%1 iken bilinen doğru tanıma ≥%95 ve ayrı ≤%0,1 çalışma noktası mevcut değerlendirme hedefleriyle tutarlıdır; 50 profil ürün kotası yapılmıyor, başarısız ilk kayıtlar recall paydasından çıkarılmıyor.
   M5 2.433 MediaSpeech/71.767 kelime ve 743 FLEURS/12.914 kelime sayıları, yuvarlatılmış WER değerleri ve eski 80 dahil 3.256 klip toplamı kanıtla uyumlu; iki Türkçe zincirin aynı altı kişiyi kullanması ve zayıf referanslı %29,96/%30,44 cpWER ayrıca belirtiliyor.
   M6 011'in 30 saniye/11.520.128 bayt sınırı, kaynak ömrü, tek oynatıcı, ad değiştirmenin kimliği düzeltmemesi ve TR/EN rehberleri tutarlı; senaryo rehberi fiziksel ses, uzun satırın bütün bölümleri ve süre sonunu dar tarayıcı akışından çıkarmıyor.
   **AÇIK**
   M7 Dört dış bağlantının erişilebilirliği ve uzak içeriğinin güncelliği bu yerel denetimde sınanmadı; yerel hedeflerde kırık bağlantı veya fragment hedefi yoktu.
   M8 Bu belge incelemesi gerçek ses, tarayıcı veya tam kalite kapısı sonucu değildir. Ana görev ayrı olarak 687 backend ve 158 frontend başarısı bildirdi; 011/002 kabul kutuları ve nihai kapsam raporu ana görev tarafından kendi canlı kanıtıyla güncellenecek.
   **YAN-ETKİ**
   M9 Bu denetçi yalnız bu raporu ekledi; gereksinim, uygulama, model, veri, sözleşme veya deney günlüğü değiştirmedi. M1'deki açık payda düzeltmesini ana görev yaptı; kırık bağlantı olmadığı için bağlantı düzenlemesi yapılmadı.
