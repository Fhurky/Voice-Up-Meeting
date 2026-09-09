# CLI kullanım rehberi

CLI, yerel ve deterministik uygulama yüzeyidir. Her komut tek satır, sıralı anahtarlı JSON sonucu
döndürür. Başarılı sonuç `ok: true`; sözleşme/girdi hatası çoğunlukla exit code 2; çözülmemiş
operation sonucu exit code 1 üretir. Otomasyon yalnızca insan mesajını değil bu yapılandırılmış sonucu
değerlendirmelidir.

## Komut aileleri

| İngilizce | Türkçe alias | Amaç |
|---|---|---|
| `init` | `baslat` | Boş dizinde deterministik scaffold oluşturur |
| `update` | `guncelle` | Answers değişikliğini managed dosyalara yerel olarak uygular |
| `rules` | `kurallar` | Kural envanterini filtreleyerek listeler |
| `rule` | `kural` | İstenen kural gövdelerini getirir |
| `render` | `yansit` | İstemci projeksiyonlarını yazar veya drift kontrol eder |
| `spec` | `spesifikasyon` | Draft PRD, plan, tasks ve roadmap kaydı üretir |
| `domain` | `alan` | Kabul edilmiş PRD'den backend dikey dilim iskeleti hazırlar |
| `page` | `sayfa` | Kabul edilmiş PRD'den yetki korumalı frontend page hazırlar |
| `schema` | `sema` | Kabul edilmiş PRD için desired-state/migration değişimini hazırlar |
| `gate` | `kalite-kapisi` | Yerel kalite kanıtını çalıştırır veya prepare/finalize eder |
| `scenario` | `senaryo` | Acceptance'a bağlı, başlangıçta failing browser senaryosu üretir |
| `done` | `tamamla` | Kaydedilmiş kanıta göre teslim seviyesi raporlar |

`mcp` / `mbp`, trusted local stdio yüzeyini veya workspace-blind HTTP governance yüzeyini başlatır;
yukarıdaki proje operasyon çiftlerinden biri değildir.

## Hedef dizin

Proje komutlarında `--target-dir` verilmezse CLI mevcut dizinden proje kökünü çözer. Otomasyonda
belirsizliği azaltmak için hedefi açık verin. `init` dışında mevcut bir scaffold manifesti olmayan
dizinde proje operasyonları başarısız olur.

~~~sh
kt-scaffold rules --target-dir ./payment-reconciliation --scope backend
kt-scaffold rule --target-dir ./payment-reconciliation 10-spec-first 50-quality-gate
kt-scaffold render --target-dir ./payment-reconciliation --mode check
~~~

## Güncelleme ve çakışma

~~~sh
kt-scaffold update --target-dir . --set product_name="New Product Name"
~~~

`update`, generator answers ve managed manifest üzerinden yerel dosya setini hesaplar. Kullanıcı
tarafından değiştirilmiş bir managed dosya güvenli birleştirilemiyorsa sonuçta conflict bildirir;
sessiz overwrite başarı sayılmaz. Sabit backend/persistence alanlarına alternatif değer verilmez.

## Kalite kapısında güven onayı

`gate --phase execute`, hedef projenin `scripts/quality-gate.sh` betiğini çalıştırabilir. CLI paketine
güvenmek, hedef repodaki project-owned betiğe otomatik güvenmek değildir:

~~~sh
kt-scaffold gate --target-dir . --scope all \
  --include-browser --allow-project-code-execution
~~~

Uzaktan yürütücüler prepare/finalize protokolünü kullanabilir: `prepare` challenge ve beklenen komutu
üretir; yürütücü ham çıktıyı dosyaya kaydeder; `finalize` bu çıktı, exit code ve challenge ile bounded
evidence üretir. Challenge veya kararlı `KT_GATE_*` satırları uyuşmazsa doğrulama başarısız olur.

Tam seçenekler için `kt-scaffold <command> --help` kullanın. Özet referans:
[Komutlar](referans/komutlar.md).
