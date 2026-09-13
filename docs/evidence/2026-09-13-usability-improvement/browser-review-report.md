# Koşum raporu — 2026-09-13 · Gerçek Türkçe kayıtta kaynak sesi inceleme

1. Sonuç: Gerçek sonuç ekranı ve dört dil/genişlik oynatma varyantı geçti — birim 0 başarılı / tarayıcı 4 başarılı / atlanan 3; karar bekleyen: yok. Gözlenen sınır L2'dir, fiziksel ses veya kullanıcı kalite kabulü değildir.
2. Koşulan: Brave tarayıcısı CUA ile, gerçek ters proxy `http://127.0.0.1:8081`; profil `kt-vibecoding-python-web-v2`. [Özet gözlemler](browser-review.json), [normal rol gerçek HTTP kanıtı](live-preview-http-report.md).

   | Akış | Gözlenen sonuç |
   | --- | --- |
   | Giriş | Gerçek giriş ekranında yerel Admin düğmesiyle giriş; tarayıcıya token enjekte edilmedi |
   | Dosya seçme | Eklenti `fileChooser.setFiles` işlemini `Not allowed` ile reddetti; bu adım atlandı |
   | Gerçek model işi | Önceden kullanılan 300 saniyelik Türkçe `rec01.wav` gerçek API'den üç parça ile yüklendi; kaynak hash eşleşti; 2 konuşan girdisi, otomatik hafıza kapalı; RTX işi `succeeded` |
   | Sonuç | 300/300 saniye işlenmiş, 2 konuşmacı, 101 metin satırı; galeri 1→1 ve profil yanıtları aynı |
   | Türkçe geniş / dar | Gözlenen CSS genişlikleri 1901 / 469 piksel; 6,06 saniyelik gerçek WAV, `readyState=4`, Blob kaynak, klavyeyle oynatma ve hata yok |
   | İngilizce dar / geniş | Aynı iki genişlikte aynı WAV çözüldü, klavyeyle başladı ve bitti; hata yok |
   | Dar görünüm | Her iki dilde yatay taşma yok; ekran görüntüsünde kontroller erişilebilir. İstenen viewport 390, gözlenen CSS genişliği 469 idi; tam 390 CSS piksel testi diye sunulmaz |
   | Seçim ve klavye | Üç kapatmada odak dinleme düğmesine döndü; ikinci konuşmacıya geçişte 1 oynatıcı ve 1 açık satır kaldı |
   | Metin sayfalama | 1–50→51–100 geçişinde oynatıcı kaldırıldı; geri dönüşte eski ses açılmadı |
   | Ad açıklaması | Ad değişiminin kimliği/yanlış atamayı düzeltmediği görüldü; form kaydedilmeden kapatıldı |
   | Çıkış | Açık oynatıcı çıkışta kaldırıldı ve gerçek giriş formu göründü; viewport sıfırlandı, test sekmesi kapatıldı |
   | Değişmezlik | Toplantı, iki konuşmacı, ilk 100 metin satırı ve galeri yanıtları aynı; kaynak WAV hash aynı |

   Normal rol, kurum ayrımı, kaynak/WAV eşitliği ve yetkisiz erişim Admin
   üzerinden çıkarılmadı; ayrı iki sıradan hesapla 182 gerçek HTTP işleminde
   doğrulandı. Kalıcı `09-meeting-audio-review.mjs` yazıldı ve sözdizimi
   denetlendi; headless koşucusu bu oturumda yürütülmedi. Buradaki dört başarı
   gerçek CUA gözlemlerine aittir.

3. Maddeler:

   **KUSUR**

   M1 İlk iki sayfa açılışında eski Vite çeviri dönüşümü boş ekran üretti. Diskte olan iki anahtar HTTP ile sunulan katalogda yoktu; `scripts/stack.sh restart frontend` ve reload sonrası sunulan anahtar doğrulandı, dört varyantta yeni console hatası oluşmadı (ÇALIŞMA ORTAMI DÜZELTİLDİ).

   **TUZAK**

   M2 Windows dosya izleme/değişiklik akışında yalnız tarayıcı reload yeterli olmayabilir; eski sunulan katalog ile yeni kaynak ayrımı yapılmalı. Eksik çeviriyi gizleyen fallback eklenmedi.

   M3 Tarayıcı eklentisinin yerel dosya erişimi engeli uygulama yükleme hatası diye sayılmadı; API ile yükleme gerçek sonuç testini sağladı, dosya seçicinin başarısını kanıtlamadı.

   **GÖZLEM**

   M4 Kaynak sesi dinlemek model çalıştırmıyor ve sonuçları değiştirmiyor. Yeni iş ilk 300 saniyelik tek parçayı kullandığından Türkçe çok parça sınırı doğruluğuna yeni model kanıtı sağlamaz; `results.md` doğruluk skoru eklenmedi.

   **AÇIK**

   M5 Atlanan üç adım: tarayıcı dosya yükleme, kalıcı headless senaryo yürütümü ve fiziksel hoparlör çıktısı. Kod/dosya/HTTP testleri bu eksikleri başarılıya çevirmiyor.

   M6 Bu kaydın satırları 30 saniyeden kısa; uzun satırın önceki/sonraki ses bölümü ile hata/expiry ekranları otomatik testlerde sınandı, bu canlı varyantta gözlenmedi. Kullanıcının gerçek toplantısı ve 50 kişi kabulü açık.

   **YAN-ETKİ**

   M7 Admin çalışma alanına “Kaynak sesi inceleme testi 13 Eylül” adlı tek gerçek test toplantısı eklendi; yeni kişi oluşturma kapalıydı, mevcut profil değişmedi. Kaynak normal saklama süresine tabidir; silinmedi.

   M8 Güncel kodu yüklemek için worker ve frontend yeniden başlatıldı; mevcut wrapper ters proxy'yi yeniledi. Geçici sekme/viewport temizlendi; özel iş durumu yalnız Git dışı `outputs/` altında kaldı.
