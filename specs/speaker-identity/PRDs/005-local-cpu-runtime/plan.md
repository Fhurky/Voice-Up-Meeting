# Plan — Yerel CPU çalışma ortamı

1. Requirement 1: Inference config/models ve backend HTTP yanıt sınırına açık CPU
   profilleri ekle; mimari/sürüm denetimi ve CUDA regresyonunu kırmızı/yeşil test et.
2. Requirement 2: Resmi artifact metadata ile iki CPU manifesti hazırla; mevcut
   `prepare-spark-wheelhouse.py` ile ayrı hash kilitleri üret. Kabul kaydını inceleme
   kanıtıyla güncelle; pin yükseltme yok.
3. Requirement 3–4: `stack.sh`, CPU Compose/Dockerfile, model hazırlama ve tekrar
   çalışabilen kurulum/başlatıcıyı mevcut yardımcıları kullanarak tamamla.
4. Requirement 5: Mac rehberini README/Git rehberine bağla; pilot sınırı ve gerçek
   Mac kanıtının durumunu belirt.
5. Requirement 1–5: Odaklı testler, iki mimari Compose çözümleme, network-none CPU
   yükleme/HTTP akışı, `scripts/quality-gate.sh all`, `scripts/security-gate.sh` ve
   sabit koşum raporu. Mac L2/L3 yalnız cihazda gözlenebilir.
6. Requirement 3: Temiz GitHub kopyasında görülen Windows/Linux kural sıralama
   farkını `scripts/check-governance-drift.py` ve gerçek dosya tabanlı regresyon
   testiyle gider; kayıtlı kural/üretim özetlerini değiştirme. Ayrı Docker motorunda
   yeni ayar/veritabanı, kopyalanmış doğrulanmış model, ilk yönetici, profil kayıt/
   tanıma ve günlük yeniden başlatmada kalıcılık deneyiyle kurulumu doğrula.
