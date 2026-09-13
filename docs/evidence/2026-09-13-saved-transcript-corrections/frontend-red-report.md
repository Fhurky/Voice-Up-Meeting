# Koşum raporu — 2026-09-13 · Model seçimi ve kayıt hizmetlerinin kırmızı testi

1. Sonuç: Yeni üç hizmetin eksikliği gözlendi — birim 7 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Mevcut Linux frontend konteynerinde `scripts/stack.sh exec -T frontend npm test -- src/services/meetings.test.ts`; 10 test, 3 başarısız, çıkış 1. Profil `kt-vibecoding-python-web-v2`.
3. Maddeler:

   **KUSUR**
   M1 `reviewModels`, `correctionSuggestion`, `saveCorrection` mevcut değil; yeni kontrat testleri başarısız.

   **TUZAK**
   M2 012'nin eski API sözleşmesi korunur; kullanıcı ekranı 013'ün açık model seçimi ve kaydetme davranışına genişler.

   **GÖZLEM**
   M3 Önceki yedi hizmet kontrolü geçti.

   **AÇIK**
   M4 Yeni arayüz ve gerçek model/tarayıcı henüz çalıştırılmadı.

   **YAN-ETKİ**
   M5 Hizmet testlerine üç yeni davranış eklendi; iş verisi değişmedi.
