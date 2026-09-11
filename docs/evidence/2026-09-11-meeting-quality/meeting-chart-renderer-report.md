# Koşum raporu — 2026-09-11 · Toplantı ve pilot Helm seçimleri gerçek render sınırında doğrulandı.

1. Sonuç: Son renderer paketi ve chart özdenetimi başarılı — birim 19 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan:

   | Ortam ve komut | Gözlenen sonuç |
   |---|---|
   | Windows proje Python 3.12 ortamı, ilk dar `pytest tests/test_meeting_chart_contract.py` seçimi | Uygulamadan önce 7 başarısız: 6 bozuk/eksik seçim kabul ediliyor, runtime seçimi chart değerlerine aktarılmıyordu |
   | Aynı ortam, uygulamadan sonra aynı 7 test | 7 başarılı |
   | Doğrudan PowerShell tam dosya koşumu | 7 başarılı, 3 başarısız, 9 kurulum hatası; alt süreç PATH'inde mevcut Helm bulunamadı |
   | Git Bash üzerinden `.venv/Scripts/python.exe -m pytest tests/test_meeting_chart_contract.py -q --tb=short`, mevcut `C:/Users/furko/bin/helm.exe` | 19 başarılı; gerçek Helm lint/template, pilot x86/ARM, toplantı x86 ve ARM toplantı reddi |
   | Sabit scaffold Python 3.13 ortamı, `scripts/render-charts.sh --self-test` | Pilot 46 kaynak × 2 overlay; toplantı 47 kaynak × 2 overlay başarılı; 9 bozuk toplantı çıktısı ve 4 bozuk seçim özdenetimde reddedildi |
   | `scripts/check-config-sync.py`, değişen renderer/test dosyalarında Ruff lint/format, `git diff --check` | Yapılandırma eşleme ve dar statik kontroller başarılı |

3. Maddeler:

   **KUSUR**

   M1 Overlay'de eksik/yanlış tipte/uyumsuz runtime seçimi reddedilmiyordu ve chart_values toplantı seçimini aktarmıyordu; yedi kırmızı testten sonra `render_charts.py` doğrulama ve aktarımı eklendi, testler geçti.

   M2 Önceki pilot-only render kontrolü toplantı modellerini/sağlık uçlarını kanıtlamıyordu; varsayılan kapı artık iki overlay'de hem kapalı pilotu hem açık x86 toplantı varyantını üretip doğrular.

   **TUZAK**

   M3 Bu Windows ortamında Helm mevcut fakat doğrudan PowerShell'in alt süreç PATH'inde yoktu; aynı testler mevcut Git Bash PATH'iyle geçti. Yeni araç veya sürüm kurulmadı; ilk ortam hatası korunur.

   M4 Model PVC'sinin çizilmesi içeriğinin hazırlanmış olduğunu göstermez. Gerçek model manifesti, imaj digest'i ve küme dağıtım bilgileri ayrı teslim girdileridir; fixture render bunları doğrulayamaz.

   **GÖZLEM**

   M5 Render denetimi model/sürüm seçiminin annotation ve açık ortam alanlarında eşitliğini, Linux amd64/tek GPU seçimini, iki salt okunur alt dizini, 4 GiB PVC'yi, çevrimdışı ayarları ve doğru startup/readiness/liveness yollarını denetler.

   M6 Mevcut pilot x86_64-cu128 ve aarch64-cu129 seçimleri, tek model PVC'si ve eski sağlık yollarıyla doğrulandı; aarch64 toplantı seçimi hem overlay hem doğrudan Helm sınırında reddedildi.

   **AÇIK**

   M7 [Önceki deployment raporundaki](deployment-report.md) gerçek lab/cluster ortam bilgilerinin eksikliği sürer. Bu koşum Kubernetes, Spark veya model doğruluğu için canlı kabul değildir; son tam profil kapısı ayrıca çalıştırılır.

   **YAN-ETKİ**

   M8 Bu alt görevde `scripts/render_charts.py` ve `tests/test_meeting_chart_contract.py` değişti; chart/overlay/Accepted Decision 17 dosyaları diğer görev sahibi tarafından eşzamanlı tamamlandı. Üretim container'ına, model verisine veya veritabanına dokunulmadı.
