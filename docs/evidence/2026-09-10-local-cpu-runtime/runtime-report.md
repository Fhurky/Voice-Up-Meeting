# Koşum raporu — 2026-09-10 · Açık CPU çalışma profilleri ve backend yanıt sınırı.

1. Sonuç: T01 otomatik sınır kontrolleri geçti — birim 139 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`; Linux Python 3.13.14 üzerinde mevcut inference imajı, ağ kapalı, GPU verilmeden, kaynaklar salt okunur ve önceki kilitli saf Python test araçlarıyla; backend mevcut stack wrapper üzerinden sınandı.

   | Koşum | Gözlenen sonuç | Kanıt |
   | --- | --- | --- |
   | Inference kırmızı: runtime profiles + HTTP service | 23 başarısız, 54 başarılı, 0 atlama | [JUnit](runtime-red.xml), [çıktı](runtime-red.txt) |
   | Backend sınır kırmızı | 2 başarısız, 18 başarılı, 0 atlama; tekrar toplamı artırmaz | [JUnit](backend-boundary-red.xml), [ilk çıktı](backend-boundary-red.txt), [tekrar](backend-boundary-red-repeat.txt) |
   | Inference bütün testler | 119 başarılı, 0 atlama | [JUnit](runtime-green.xml), [çıktı](runtime-green.txt) |
   | Backend `tests/unit/test_speaker_boundaries.py` | 20 başarılı, 0 atlama | [JUnit](backend-boundary-green.xml), [çıktı](backend-boundary-green.txt) |
   | Inference dört sahipli dosyada Ruff lint/format | Başarılı | [Çıktı](runtime-static.txt) |
   | Mevcut kalite kapısının `backend_static` işlevi | Ruff/Black/isort başarılı; 67 dosya biçimi, 54 kaynakta mypy başarılı | [Çıktı](backend-boundary-static.txt) |

   Inference komutu: `docker run --rm --network none --read-only --tmpfs /tmp:rw,size=256m -v <workspace>:/workspace:ro -v <workspace>/outputs/public-speaker-evaluation/inference-test-tools-s49quli0:/test-tools:ro -v <evidence>:/evidence -e PYTHONPATH=/test-tools:/workspace/src:/workspace/app/inference -e PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 -e PYTHONDONTWRITEBYTECODE=1 -w /workspace voiceup-inference:pilot python -m pytest -q -p no:cacheprovider app/inference/tests --junitxml=/evidence/runtime-green.xml`.

   Backend yeşil komutu: `scripts/stack.sh exec -T backend sh -lc 'pytest -q tests/unit/test_speaker_boundaries.py --junitxml=/tmp/voiceup-cpu-boundary-green.xml'`. Statik geçiş, `scripts/quality-gate.sh` dosyasının ilk `run_step configuration validate_configuration` çağrısından önceki işlevlerini kullanan ve yalnız `backend_static` çağıran, sistem geçici dizinindeki `voiceup-cpu-backend-static.sh` ile çalıştı; profil kapısının tam geçişi değildir. Git Bash ortamında `outputs/local-tools` PATH başında, `MSYS2_ARG_CONV_EXCL=/tmp;/workspace` kullanıldı. Doğrudan inference lint/format komutları backend'in mevcut Python 3.13 sanal ortamındaki Ruff ile `--config app/inference/pyproject.toml` kullandı.

3. Maddeler:

   **KUSUR**
   M1 Açık `x86_64-cpu`/`aarch64-cpu` profili ve `device=cpu` çifti, Linux/mimari/`2.8.0+cpu`/`version.cuda is None` denetimi, CPU tensor sonucu ve iki model ısınması eklendi; backend aynı cihazı tipli HTTP sınırında kabul ediyor (DÜZELTİLDİ, runtime/HTTP/backend testleri).
   **TUZAK**
   M2 İlk backend JUnit argümanı Git Bash tarafından Windows yoluna çevrildi; yalnız oluşturulan tek XML'in mutlak yolu doğrulanıp bu kanıt dizinine taşındı. Yeşilde kapının `sh -lc` biçimi kullanıldı; ürün kaynağına bırakılmış çıktı yok.
   M3 Doğrudan Windows Ruff çağrısı üst dizin ayarından mevcut import bloğuna I001 verdi; importlar değiştirilmedi, kapının izole kopya komutu geçti. PowerShell'in başarılı Black stderr çıktısını `NativeCommandError` biçiminde göstermesi ham kayıtta korunur; kapı çıkışı 0'dır.
   **GÖZLEM**
   M4 CUDA varsayılanı, mimari/sürüm/gerçek GPU denetimi ve hatada CPU'ya geçmeme regresyonları geçti. CPU çıktısında GPU bellek ölçüsü yok; model/192 boyut/eşik/kalite politikası değişmedi, kamu OpenAPI cihaz alanı zaten `string` olduğundan üretilmiş sözleşme değişmedi.
   **AÇIK**
   M5 Bu paket imza kısıtlı test modelleriyle sınırları doğrular; gerçek CPU ECAPA/Silero çalışması, tam kalite kapısı ve Mac cihaz kabulü ayrı ana görev kanıtıdır. Buradan gerçek Mac veya yeni tanıma doğruluğu sonucu çıkarılmaz.
   **YAN-ETKİ**
   M6 Üç üretim dosyası ve üç test dosyası değişti; kanıt dosyaları, yalnız testlere ait geçici kapsayıcı/disk dosyaları üretildi. Sır dosyası, kullanıcı verisi, servis seçimi, model ağırlıkları veya Git yayını değiştirilmedi.
