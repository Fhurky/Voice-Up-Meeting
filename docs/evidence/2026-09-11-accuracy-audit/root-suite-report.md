# Koşum raporu — 2026-09-11 · Araştırma araçları ve yerel kurulum sözleşmeleri

1. Sonuç: Sabitlenen kaynakların çalıştırılan araştırma/kurulum testleri geçti — birim 1.130 başarılı / tarayıcı 0 başarılı / atlanan 1; karar bekleyen: yok.
2. Koşulan: Windows/Python 3.12, `kt-vibecoding-python-web-v2`; son `pytest tests -q` → 1.116 başarılı, 0 başarısız, 0 hata, 15 atlanan; gerçek çıkış kodu 0, XML'de 1.131 vaka ve 341,333 saniye. Mevcut Helm dizini süreç PATH'ine eklendi. Ham XML/loglar: `outputs/2026-09-11-accuracy-audit/root-suite-frozen.*`. Önceki koşumun 1.099 başarılı / 3 başarısız / 9 kurulum hatası / 15 atlanan kaydı `root-suite-final.*`, ilgili 19 başarılı tekrar `root-chart-path-rerun.*` altında korunur; bunlar son toplama eklenmez.
3. Maddeler:
   **KUSUR** — yok
   **TUZAK**
   M1 İlk süreç `C:/Users/furko/bin` dizinini içermediği için 12 Helm vakası `FileNotFoundError` verdi; mevcut `helm.exe` arama yoluna eklenince 19 dosya testi geçti. Araç indirilmedi, test gevşetilmedi.
   **GÖZLEM**
   M2 İlk paketteki 15 atlamadan 13 Docker taşıma vakası ayrı gerçek Docker koşumunda, bir dosya sınırı vakası Linux'ta geçti; bunlar ilk koşumun sonucu değiştirilmeden toplam 1.130 farklı başarıya eklendi. [Ek koşum](additional-runtime-tests-report.md) ham kanıtı ve kalan tek Windows atlamasını açıklar.
   **AÇIK**
   M3 Bu kök test paketi gerçek model tanıma doğruluğu ölçmez; son backend/ön yüz kanıtı [tam kapı raporundadır](full-gate-report.md), GPU ve canlı hafıza deneyleri ayrı raporlanır.
   **YAN-ETKİ**
   M4 Yalnız test çıktıları ignore edilen dizine yazıldı ve ikinci alt sürecin PATH'i değişti; kalıcı ortam, model veya uygulama verisi değişmedi.
