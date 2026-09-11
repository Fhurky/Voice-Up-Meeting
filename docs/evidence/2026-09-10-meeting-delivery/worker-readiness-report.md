# Koşum raporu — 2026-09-11 · Model hazır olmadan toplantı işi sahiplenilmemesi

1. Sonuç: Başlangıç yarışı düzeltildi; yeni iş kabulü güncel model tarifini gerektiriyor — birim 57 başarılı / PostgreSQL bütünleşme 3 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`, yerel Docker backend ve geçici, göçleri uygulanıp kaldırılan PostgreSQL test veritabanı.

   | Koşum | Dosya / kapsam | Gözlenen sonuç |
   | --- | --- | --- |
   | İlk RED | Yeni `test_meeting_readiness.py` | Eksik `ready()` için 17 başarısız |
   | İlk birleşik GREEN | Readiness, HTTP adaptörü, worker sağlık ve `test_meeting_startup_readiness.py` | 59 başarılı, 5,29 saniye |
   | Tarif RED | `test_wrong_readiness_contract_is_visible_as_model_error[recipe_missing]` | 1 başarısız, 20 seçilmeyen |
   | Son birim GREEN | `test_meeting_readiness.py` 21, `test_meeting_inference.py` 35, `test_meeting_worker_health.py` 1 | 57 başarılı, 2,65 saniye |
   | Statik doğrulama | Değişen dört Python dosyası Black/Ruff, iki üretim dosyası mypy | Başarılı |

3. Maddeler:
   **KUSUR**
   M1 DÜZELTİLDİ: Bağlantı yokken veya geçici 503 sırasında model hazır olmadan claim alınabiliyordu; gerçek PostgreSQL üzerinde üç denemede kuyruk/deneme/token/parça `queued/0/0/0` kaldı, hazır olduğunda `finalizing/0/1/1` oldu.
   M2 DÜZELTİLDİ: Eski model kimliği yeni işi kabul edebiliyordu; `HttpMeetingAdapter.ready()` güncel `community-vbx-fa015-v1` tarifini zorunlu tutuyor.
   M3 DÜZELTİLDİ: Sıkıştırılmış bozuk yanıt geçici bağlantı sorunu sayılabiliyordu; sınırlı ve sıkıştırılmamış 16 KiB sözleşmesi ile kalıcı model hatası ayrılıyor.
   **TUZAK**
   M4 Hazır kabulünden sonraki gerçek model hataları mevcut sınırlı yeniden denemeyi korur; iki hata sonunda iş `failed/2/2/0` olur. Hazırlık denetimi yalnız iş kabulünü erteler.
   M5 İlk PostgreSQL koşumundaki iki başarısızlık testin tek parçalık iş için `running` beklemesiydi; gerçek sözleşme olan `finalizing` beklentisiyle düzeltildi, önceki çıktı korundu.
   **GÖZLEM**
   M6 Üretim döngüsü testi model açılırken pilot iş, iki temizlik yolu ve gerçek dosya sağlık işaretinin ilerlediğini doğruladı; yeni hazırlık metodu çekirdek sağlayıcı protokolüne eklenmedi.
   M7 Ham çıktılar `outputs/2026-09-10-meeting-delivery/worker-readiness-*.txt` altında korundu; kaynak kayıtları veya hizmet anahtarları rapora alınmadı.
   **AÇIK**
   M8 Bu rapor dar L1 kanıtıdır; son tarif eklemesinden sonra tam kalite kapısı ve çalışan uygulama doğrulaması ana teslim koşumunda kaydedilecektir. Üç PostgreSQL testi tarif eklemesinden önce geçen birleşik koşumdandır.
   **YAN-ETKİ**
   M9 Requirement 4, plan ve görev kaydı güncellendi; hazır olma adaptörü, üretim döngüsü ve iki test dosyası eklendi/değişti. Yalnız koşuma ait geçici test veritabanı oluşturulup kaldırıldı.
