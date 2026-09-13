# Koşum raporu — 2026-09-13 · Zayıf referans, kayıt kapsamı ve gerçek kişi sayısı girdisi

1. Sonuç: İlk görünüm ve koşu sonu kapsamı ayrıldı; zayıf referans ve gerçek kişi sayısı girdisi yeni skor tablolarından önce görünüyor — birim 35 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Yerel Windows/Python 3.12, sabit `kt-vibecoding-python-web-v2`; `.venv/Scripts/python.exe -m pytest tests/test_experiment_ledger.py -q --junitxml=outputs/2026-09-13-turkish-evaluation/ledger-tests-hint-final.xml` → çıkış 0, 35 başarılı. Uyarı/sıralama beklentisi önce tek kırmızı testti; kişi sayısı alanının beş testi de uygulama öncesi kırmızıydı. Son kaynakta bütün testler ve Ruff denetimi geçti.
3. Maddeler:

   **KUSUR**

   M1 Real-TurnTurk ham `enrollment_coverage=len(identity_profiles)/6`, daha sonra kaydı tamamlanan kişileri içeriyordu; ilk görünüm kapsamı diye etiketlenmesi yanlıştı. Özel durumda yalnız toplu sayımla ilk görünüm 4/6, sonraki görünümde iki ek kayıt, son birikimli kayıt 6/6 doğrulandı.
   M2 Zayıf otomatik referans açıklaması tablonun sonundaydı ve metin/zaman damgası doğrulamasını açık söylemiyordu; yeni tabloların önünde otomatik etkinlik ve doğrulanmamış metin/zaman bilgisi belirtilir.

   **TUZAK**

   M3 Ham eski alan korunur; günlük yeni makine bloklarında birikimli oranı `cumulative_enrollment_coverage`, ilk görünümü `first_enrollment_coverage` olarak ayırır. Eski blokta ilk görünüm alanı yoksa yeni ölçülmüş gibi doldurulmaz.

   **GÖZLEM**

   M4 `test_meeting_coverage_distinguishes_first_appearance_from_later_enrollment`, 4/6 ilk ve 6/6 son kapsamı korur, çelişen ilk oranı reddeder. Kimlik precision/recall/F1 ve VoiceUp Score formülleri değişmedi.
   M5 `use_known_speaker_count` varsa yalnız gerçek boolean kabul edilir: true her toplantıda `expected_speakers=2`/`participant_count=2`, false ipucu yok olarak görünür; eski kayıtta olmayan alan uydurulmaz.

   **AÇIK**

   M6 Ana görevin son Türkçe aday koşusu ve bütün-günlük denetimi bu dar doğrulamadan ayrıdır; zayıf kaynak, insan etiketli toplantı kabulü değildir.

   **YAN-ETKİ**

   M7 Günlük adaptörü, testler ve kullanım açıklaması güncellendi. Kök `results.md` girişine eski görünümün anlamını düzelten açıklama eklendi; bütün tarihsel makine blokları ve ses/model gözlemleri korundu.
