# Koşum raporu — 2026-09-13 · Bilinen konuşmacı sayısı adayının istek sözleşmesi ve ilk kayıt kapsamı

1. Sonuç: Bilinen iki konuşmacı girdisi ve ölçüm ayrımı doğrulandı — birim 62 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2` deposu; Windows yerel araştırma Python 3.12. `.venv/Scripts/python.exe -m pytest tests/test_turkish_meeting_evaluation.py tests/test_run_meeting_evaluation.py -q --tb=short`: Türkçe 27, eski yürütücü 35 başarılı; ilk kırmızı Türkçe koşum 23 başarılı / 3 başarısız. İki yürütücü ve Türkçe test dosyasında `ruff check` ile `ruff format --check` geçti. Taban çizgisi tanısı mevcut altı tamamlanmış HTTP sonucundan salt okunur üretildi; bu alt görev GPU çıkarımı çalıştırmadı.
3. Maddeler:
   **KUSUR**
   M1 DÜZELTİLDİ: Eski `enrollment_coverage` ilk karşılaşmayı değil sonunda hafızaya alınan altı kişiyi sayıyordu; anlamı korunup ayrı `first_enrollment_coverage` eklendi. İki ilk kaydı geciken testte sonuçlar sırasıyla 6/6 ve 4/6.
   M2 DÜZELTİLDİ: Ortak yükleme gövdesinin doğrulanmamış protokol dilini devralması önlendi; temel yürütücü İngilizceyi korur, Türkçe alt sınıf dili açık seçer. Gerçek yerel HTTP sınırında dört gövde varyantı doğrulandı.
   **TUZAK**
   M3 Aday yalnız `--use-known-speaker-count` ile mevcut API'ye `expected_speakers=2` ve `participant_count=2` gönderir; varsayılan eski gövdeyi korur. Devam dosyası bu seçimi kilitler; eski dosyalar yalnız ipucusuz devam eder.
   M4 Karşılaştırma aynı altı sabit kalibrasyon kaydı ve ayrı boş deney tenantı kullanır; model, eşikler, metin normalizasyonu ve puan formülleri değişmez. Bu kalibrasyon karşılaştırması bağımsız test kümesi sonucu değildir.
   M5 Otomatik etkinlik, doğrulanmamış metin ve doğrulanmamış zaman referansı altın kimlik etiketi değildir. `unmapped` kabulü ihtiyatlı biçimde doğrulanamayan yanlış kabul olarak paydada kalır; kanıtlanmış biyometrik yanlış anlamına gelmez. Taban çizgisinde bu durum sıfırdır.
   **GÖZLEM**
   M6 rec02'de yeni kişi `insufficient_speech` ile bekledi: 10,893 saniye nitelikli konuşma ve iki küme vardı. Bilinen sayı ipucunun bu veri yetersizliğini gidermesi beklenmez; 20 saniyeyi aşma koşulu korunur.
   M7 rec03'te 55,700 saniye nitelikli yeni konuşmaya rağmen `reconciliation_ambiguous` görüldü; üçüncü kümenin nitelikli süresi sıfırdı. Aynı kişinin rec04'te kaydı önceki mevcut profilin kopyası olarak kanıtlanamaz: ilk kayıt gecikmiştir.
   M8 rec06'da bir kişinin ilk kaydı rec02'deki yetersizlikten sonra tamamlandı; diğer kişi tanınmış olsa da baskın referans payı %83,224 ile %90 eşleme eşiğinin altında kaldı. Üçüncü küme 10,383 saniye ve `insufficient_margin` taşıyordu.
   M9 Taban çizgisindeki bilinen kişi desteği 6, doğrulanmış doğru tanıma 3, yanlış kabul 0 ve kaçırma 3'tür; iki önceki kayıt yetersizliği ile bir referans bölünmesi bu üç kaçırmayı açıklar. İlk kayıt kapsamı 4/6, son birikimli kapsam 6/6'dır.
   **AÇIK**
   M10 İpucunun rec03 uzlaştırma ve rec06 bölünmesini iyileştirmesi henüz bu raporda gözlenmedi; eşli gerçek GPU deneyi kök görevde yürütülür. İnsan doğrulamalı zaman/kimlik altın referansı ve 50 kişi düzeyi bu altı görüşmeyle kanıtlanmaz.
   **YAN-ETKİ**
   M11 Accepted 009 Decision 11, iki yürütücü ve Türkçe testleri değiştirildi; testler geçici yerel HTTP sunucusu ve dosyalar kullandı. Mevcut deney anlık görüntüleri, model ağırlıkları ve ürün kullanıcı verisi değiştirilmedi.
   M12 Aday için dondurulan `scripts/run-turkish-meeting-evaluation.py` SHA-256: `ae4e5e4ff3e9d7c3d1ccbf89470c06c9834fabc7875f773760ae0214b885bc8e`; kaynak protokol SHA-256: `483e4810b3cd4559f9f00ce232deb12974e483be280e012f6117324911e7414c`.
