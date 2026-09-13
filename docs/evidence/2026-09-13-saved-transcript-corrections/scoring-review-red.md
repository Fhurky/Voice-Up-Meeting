# Koşum raporu — 2026-09-13 · Kaydedilemeyen kısmi önerinin puanlanması

1. Sonuç: Kısmi/geçersiz yanıtın uygulanmış gibi puanlanması kusuru yeniden üretildi — birim 11 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows Python 3.12; `pytest tests/test_transcript_review_controller.py -q -o addopts=`; 2 başarısız, 11 başarılı, 0,47 saniye.
3. Maddeler:

   **KUSUR**
   M1 Hem eşlenen hem eşlenemeyen öneri içeren yanıt, kaydedilemediği halde kelime hatasını değiştirdi; yeni regresyon bunu yakaladı.
   M2 Geçerli JSON biçimindeki kesilmiş yanıt da uygulanmış sayıldı; ikinci regresyon aynı yanlış hesabı gösterdi.

   **TUZAK**
   M3 Model önerisinin ekranda görülebilmesi, bütün cevabın kaydedilebilir veya kalite hesabında uygulanmış olduğu anlamına gelmez.

   **GÖZLEM**
   M4 Üç gerçek modelin 12 sabit örneğinde bu iki kısmi durum yoktu; toplu skorları ham kanıttan ayrıca yeniden hesaplanacak.

   **AÇIK** — yok

   **YAN-ETKİ**
   M5 İki regresyon testi eklendi; model veya kullanıcı verisine yazılmadı.
