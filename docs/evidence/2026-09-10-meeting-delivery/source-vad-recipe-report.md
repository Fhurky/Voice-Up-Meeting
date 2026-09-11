# Koşum raporu — 2026-09-11 · Kaynak VAD sözleşmesi ve sabit kümeleme tarifi

1. Sonuç: Sağlayıcı sözleşme regresyonları başarılı — birim 183 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `pytest app/inference/tests -q` → 183; ortam Python 3.13, sabit `7b3e7348` x86_64 imajı, ağ kapalı, güncel kaynak salt okunur. İlk tarif ve VAD regresyonları birer kez, biçim regresyonları üç kez beklenen eksiklik nedeniyle başarısız oldu; ara tam süit 180, son tam süit 183 başarılı. Ayrıntılar ignore edilen `outputs/2026-09-10-meeting-delivery/{clustering-recipe-red,source-vad-red,recipe-vad-green,private-pcm-red,private-pcm-green}.{txt,xml}` içinde.
3. Maddeler:

   **KUSUR**

   M1 Model kurucusu seçilen Fa=0,15 tarifini uygulamıyordu; sabit parametreler ve özel tarif kimliği eklendi (DÜZELTİLDİ, `test_local_constructor_applies_recorded_clustering_recipe`).

   M2 Örnek bağlamları yerel etiket birleştirilmeden üretiliyordu; sağlayıcı artık hash/sürüm etiketli kaynak VAD aralıklarını gönderir, bağlamı uygulama oluşturur (DÜZELTİLDİ, `test_meeting_exports_source_vad_for_candidates_after_acoustic_mapping`).

   M3 Özel toplantı girdisi FLAC, float WAV ve çok kanal kabul ediyordu; mono PCM16 WAV sınırı çözmeden önce denetlenir (DÜZELTİLDİ, `test_private_meeting_input_requires_source_mono_pcm16_wav`).

   **TUZAK**

   M4 Pyannote iç codec yükleyicisi FFmpeg yokluğu uyarısı verdi; ürün doğrulanan libsndfile ile çözüp bellekte dalga biçimini iletir. İki mevcut test çatısı kullanım dışı kalma uyarısı da korundu.

   **GÖZLEM**

   M5 Bu testlerde gerçek dosya ve özel HTTP sınırı kullanıldı; model hesapları sözleşme fikstürüdür, biyometrik doğruluk kanıtı değildir.

   **AÇIK**

   M6 Yeni çalışan imajla kaynak VAD, birleştirme, hafıza ve A/B/D/C kabulü ayrıca gözlenmelidir; karışık ses koruması araştırması sürmektedir.

   **YAN-ETKİ**

   M7 Decision 15, özel model tarifi ve sağlayıcı kaynak aralıkları eklendi; ham ses, vektör veya anahtar rapora alınmadı. Bu koşumda kalıcı profil oluşturulmadı.
