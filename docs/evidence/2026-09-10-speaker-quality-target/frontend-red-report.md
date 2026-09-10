# Koşum raporu — 2026-09-10 · Profil kotasının kaldırılması için ön yüz kırmızı aşaması.

1. Sonuç: Güncel Decision 11 davranışını eski kota uygulaması karşılamadı — birim 14 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`; yerel Windows Git Bash → `scripts/stack.sh exec -T frontend npm test -- src/pages/SpeakerProfilesPage.test.tsx src/pages/SpeakerJobPage.test.tsx src/components/AudioJobForm.test.tsx src/lib/speakerErrors.test.ts --reporter=dot`. Çalışan Linux frontend konteynerinde 27 test: 14 başarılı, 13 başarısız, 0 atlanan; çıkış 1.
3. Maddeler:

   **KUSUR**
   M1 Eski kapasite sayacı, liste yüklenme/hata engeli ve sayfalama sırasında yeni kayıt engeli 9 profil sayfası testinde yakalandı; koruyucu `SpeakerProfilesPage.test.tsx`.
   M2 Geçmiş `profile_limit` hatası güncel kota gibi anlatıldığı için Türkçe/İngilizce form ve terminal iş metinleri 4 testte başarısız oldu; koruyucular `AudioJobForm.test.tsx` ve `SpeakerJobPage.test.tsx`.
   **TUZAK**
   M3 Test yanıtı Decision 11'in `{items, total, offset, limit}` sözleşmesini kullanır; eski kod kaldırılmış `max_profiles` alanını okumaya devam ederken kapasite başlığı hâlâ oluştu.
   **GÖZLEM**
   M4 50/51/100/200/201 toplamları, iki dilde yüklenme/hata ve geçmiş iş metinleri yeni karara göre korunur; önceki kota kanıtları değiştirilmedi.
   **AÇIK**
   M5 Yeşil uygulama, tam kalite kapısı ve gerçek tarayıcı bu kırmızı aşamada henüz koşulmadı.
   **YAN-ETKİ**
   M6 Ön yüz testleri kabul edilen Decision 11'e uyarlandı; veritabanı, profil veya ses fikstürü oluşturulmadı/silinmedi.
