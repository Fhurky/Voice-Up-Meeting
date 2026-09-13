# Koşum raporu — 2026-09-13 · Tam FLEURS Türkçe test bölümünde betimleyici hata analizi

1. Sonuç: 743 klipte 3.717 kaynak/hizalama kontrolü başarılı; ortak Unicode aktarımının 10 kontrolü de geçti, model puanı değiştirilmedi — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Yerel Windows/Python CPU; tamamlanmış `fleurs.private.json` ve sabit manifest üzerinde `voiceup-turkish-orthography-boundary-diagnostics-v2`. MediaSpeech v2 ile aynı sözcük listesi ve hizalama öncelikleri kullanıldı; yeni model/ayar/çıkarım yok. Sabit profil `kt-vibecoding-python-web-v2` korunuyor.

   | Gözlem | Tam 743 klipteki sayı |
   | --- | ---: |
   | Referans / hipotez kelimesi | 12.914 / 12.966 |
   | Değiştirme / silme / ekleme | 676 / 56 / 108 |
   | Toplam kelime hatası | 840 |
   | Sıfır kelime hatalı / boş hipotezli klip | 321 / 0 |
   | Rakam içeren referans / hipotez klibi | 134 / 182 |
   | Rakam–yazıyla sayı temsili adayı | 42 klip, 51 hata bloğu |
   | Birleşik–ayrı yazım eşdeğer harf dizisi | 48 klip, 50 blok, 100 hata işlemi |
   | Yalnız kesme işareti farklı değiştirme | 61 klip, 68 değiştirme |
   | Harf işareti/kesme farkı adayı, önceki satır hariç | 83 klip, 89 değiştirme |
   | Başta / sonda silinen referans kelimesi | 0 / 0 |
   | Ekleme ağırlıklı / kelime hata oranı %50 üzeri klip | 15 / 1 |

   [Anonim JSON](fleurs-error-analysis-v2.json), SHA-256
   `c794247b2815696eb1661b4896b12434a20efc4e7b19d02f9e829042be3f1e1f`;
   kaynak özel rapor SHA-256
   `b8fdff098788ca4a1daaa247b92500ca226c6b40e2c249561702dac4da3e28b5`.
   [Ortak Unicode aktarım kanıtı](diagnostic-unicode-probes.json), aynı
   kodlanmış sözcük listelerinin iki JSON'da doğru korunduğunu denetler.
   Bu ortak 10 kontrol, her kaynakta ayrı 10 yeni kontrol diye toplanmamalıdır.
   Son ortak belge denetiminin 7 başarılı hash/Unicode kontrolü de
   [MediaSpeech v2 raporunda](mediaspeech-error-analysis-v2-report.md) kaydedildi.

3. Maddeler:

   **KUSUR**

   M1 Önceki MediaSpeech geçici analizinde bulunan Türkçe sabit sözcük aktarım kusuru, FLEURS analizi yayımlanmadan giderildi. Unicode kaçışları ve çıktıdaki gerçek listeler ortak kontrolle doğrulandı; FLEURS için hatalı ilk sürüm yayımlanmadı (DÜZELTİLDİ, `diagnostic-unicode-probes.json`).

   **TUZAK**

   M2 Bu veri 743 erkek etiketli kayıt ve tekrar eden 329 cümle kimliği içerir; 743 bağımsız kişi/oturum veya Türkçe nüfusu değildir. Aynı cümlenin tekrarları gözlemleri bağımlı kılar; kaynaklar arası fark nedensel model iyileşmesi sayılamaz.

   M3 Sayı/yazım kategorileri adaydır ve kesişebilir; doğru anlam veya hatanın yalnız yazımdan geldiği varsayılmaz. Harf işaretlerini kaldırmak sadece bu tanıda karşılaştırma kuralıdır, gerçek metrik normalizasyonu değişmedi.

   **GÖZLEM**

   M4 FLEURS referanslarında 134 klip rakam içeriyor; MediaSpeech referanslarında hiç rakam yok. FLEURS'te 42/743, MediaSpeech'te 617/2.433 klip sayı temsili adayı taşıyor; farklı referans yazım sözleşmelerini aynı varsaymak uygun değil.

   M5 FLEURS'ün 56 silmesinin hiçbiri kullanılan hizalamada baş/sonda değil; MediaSpeech'te 1.387 sınır silmesi gözlendi. Kaynak türü ve referans kapsamı farklı; bu karşılaştırma ses dinlemeden sebep atamaz.

   M6 Kesme işareti farkları 68 değiştirmede, başka harf işareti/kesme adayları 89 değiştirmede yer alıyor. Sayı, yazım ve harf işareti kaynaklarını insan doğrulamasıyla ayırmak, sonraki hata incelemesini somutlaştırır.

   **AÇIK**

   M7 Ses dinleme, referans düzeltme, özel ad/kurum adı ve yabancı sözcük etiketleme yapılmadı. Sıfır sınır silmesi bütün klip sınırlarının kusursuz olduğunu göstermez; yakın kopya veya model eğitim sızıntısı bu analizle ölçülmez.

   **YAN-ETKİ**

   M8 Yalnız sürümlü anonim hata JSON'u ve bu rapor eklendi. Kaynak ses/metin, özel hipotezler, model, kod, günlük ve veritabanı değiştirilmedi; yeni GPU koşumu yapılmadı.
