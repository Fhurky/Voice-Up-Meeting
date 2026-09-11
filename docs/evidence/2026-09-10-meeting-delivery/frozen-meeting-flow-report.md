# Koşum raporu — 2026-09-11 · Sabit dört toplantı kaydı gerçek uygulamada beş kişiyi hatırladı ve yalnız altıncı kişiyi ekledi

1. Sonuç: Son kodla boş test hafızasında dört gerçek HTTP/model akışı geçti — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; canlı API 4 başarılı; karar bekleyen: yok.
2. Koşulan: Windows → Linux Python 3.13/FastAPI/PostgreSQL 17, RTX 4060 Laptop GPU; profil `kt-vibecoding-python-web-v2`. `scripts/run-meeting-evaluation.py` aynı dondurulmuş protokol ile `--repeat-complete --stop-after-upload-b`, gerçek backend/worker yeniden başlatması, ardından `--repeat-complete --resume` kullanılarak çalıştı. Tam komutlar, kaynak/model/kod özetleri ve sayılar [ölçüm kaydındadır](frozen-meeting-flow-results.json).

   | Kayıt | Süre | Gözlenen kişi | Kalıcı profil | Gözlenen sonuç | En düşük kaynak aralığı eşleşmesi |
   | --- | ---: | ---: | ---: | --- | ---: |
   | A | 182,03 sn | 5 | 5 | Beş yeni kişi kaydedildi ve adlandırıldı | %91,72 |
   | B | 94,62 sn | 5 | 5 | Yeniden başlatma sonrasında aynı beş profil/ad tanındı | %90,12 |
   | D | 88,94 sn | 6 | 5 | Kısa konuşan yeni kişi `profile_pending` kaldı | %95,12 |
   | C | 137,27 sn | 6 | 6 | Önceki beş kişi korundu, yalnız altıncı kişi eklendi | %97,77 |

3. Maddeler:
   **KUSUR**
   M1 İlk gerçek A koşumundaki 11 parçalı kişi/0 profil sorunu model reçetesi, kaynak zamanında eşleme ve bağımsız örnek doğrulamasıyla giderildi; önceki başarısız koşumlar [gözlem raporunda](failed-observation-report.md) korunur.
   M2 v6 C koşumunda uzun sözcük aralığı yanlış kişiye bağlandı; [Decision 18 düzeltmesi](sequential-word-report.md) sonrasında aynı kaynak ve yüzde 90 eşik değişmeden dört kayıt geçti.
   M3 Backend yeniden başlayınca Nginx eski IP'yi tutuyordu; aynı `scripts/stack.sh --mode local restart backend worker` artık geçerli ayarı sınayıp yeniden yüklüyor. Gerçek çıkış 0, HTTP 200 ve iki servis başlangıç zamanı değişimi kaydedildi.
   **TUZAK**
   M4 Bu örnekler sabit İngilizce sesli kitap kaynaklarından oluşturulmuş ayrı konuşmalardır; sonuç Türkçe Teams toplantısı, 50 kişi, konuşmacı ayrım hatası, kelime hata oranı veya genel kimlik F1 skoru değildir.
   M5 Belirsiz sözcüklerin metni korunur; A/B/D/C için sırasıyla 6,50/2,92/9,36/16,48 saniyelik transkript aralığı kişiye atanmadı. Kaynak eşleşmesi bu kapsam kaybını gizlememelidir.
   **GÖZLEM**
   M6 Model kişi sayısı ipucu kullanmadı. Her kayıtta yükleme hash'i ve yinelenen tamamlama isteği doğrulandı; B/D/C kimlikleri ve adları A'da kaydedilen kimliklerle karşılaştırıldı.
   M7 Bağımsız [örnek saflığı denetimi](../2026-09-11-meeting-quality/v8-source-purity-memory-report.md) yeni profil sesini kaynak aralıkları ve saklanan WAV hash'leriyle denetler; bu ölçü transkript eşleşmesinden ayrıdır.
   **AÇIK**
   M8 [Gerçek tarayıcı akışı](meeting-memory-browser-report.md) ve [310 saniyelik model girdisi](private310-gpu-report.md) ayrıca geçti; bağımsız güvenlik araç paketi ve temsil edici Türkçe/50 kişilik sahip kabulü açık kalır. Bu dört API geçişi onların yerine kullanılmaz.
   **YAN-ETKİ**
   M9 Yalnız değerlendirmeye ait boş tenant/normal kullanıcı, dört toplantı ve altı profil oluşturuldu. Ham ses, transkript, vektör ve kimlik bilgileri Git'e alınmadı; v6 başarısızlığı ve v7 ara koşumu yerel çıktıda korundu.
