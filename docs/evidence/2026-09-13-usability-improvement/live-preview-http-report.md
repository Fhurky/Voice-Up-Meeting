# Koşum raporu — 2026-09-13 · İki normal hesapta saklanan toplantı sesini gerçek HTTP üzerinden inceleme

1. Sonuç: Saklanan 12 toplantıda 36 farklı ses bölümü ve 12 tekrar kaynakla birebir eşleşti — gerçek HTTP 182 başarılı / birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`, Windows/Python 3.12 istemcisi → `http://127.0.0.1:8081` gerçek ters proxy → çalışan Python 3.13/FastAPI uygulaması. İki mevcut normal test hesabıyla `/auth/login` kullanıldı; JWT imal edilmedi, `super_admin` kullanılmadı. [Makine kanıtı](live-preview-http.json) anonim kaynak/çıktı SHA-256 değerlerini, kaynak kod kimliklerini ve 913 başarılı denetimin dökümünü içerir.

   | Doğrulama | Gözlenen sonuç |
   | --- | --- |
   | Normal oturum açma | 2/2 başarılı; her hesabın tenant/kullanıcı bağlamı kendi değişmez deney durumuyla eşit |
   | Kaynak ve mevcut sonuç okuma | 98/98 JSON GET; iki galeride ayrı ayrı 6 profil, toplam 12 başarılı ve kaynağı kullanılabilir toplantı |
   | Baş/orta/son kaynak sesi | Her kayıtta `[0,30)`, `[135,165)`, `[270,300)`; 36/36 bölümde mono PCM16/16 kHz, tam 480.000 kare, tam PCM ve kanonik WAV bayt eşitliği |
   | Tekrar okuma | Orta bölüm her kayıtta yeniden istendi; 12/12 aynı WAV baytı, içerik türü ve saklamama başlığı |
   | Başlık ve boyut | 48/48 ikili yanıt `audio/wav`, `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`; tam `Content-Length` ve 11.520.128 bayt üst sınırı |
   | Tenant/kimlik sınırı | Başka normal hesapla 12 kaynak isteği ve 2 bulunamayan kayıt 404; kimliksiz 2 istek 401; normal kullanıcının tenant başlığını değiştirmesi 2 istekte 403 |
   | Geçersiz zaman aralığı | İki hesapta toplam 16 istek 422 `invalid_audio_range`: eksik alan, negatif/boş aralık, 30 saniye aşımı, kaynak sonunu aşma, NaN ve sonsuzluk |
   | Değişmezlik | İki hesapta profil/kişi/metin/toplantı genel yanıtları önce/sonra birebir eşit; kaynakların API/protokol/yerel SHA-256 değerleri ve 12 dosyanın son hashleri eşit; galeri 6→6 |

   Komut:

   ```text
   .venv/Scripts/python.exe outputs/2026-09-13-usability-improvement/verify-live-preview.py
   ```

   Yürütücü mevcut `scripts/benchmark-local-pilot.py` içindeki döngüsel ağ adresiyle sınırlı, yönlendirmeyi reddeden `Api` istemcisini; `scripts/run-turkish-meeting-evaluation.py` içindeki değişmez protokol/durum denetimini kullanır. Kimlik bilgileri yalnız yerel UTF-8 özel dosyalardan okunur. Koşum yalnız iki kimlik doğrulama POST'u ve GET çağrıları yaptı; dosya yükleme, toplantı/iş başlatma, yeniden adlandırma veya silme isteği yoktur.

3. Maddeler:

   **KUSUR** — yok

   **TUZAK**

   M1 Bu kayıtlar önceki iki Türkçe deneyin aynı altı kişisi ve 12 saklanan beş dakikalık bölümüdür; 36 önizleme yeni konuşmacı veya yeni doğruluk deneyi değildir. Kontrol edilen benzersiz ses 18 dakika, kaynak toplamı 60 dakikadır.

   M2 182 başarı, beklenen güvenli retleri de kapsayan HTTP kabul noktası sayısıdır; 182 adet 200 yanıt anlamına gelmez. 913 denetim çoğunlukla başlık, sayfalama ve eşitlik değişmezleridir; bağımsız doğruluk örneği değildir.

   **GÖZLEM**

   M3 İlk/son genel yanıt hashleri JSON'da ayrı saklandı; hiçbir kullanıcı adı, parola, token, tenant/profil/toplantı kimliği veya ham transkript yayımlanmadığı ayrıca denetlendi. Kaynak ses ve özel deney dosyaları değiştirilmedi.

   M4 Canlı kaynakların hepsinde `source_available=true` ve başarılı önizleme gözlendi. Tam sona bitiş kabul edildi, sonu aşan aralık reddedildi; metin ve kişi sonuçları değişmedi.

   **AÇIK**

   M5 Bu hesaplarda canlı süresi dolmuş kaynak yoktur; API tam son kullanma zamanını yayımlamaz. Temizliğe bağlı olmadan 410 reddi ve metnin korunması [ayrı gerçek PostgreSQL/ASGI kanıtında](audio-preview-backend-report.md) doğrulandı; burada yeni bir canlı süre sonu olayı iddia edilmez.

   M6 HTTP genel yanıtları özel embedding/veritabanı satırlarının doğrudan denetimi değildir. Tarayıcı oynatıcısı, fiziksel hoparlör sesi ve kullanıcı kalite kabulü bu ayrı salt okunur koşumda gözlenmedi; bunlar ana teslimin ayrı kabul noktalarıdır.

   **YAN-ETKİ**

   M7 Yalnız yok sayılan yerel doğrulama yürütücüsü ve bu iki anonim kanıt dosyası oluşturuldu. Yeni toplantı, model işi, profil kaydı, şema/ayar/kaynak kod değişikliği veya test veritabanı oluşturulmadı.
