# Koşum raporu — 2026-09-11 · Kişi eşlemeli metin ölçümünün ilk otomatik doğrulaması

1. Sonuç: Eksik, fazla ve kişisi belirsiz kelimeleri koruyan ölçüm geçti — birim 30 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Yerel Windows/Python 3.12, `kt-vibecoding-python-web-v2` araştırma aracı; `.venv/Scripts/python.exe -m pytest tests/test_meeting_metrics.py tests/test_score_meeting_transcript.py -q` → 21 hesaplama + 9 gerçek dosya/komut testi. İlgili dört dosyanın Ruff biçim/lint denetimi geçti.
3. Maddeler:
   **KUSUR**
   M1 Yeni ölçüm eksikti: ilk koşumda modül bulunamadı; komut aracı ilk koşumda 1 başarısız/8 başarılıydı. Her iki gerçek uygulama eklendikten sonra 30 test geçti.
   **TUZAK**
   M2 `cpWER` toplantı içi kişi etiketlerini en uygun biçimde eşler; kalıcı kimlik doğruluğu, konuşmacı zaman hatası veya zaman damgası doğruluğu değildir.
   M3 Standart ölçüm belirsiz akışı bir kişiye eşleyebilir; ayrı `assigned_only` maliyeti bunu yasaklar ve belirsiz kelimeleri ekleme olarak sayar.
   **GÖZLEM**
   M4 Bağımsız tam permütasyon hesaplaması küçük örneklerde aynı sonucu verdi; 50 akışlık test tam eşlemeyi doğruladı. Bu yapay test, 50 gerçek kişinin ses doğruluğu değildir.
   **AÇIK**
   M5 Güncel değişikliklerin tam profil kapısı, gerçek model karşılaştırması ve bağımsız ses ölçümü bu dar koşumda çalıştırılmadı.
   **YAN-ETKİ**
   M6 `meeting_metrics.py`, `score-meeting-transcript.py` ve iki test dosyası eklendi; kalıcı uygulama verisi, eşikler ve bağımlılıklar değişmedi.

Sonraki bağımsız karşılaştırmada, mevcut A/B/C kayıtlarının standart ve belirsiz
akışı ayrı cezalandıran toplam altı skoru tam permütasyon uygulamasıyla
değiştirme/silme/ekleme sayıları dahil aynı çıktı. Özel ham kanıt
`outputs/2026-09-11-accuracy-audit/cpwer-baseline/reusable-module-comparison.json`
içindedir; önceki 30 testin sayısına bu karşılaştırmalar eklenmemiştir.
