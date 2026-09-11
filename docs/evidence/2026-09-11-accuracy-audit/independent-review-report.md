# Koşum raporu — 2026-09-11 · Merkez, metin ölçümü, veri hazırlama ve özel çıkarım sınırlarının bağımsız incelemesi

1. Sonuç: Bir P2 veri hazırlama kusuru doğrulandı ve ayrı düzeltmeyle kapandı; incelenen diğer sabit sınırlarda ek somut kusur bulunmadı — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok. Salt okunur ölçüm doğrulamasında 512 örneğin 1.024 sonucu bağımsız hesapla eşleşti.
2. Koşulan: Windows/Python 3.12; sabit `kt-vibecoding-python-web-v2` kapsamındaki Decision 19–22 kod, test ve sözleşmelerinin ilk salt okunur incelemesi, ardından Decision 19–24'ün tamamlanmış üretim kaynaklarının bağımsız son incelemesi. İnceleme yeni bir uygulama testi veya tam kalite kapısı koşusu değildir.

   | Sınır | İncelenen kaynak / gerçek doğrulama | Sonuç |
   |---|---|---|
   | Kaynak ağırlıklı merkez | `app/backend/app/domain/meeting_centroid.py`, ilgili worker güncellemesi ve birim/PostgreSQL testleri | Ayrı 192/256 ağırlık ve norm; sıfır/tekrar katkı, eski başlangıç kökeni ve geçersiz durumun reddiyle çelişen ek kusur bulunmadı |
   | Metin ölçümü | `src/voiceup/meeting_metrics.py`, `scripts/score-meeting-transcript.py` ve testleri | Paydalar, fazla/eksik ve atanmamış akışlar, normalizasyon genişlemesi, çalışma sınırı ve metinsiz çıktı incelendi |
   | Bağımsız ölçüm hesabı | Kaydedilmiş araç çağrısında `Random(37261)` ile 512 küçük yapay örnek; tüm permütasyonlar ve ayrı tam-matris Levenshtein hesabı | Her örnekte `cpwer` ve `assigned_only`: 1.024/1.024 eşleşme, 0 hata; boş/eksik/fazla/atanmamış akışlar dahil |
   | Hazırlayıcı süreleri | `select_utterances` üzerinde bellekte `[45]`, `[61,35]`, `[30,20]` saniyelik kaynaklar | İlk iki geçerli seçim yolu hatalı reddedildi; üçüncü 50 saniye üretti; kusur ayrı [düzeltme raporunda](preparer-duration-report.md) kapandı |
   | Özel karar izi | `meeting_memory_trace.py`, hafıza transaction yolu ve özel/genel çıktı, tekrar, eski claim ve temizleme testleri | En fazla iki skor/popülasyon; aday kimliği veya ses/metin yok; mevcut tenant, kaynak ve fencing sınırlarıyla çelişen ek kusur bulunmadı |
   | GPU'da istek boyunca tutma | `meeting_models.py`, `runtime.py`, `test_meeting_residency.py` | Tek istek sahibi, süresi biten encoder, yanlış thread/iç içe çağrı reddi ve hata sonunda hassasiyet/CPU/kilit temizliği incelendi; model koşusu yapılmadı |
   | Kaynağa bağlı farklı kişi kanıtı | `meeting_native_exclusions.py`, `meeting_chunks.py`, `meeting_memory.py`, `meeting_cleanup.py`, `meeting_repository.py`; ilgili birim/gerçek PostgreSQL testleri | Tenant/aktif peer/simetri, tam aday sıralaması, yalnız bağlam parçası, kaynak fingerprint'i, aynı transaction'da iki çelişkili bağın kaldırılması ve temizleme incelendi |
   | İki bağımsız kalite kontrolü | `meeting_coherence.py`, `meeting_memory.py`, `meeting_models.py`, `runtime.py`, `api.py`; çift model ve residency testleri | Boyutların ayrılığı, veto sonrası bütün saklanabilir çıktının kaldırılması, sağlayıcı hatasında 503 ve CPU taşıma hatasında da oturum/kilit temizliği incelendi |

3. Maddeler:

   **KUSUR**

   M1 P2 — Hazırlayıcıdaki belgelenmeyen 40 saniyelik tek cümle sınırı, 45/60 saniyelik geçerli kaynaklarla taşan cümleyi atlama sözleşmesini ihlal ediyordu (DÜZELTİLDİ, [5 başarısız regresyon → 20 başarılı test](preparer-duration-report.md)).

   **TUZAK**

   M2 Bu bir yeniden üretilebilirlik/geçerli girdi kusurudur; mevcut 190 klibin seçilen cümleleri 40 saniyeyi aşmadığından 50 kişilik gerçek hafıza karışımının nedeni değildir. Tarihsel sesler, manifestler ve hazırlayıcı hashleri değişmedi.
   M3 Kod incelemesinde ek kusur bulunmaması kalite geçişi değildir; özel modelin sayısal eşdeğerliği ve gerçek kullanıcı akışı ayrı canlı kanıta dayanır.

   **GÖZLEM**

   M4 512 örneklik bağımsız doğrulama doğrudan araç çağrısında çalıştı; ayrı dosya veya hash üretilmedi. Sözcükler yalnız yapay `a/b/c` dizileriydi; kullanıcı metni, model, ağ veya veritabanı kullanılmadı.

   **AÇIK**

   M5 Son inceleme Decision 23–24'ü de kapsadı; bilinen [C yanlış birleşmesi](capacity50-c-merge-forensics-report.md) açık kalır. GPU sırasında gerçek HTTP kopması ve bozuk merkez metadata'sıyla yalnız bağlam parçası için ayrı sınır testi görülmedi; bunlar doğrulanmış yeni kusur değildir.
   M6 Temsilî Türkçe doğal ses ve yeterli bağımsız desteği olmayan kısa ikinci ses üzerinde genelleme kod incelemesiyle kanıtlanamaz; elli kişinin bütün kaynak/ses örneği denetimleri ayrı canlı raporlardadır.

   **YAN-ETKİ**

   M7 Bu inceleme uygulama kodunu, kaynak sesleri veya veritabanını değiştirmedi; yalnız bu rapor kaydedildi. Hazırlayıcı düzeltmesini kök ajan ayrı kaynak/test değişikliği olarak yaptı. Son inceleme sırasında 190 kliplik deneyin üretim kaynağı ve imaj sabitlemesi korundu.
