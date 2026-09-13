# Koşum raporu — 2026-09-13 · Bağlamsal metin incelemesi ilk uygulama kontrolü

1. Sonuç: İşlev çalıştı; üç yeni testin bekleme/etiket varsayımı düzeltilmeli — birim 35 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `scripts/stack.sh exec -T frontend npm test -- src/services/meetings.test.ts src/components/MeetingResults.test.tsx src/components/MeetingTextReview.test.tsx`; mevcut Linux frontend konteyneri, 38 test, 3 başarısız, çıkış 1.
3. Maddeler:

   **KUSUR**
   M1 Yeni testlerde asenkron dil kataloğu yüklenmeden düğme/ilk istek arandı; iki test başarısız.
   M2 Retry testindeki etiket mevcut `common.retry` Türkçe karşılığıyla uyuşmadı; bir test başarısız.

   **TUZAK**
   M3 Dil sağlayıcısı katalog yüklenene kadar çocukları oluşturmaz; test gerçek görünür durumu beklemeli.

   **GÖZLEM**
   M4 Kaynak kimliği/metni/SHA256, Unicode ve düz metin güvenliği dahil 35 kontrol geçti; ilk iki kırmızı davranış yeşil.

   **AÇIK**
   M5 Üretilmiş sözleşme, tam kontrol ve gerçek tarayıcı henüz çalıştırılmadı.

   **YAN-ETKİ**
   M6 Yerel UI/hizmet/katalog ve yeni test eklendi; kayıtlar değişmedi.
