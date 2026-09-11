# Koşum raporu — 2026-09-11 · Kalıcı hafıza örneğinin kaynak hash'i ve üç bağımsız bağlam koşulunun salt okunur incelemesi.

1. Sonuç: İki bütünleşme kusuru ana uygulama sahibine bildirildi; kalite başarısı iddia edilmedi — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok. Bu inceleme L0.
2. Koşulan: `kt-vibecoding-python-web-v2`; `meeting_chunks.py`, `meeting_memory.py`, `meeting_memory_samples.py`, `meeting_memory_ports.py`, `meeting_memory_inference.py` ve `audio_storage.py` kaynak okuması. Test veya model çalıştırılmadı.
3. Maddeler:

   **KUSUR**
   M1 İnceleme anında `meeting_chunks.py` kaynak hash'ini yalnız eski ECAPA usable dalında yazıyordu; yeni bağlamı olan abstain track, hafıza `memory_candidate_source_mismatch` denetimini geçemez. Ana ajana kaynak hash'ini aday kanıtla beraber yazma ve regresyon isteği iletildi.
   M2 İnceleme anında parça biriktirme aday sayısını sınırlandırmıyor, hafıza okuyucusu 256 üstünü reddediyordu; uzun konuşan kişi bu sınırı aşabilir. Ana ajana deterministik sınırlı biriktirme ve uzun-kayıt regresyonu iletildi.
   **TUZAK**
   M3 Bu kayıt gelişmekte olan kaynakların gözlemidir; kusurların kapanması düzeltilmiş kaynak ve gerçek regresyonla ayrıca doğrulanmalıdır. Salt kaynak okuması test geçişi yerine kullanılamaz.
   **GÖZLEM**
   M4 `validate_context_result` girdi hash/rate/frame eşleşmesini, seçilen indekslerin sınırlarını ve aralıkların bildirilen ses altkümesi olmasını doğrular; özgün kaynak aralıklarına geri eşleyip tekrarları birleştirir.
   M5 `resolve_context` yeniden üretilen saklama WAV'ının SHA-256 değerini sağlayıcının `retained_sha256` alanıyla karşılaştırır; bilinmeyen otomatik kayıt için özgün konuşma süresi kesin 20 saniyeyi aşmalı ve kabul edilen bağlamların en az üç farklı PCM hash'i bulunmalıdır.
   M6 Kayıt adaptörü aktardığı byte'ların hash'ini hesaplar; bu hash Recording/SpeakerSample ve yeni 256 boyutlu profil kaynak referansına taşınır. Tanınan kişinin vektörü ve örnek sayısı bu dalda büyütülmez.
   **AÇIK**
   M7 Sağlayıcının doğru kişiyi ve gerçek konuşma saflığını seçmesi kaynak incelemesiyle kanıtlanamaz; sabit model kontrolleri ve A/B/D/C akışı ana teslimde gereklidir.
   **YAN-ETKİ**
   M8 İncelenen uygulama dosyalarında değişiklik yapılmadı; yalnız bu rapor oluşturuldu ve iki bulgu ana ajana iletildi.
