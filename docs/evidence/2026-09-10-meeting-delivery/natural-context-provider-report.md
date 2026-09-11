# Koşum raporu — 2026-09-11 · Yerel toplantı bağlamı ve özel hafıza sağlayıcısı

1. Sonuç: Python 3.13 konteynerinde sağlayıcı süiti başarılı, gerçek hafıza doğruluğu henüz kabul edilmedi — birim 178 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `pytest app/inference/tests -q` → özel HTTP, decoder, model sınırı, doğal bağlam, kaynak hash'i ve hafıza → 178; ortam sabit `7b3e7348` x86_64 imajı, ağ kapalı, güncel kaynak salt okunur bağlandı. `ruff check` → import düzeltmesi sonrasında başarılı; backend aday portu ve parça servisi mypy → 2 kaynak başarılı.
3. Maddeler:

   **KUSUR**

   M1 Doğal sessizlik boşluğu VAD tarafından köprülenirse konuşma sayılabiliyordu; özgün tek konuşmacı aralıklarıyla kesişim eklendi (DÜZELTİLDİ, `test_meeting_candidates.py`).

   M2 Yeni özel HTTP testinin eski `audio/wav` başlığı JSON isteğini 415 yapıyordu; test gerçek JSON başlığına taşındı, 310 saniye sınırı eski 70 saniye beklentisinin yerini aldı (DÜZELTİLDİ, `test_meeting_memory.py`, `test_meeting_runtime.py`).

   **TUZAK**

   M3 Backend Windows ortamında scipy, eski araştırma ortamında pydantic yok; tam sağlayıcı koşumu sabit Python 3.13 konteyneri ve mevcut çevrimdışı test araçlarıyla çalıştırıldı.

   **GÖZLEM**

   M4 Yeni port 192 ve 256 boyutlarını ayrı taşır; kabul edilen PCM örneği yeniden kodlanıp iki vektör aynı örnekten üretilir. Bu sınır testleri biyometrik doğruluk kanıtı değildir.

   **AÇIK**

   M5 Araştırmadaki ilk doğal bağlam kalite kuralı iki uzun karışımı saf profil sanabildi; bu negatif sonuçlar korunuyor ve üretim doğruluk kabulü verilmedi.

   M6 Yeni imajla gerçek özel HTTP hafıza, A/B/D/C ve 310 saniye model/bellek denemeleri bekliyor; Spark ve 50 kişi Türkçe kabulü gözlenmedi.

   **YAN-ETKİ**

   M7 Doğal bağlam, ayrı kalite portu ve regresyonları eklendi; geçici XML/loglar yalnız ignore edilen `outputs/2026-09-10-meeting-delivery` altında saklandı. Kalıcı kullanıcı profili bu koşumda oluşturulmadı.
