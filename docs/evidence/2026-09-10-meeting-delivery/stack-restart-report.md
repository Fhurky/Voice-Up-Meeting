# Koşum raporu — 2026-09-11 · Servis yeniden başlatmasından sonra Nginx adreslerinin yenilenmesi

1. Sonuç: Başarılı upstream yeniden başlatmasından sonra etkin Nginx yapılandırması doğrulanıp yeniden yükleniyor — birim 62 başarılı / gerçek Docker HTTP 4 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`, Windows üzerinde Git Bash/pytest ve mevcut yerel Docker; ana uygulama servisleri değiştirilmeden ayrı kapalı ağlar kullanıldı.

   | Koşum | Komut / kapsam | Sonuç |
   | --- | --- | --- |
   | RED | `.venv/Scripts/python.exe -m pytest -q tests/test_stack_restart.py` | 15 başarısız, 18 başarılı |
   | GREEN | `RUN_DOCKER_TRANSPORT=1 .venv/Scripts/python.exe -m pytest tests/test_stack_restart.py tests/test_spark_transport_config.py tests/test_spark_startup.py tests/test_cpu_startup.py -k 'stack or nginx_reload' --junitxml=outputs/2026-09-10-meeting-delivery/stack-restart-green.xml` | 66 başarılı, 73 kapsam dışında seçilmeyen; 30,20 saniye |
   | Statik | Değişen üç test dosyasında Ruff biçimlendirme ve lint | Başarılı |

3. Maddeler:
   **KUSUR**
   M1 DÜZELTİLDİ: `scripts/stack.sh restart backend worker` sonrası Nginx eski IP adresini kullanarak 502/504 üretebiliyordu; başarılı backend/frontend veya bütün servis restart'ından sonra aynı modun etkin yapılandırması doğrulanıp kesintisiz yükleniyor.
   **TUZAK**
   M2 Başarısız restart yeniden yükleme başlatmaz; başarısız yeniden yükleme başarı döndürmez. Yalnız worker, `ps`, `stop`, `exec` ve yardım komutları ek işlem yapmaz.
   M3 Spark yeniden yüklemesi tek mevcut `/tmp/voiceup-spark.*/nginx.conf` dosyasını kullanır; dosya/dizin sembolik bağlantısı, eksik veya birden çok aday reddedilir. Şablon, ortam veya özel dinleyici yeniden üretilmez.
   **GÖZLEM**
   M4 Gerçek Docker testlerinde eski backend farklı IP ile değiştirildi; öncesindeki 502/504 ve yeniden yükleme sonrasındaki yeni yanıt görüldü. Geçersiz özel yapılandırma çalışan eski yapılandırmayı bozmadı; Spark 9080 dinleyicisi korundu.
   M5 `start-local.ps1` ve yeni shell sarmalayıcı komutları Local/Spark için ayrı ayrı gerçek Nginx üzerinde çalıştırıldı; CPU aynı standart etkin yapılandırmayı kullanırken mod/argv korunması gerçek shell testleriyle doğrulandı.
   M6 RED/GREEN çıktıları ve JUnit kaydı `outputs/2026-09-10-meeting-delivery/stack-restart-*` altında korundu; ilk başarısızlıklar kaldırılmadı.
   **AÇIK**
   M7 Bu değişikliğin gerçek HTTP kanıtı izole Nginx ortamına aittir; devam eden toplantıları etkilememek için ana uygulama yeniden başlatılmadı. Son tam profil kapısı ve ana uygulama yeniden başlatma gözlemi ana teslim raporunda izlenir.
   **YAN-ETKİ**
   M8 PRD çalışma paragrafı, plan ve T09.3 güncellendi; wrapper ve üç test dosyası değişti/eklendi. Koşuma ait ağlar/kapsayıcılar oluşturulup kaldırıldı; ana veritabanı, model, GPU ve özel proxy yapılandırması değiştirilmedi.
