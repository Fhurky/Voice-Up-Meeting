# Koşum raporu — 2026-09-11 · Elli kişilik eski/yeni koşumun ham model çıktılarını karşılaştırma

1. Sonuç: İki koşumun model çıktıları ve zamanlı metni birebir aynı, konuşmacı gruplaması farklı bulundu — birim 0 başarılı / checkpoint karşılaştırması 8 başarılı / zamanlı metin karşılaştırması 1 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Mevcut özel denetleyici üzerinden gerçek PostgreSQL `REPEATABLE READ, READ ONLY` transaction'ında eski ve yeni A kaydının sekizer sağlayıcı checkpoint'i alındı; yerel Windows/Python ile karşılaştırıldı. Profil `kt-vibecoding-python-web-v2`; özet ve karmalar `summary.json`, alan bazındaki ayrıntılar `comparison.json` ve `transcript-comparison.json` içindedir.
3. Maddeler:
   **KUSUR** — yok
   **TUZAK**
   M1 Sağlayıcının 5.914 ham sözcüğü kaynak pencerelerinin bağlam tekrarlarını içerir; yayınlanan 5.722 normalize sözcük aynı ölçüm değildir. Yalnız toplam sözcük sayısının eşitliğine dayanılmadı.
   **GÖZLEM**
   M2 Sekiz tam sağlayıcı belgesi birebir eşit: sözcük sırası/metni/başlangıcı/sonu/olasılığı, segmentler, native etiketler/dönüşler, VAD, model/sürüm/tarif ve tüm mevcut 192/256 vektörleri değişmedi; vektör farkı tam sıfırdır.
   M3 Yayınlanan 343 satırda sıra/başlangıç/son/metin/örtüşme/belirsizlik aynı; 5.722 normalize sözcüğün dizisi ve karması aynı. Konuşmacı grupları 51→52, satır çiftlerinin aynı kişiye ait olma ilişkisi 35 yerde farklıdır.
   M4 Böylece ana değerlendirmede bildirilen birleşik permütasyonlu sözcük hata sayısı 803→658 değişimi uygulamanın sonraki konuşmacı gruplamasına bağlanabilir; gözlenen model rastlantısallığı veya metin/zaman iyileşmesi yoktur.
   **AÇIK**
   M5 Bu karşılaştırma metrik hesabını yeniden çalıştırmaz ve checkpoint'e yazılmamış geçici model iç durumlarını gözlemlemez. Daha geniş model kararlılığı veya elli kişide genel doğruluk iddiası değildir.
   **YAN-ETKİ**
   M6 Yalnız yok sayılan yerel kanıt dizinine özel checkpoint belgeleri ve kimlik/ses/metin/vektör içermeyen sayısal özetler yazıldı; veri tabanı yazımı, model çağrısı, yeniden başlatma ve takip edilen kaynak değişikliği sıfırdır.
