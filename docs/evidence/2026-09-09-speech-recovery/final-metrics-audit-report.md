# Koşum raporu — 2026-09-09 · Üç canlı konuşmacı değerlendirmesinin bağımsız sonuç denetimi

1. Sonuç: Üç tamamlanmış koşumun 906 işi ve önceki tarihsel referans bağımsız olarak uzlaştırıldı; 9.000 veri/özet kontrolü başarılı, 0 tutarsızlık — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok. Bu denetim yeni pytest vakası veya model çağrısı değildir.
2. Koşulan: Windows, Python 3.13.14; sabit teknoloji profili <code>kt-vibecoding-python-web-v2</code>. Yalnız yerel JSON ve kaynak hashleri okundu; üretim hesaplama fonksiyonları içe aktarılmadı. <code>app/backend/.venv/Scripts/python.exe outputs/quality-improvement/final-metrics-audit.py --publish</code> → [anonim denetim](final-metrics-audit.json). Önceki 707 işlik referansın 302 eşleşmiş kaydı karşılaştırıldı; bu referans 906 yeni işe eklenmedi.

   | Koşum | İş: başarılı / kalite hatası | Kayıtlı / planlanan profil | Doğru / planlanan bilinen sorgu | Bilinen kalite hatası | Bilinmeyen: ret / belirsiz / kalite hatası | Yanlış kişi / yanlış kabul | Yeni kişinin kaydı ve geri dönüşü |
   |---|---:|---:|---:|---:|---:|---:|---|
   | Kalibrasyon | 267 / 35 | 40 / 50 | 111 / 150 (%74) | 18 | 89 / 4 / 7 | 0 / 0 | İkisi başarılı |
   | Tarihsel | 236 / 66 | 29 / 50 | 78 / 150 (%52) | 24 | 81 / 0 / 19 | 0 / 0 | İkisi kalite hatası |
   | Yeni temiz küme | 277 / 25 | 40 / 50 | 116 / 150 (%77,33) | 10 | 94 / 1 / 5 | 0 / 0 | İkisi başarılı |

   Her koşum 50 kayıt girişimi, 150 bilinen kişi sorgusu, 100 bilinmeyen kişi sorgusu ve 2 yeni kişi işlemi içerir. Toplam 780 başarılı iş ve 126 kalite hatası vardır. Başarılı 780 işin tamamında <code>cuda:0</code>, aynı ECAPA modeli ve sabit model revizyonu, <code>.55 / .45 / .10</code> karar politikası ve izin verilen ön işleme sürümü doğrulandı: 772 <code>vad-windows-v1</code>, 8 <code>vad-packed-fallback-v1</code>, 0 eksik/desteklenmeyen sürüm.

   | Kaynak katmanı | Bilinen doğru / planlanan | Bilinmeyen ret / planlanan | Bilinen / bilinmeyen kalite hatası |
   |---|---:|---:|---:|
   | Kalibrasyon <code>dev-clean</code> | 60 / 75 | 56 / 60 | 7 / 4 |
   | Kalibrasyon <code>dev-other</code> | 51 / 75 | 33 / 40 | 11 / 3 |
   | Tarihsel <code>test-clean</code> | 45 / 72 | 57 / 70 | 9 / 13 |
   | Tarihsel <code>test-other</code> | 33 / 78 | 24 / 30 | 15 / 6 |
   | Yeni <code>train-clean-100</code> | 116 / 150 | 94 / 100 | 10 / 5 |

   Bağımsız denetim; manifestten beklenen işlemleri, tekil işler/profiller, kaynak kayıt eşleşmeleri, başarılı ve başarısız sonuçlar, tüm paydalar/oranlar, kaynak katmanları, kişi kümeleriyle bootstrap aralıkları, süre özetleri, yeni kişinin geri dönüşü ve üç özel sonuç dosyasının yayımlanmış özetlerindeki SHA-256 değerlerini kapsar.
3. Maddeler:

   **KUSUR** — yok

   **TUZAK**

   M1 Planlanan 50 kişi, 50 kişinin sisteme kaydedildiği anlamına gelmez; gerçek profil sayıları 40, 29 ve 40'tır. Kalite hataları planlanan sorgu paydasında tutulmuştur.

   M2 Bilinmeyen kalite hataları başarılı ret sayılmamıştır: gözlenen yanlış kabul her koşumda 0/100; bilinmeyen sonuçların eksikliği için en kötü durum üst sınırları sırasıyla %7, %19 ve %5'tir. Bunlar nüfus genellemesi için güven aralığı değildir.

   M3 Tarihsel %52 ile yeni temiz kümedeki %77,33 farklı kişi/kayıt koşullarından gelir; aradaki fark eşleşmiş bir iyileşme ölçümü değildir.

   **GÖZLEM**

   M4 Aynı tarihsel manifestte 302 kayıt çifti doğrulandı: doğru tanıma 77/150 → 78/150, kayıtlı profil 29 → 29; önceki 77 doğru tanımanın hiçbiri kaybedilmedi, önceki başarılı kararların tamamı korundu.

   M5 Kalibrasyonun 111/150 doğru tanıması, 40 profili ve 18/7 bilinen/bilinmeyen kalite hatası kabul edilen tanılama sonucuyla eşleşti; tarihsel artış yalnız bir ek doğru tanımadır.

   M6 Yeni kümenin 70 kişisi, önceki dört kaynak bölümündeki 146 kişinin tümünden ayrıdır; 605 kaynak söylem tekildir, rol bölümleri ayrıdır ve dondurulmuş hazırlık manifesti değişmemiştir.

   M7 Yayım manifestindeki 21 yerel dosyanın hashleri değişmemiştir. İşler model/revizyon/cihaz/ön işleme sürümünü taşır; iş başına OCI imaj hashini taşımaz. İmaj kimliği ayrı dağıtım kanıtında doğruludur.

   **AÇIK**

   M8 Tarihsel yeni kişinin hem kaydı hem geri dönüş sorgusu kalite hatası verdi; bu akış üç koşumun tamamında başarılı değildir. Yeni temiz kümede de 10/50 profil kaydı ve 10/150 bilinen sorgu kalite nedeniyle tamamlanamadı.

   M9 İngilizce birleştirilmiş okuma kayıtları Türkçe toplantı, uzun kayıt, eşzamanlı konuşma, gerçek zamanlı çalışma veya farklı mikrofon/oturum doğruluğunu kanıtlamaz; yüksek güvenilirlik iddiası desteklenmez.

   **YAN-ETKİ**

   M10 Yalnız anonim denetim JSON'u, bu rapor ve yok sayılan <code>outputs/quality-improvement/</code> altında geçici denetim aracı/ara özeti yazıldı; uygulama, veri, model, yapılandırma ve hizmetler değiştirilmedi.
