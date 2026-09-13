# Koşum raporu — 2026-09-13 · Yavaş metin incelemesinin halka açık proxy tarafından erken kesilmesi

1. Sonuç: 60 saniyelik erken kesilme yeniden üretildi ve düzeltildi; yerel/Spark önizlemesi 65 saniyelik gerçek HTTP yanıtını iletti — birim 16 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows Docker Desktop, kurulu nginx image, Python 3.12 test yürütücüsü ve gerçek Helm; profil `kt-vibecoding-python-web-v2`.

   | Koşum | Gözlenen sonuç |
   |---|---|
   | `pytest tests/test_text_review_public_timeout.py -q -o addopts= --junitxml outputs/2026-09-13-contextual-transcript-review/runtime-timeout-red.xml` | Kırmızı: önizleme 60,1 saniyede HTTP 504; 1 başarısız, toplam 61,81 saniye. |
   | `pytest tests/test_text_review_chart.py -q -o addopts=` kırmızı | 7 başarılı / 1 başarısız: etkin Ingress'te 110 saniye anotasyonu eksik. |
   | Aynı gerçek HTTP testi, `runtime-timeout-green.xml` | 1 başarılı, toplam 67,31 saniye; iki modda önizleme HTTP 200, iki sıradan API kontrolü HTTP 504. |
   | `pytest tests/test_text_review_chart.py tests/test_text_review_proxy.py tests/test_text_review_startup.py -q -o addopts= --junitxml outputs/2026-09-13-contextual-transcript-review/runtime-timeout-regression.xml` | 15 başarılı, 0 atlanan; 6,58 saniye. |
   | `scripts/render-charts.sh` | 46 kaynak × 2 normal ve 47 kaynak × 2 toplantı fikstürü başarılı. |
   | Etkin nginx dosyasında `nginx -t -c ...` ve `nginx -s reload -c ...` | 17:14:13 UTC'de geçerli yapılandırma ve başarılı zarif yeniden yükleme. |

3. Maddeler:

   **KUSUR**

   M1 Halka açık `/api/` proxy'si varsayılan 60 saniyeyi kullanıyor, uygulamanın 100 saniyelik sınırından önce önizlemeyi kesiyordu; yalnız önizleme yolu için 110 saniye eklendi (`nginx.local.conf`, `test_text_review_public_timeout.py`; [nginx belgesi](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_read_timeout)).

   M2 Etkin Kubernetes arka uç Ingress'i de erken kesebilirdi; `textReview.enabled` açıkken mevcut Ingress'e 110 saniyelik okuma anotasyonu eklendi (`test_text_review_chart.py`).

   **TUZAK**

   M3 İlk canlı yeniden yükleme denemesinde PowerShell son satıra CR ekledi; nginx dosya adı hatası verdi. Bitiş yorumuyla düzeltilen sabit stdin komutu başarılı oldu; süreç yeniden başlatılmadı.

   M4 Küme anotasyonu arka ucun `/api` Ingress'ini kapsar; yerel düzeltme yalnız önizleme yoludur. Prefix eşleştirmesi korundu; regex/snippet eklenmedi ([regex etkisi](https://kubernetes.github.io/ingress-nginx/user-guide/nginx-configuration/annotations/#use-regex), [zaman sınırı anotasyonları](https://kubernetes.github.io/ingress-nginx/user-guide/nginx-configuration/annotations/#custom-timeouts)).

   **GÖZLEM**

   M5 Test gerçek kaynak nginx yapılandırmasını kullanır; yalnız upstream adresleri yerel, yavaş HTTP fikstürüne yönlendirilir. Yerel ve Spark istekleri paralel, model/uygulama verisi kullanılmadan çalıştı.

   M6 Diğer yerel API yolları 60 saniyelik sınırı korudu; özel 9080/9081 köprüleri ve başlatıcı regresyonları geçti.

   **AÇIK**

   M7 Gerçek Kubernetes denetleyicisinde gecikmeli istek çalıştırılmadı; burada kanıt gerçek Helm çıktısıdır. Canlı model/tarayıcı yeniden denemesi ana teslimin ayrı kanıtıdır.

   **YAN-ETKİ**

   M8 Yalnız nginx yapılandırması, koşullu Ingress anotasyonu, ilgili test/belgeler değişti. Canlı nginx zarif biçimde yeniden yüklendi; model, ortam değişkeni, güvenlik duvarı ve çalışan arka uç değiştirilmedi.

   M9 İki geçici nginx konteyneri ve loopback HTTP fikstürü test sonunda temizlendi; ham test raporları Git dışındaki `outputs/` altında tutuldu.
