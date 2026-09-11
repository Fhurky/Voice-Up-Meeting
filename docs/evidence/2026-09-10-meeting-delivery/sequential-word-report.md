# Koşum raporu — 2026-09-11 · Ardışık konuşmacıları kapsayan sözcüklerin kimlik belirsizliği

1. Sonuç: Üç eksik davranış başarısız testlerle gözlendi, düzeltmeden sonra dar paket geçti — birim 29 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows, Python 3.13, `kt-vibecoding-python-web-v2`; `PYTHONPATH=app/backend app/backend/.venv/Scripts/python.exe -m pytest app/backend/tests/unit/test_meeting_timeline.py -q`; önce 24 başarılı/2 başarısız, sonra 26 başarılı; bağımsız incelemedeki ek kusur 28 başarılı/1 başarısız verdi, son koşum 29 başarılı. Black geçti. Ham JUnit: `outputs/2026-09-10-meeting-delivery/sequential-{word-red,word-green,preferred-red,final-green}.xml`.
3. Maddeler:
   **KUSUR**
   M1 Bir sözcüğün uzun zaman aralığı ardışık kişileri kapsarken en uzun kişiye kesin kimlik veriliyordu; en güçlü tekil destek yüzde 80'e ulaşmıyorsa sözcük kimliksiz ve belirsiz korunur (DÜZELTİLDİ, `meeting_timeline.py`, `test_stretched_word_spanning_sequential_voices_keeps_text_without_claiming_identity`).
   M2 Aynı kişiye ait iki sözcük arasındaki yazıya çevrilmemiş rakip konuşma birleşik satıra katılıyordu; rakip konuşma satır birleştirmeyi keser (DÜZELTİLDİ, `test_grouping_cannot_bridge_untranscribed_competing_speech`).
   M3 Normal konuşmada yüzde 91 destekli kişi varken exclusive çıktının yüzde 9'luk rakibi seçilebiliyordu; örtüşme olmayan kimlik normal destekten seçilir (DÜZELTİLDİ, `test_exclusive_minor_voice_cannot_override_regular_sequential_dominance`).
   **TUZAK**
   M4 Metin veya zaman aralığı silinmez; eşzamanlı konuşmanın görünür örtüşme davranışı korunur. Yüzde 80 ve yüzde 79,9 sınırları ile yüzde 91 baskın kısa sınır sözcüğü korunur.
   **GÖZLEM**
   M5 Gerçek v6 C kaydında 105,02–117,68 saniyelik tek sözcük kaynak eşleşmesini yüzde 88,3432'ye indirdi; yüzde 90 kabul eşiği ve dört kaynak değiştirilmedi, başarısız koşum özel yerel çıktıda korundu.
   **AÇIK**
   M6 Bu dar paket gerçek model, yeni boş hafızadaki A/B/D/C tekrarı veya son tam kalite kapısının yerine geçmez; canlı tekrar ayrı kaydedilecektir.
   **YAN-ETKİ**
   M7 Accepted 002 Decision 18, saf zaman çizelgesi ve koruyucu testler güncellendi; model ağırlıkları ve ASR ayarları değişmedi.
