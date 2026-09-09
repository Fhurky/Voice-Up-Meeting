# MCP araç referansı

Bütün şemalar bildirilmemiş argümanları reddeder. Yerel stdio ve uzak HTTP yüzeylerinin yetkileri
bilinçli olarak farklıdır.

## `project_start` / `proje_baslat` prompt'u

Yalnız yerel stdio'da bulunur. Eksik iş amacı/domain/ad bilgisini toplar, tek özet ve onay gösterir,
sonra `project_create` / `proje_olustur` çağırır. Hedef dizin, teknoloji, URL, archive, applicator,
komut veya secret sormaz.

## `project_create` / `proje_olustur`

Yalnız yerel stdio'da bulunur. Girdi product intent, primary domain, ürün adı/slug, opsiyonel türetilen
prefix'ler, tenant header, locales, observability ve opsiyonel `agent_clients` içerir. Workspace kökü
server başlangıcında sabitlenir ve tool girdisi değildir.

Önceden yüklenmiş generator tam ağacı in-process oluşturur. Bounded sonuç `local-mcp-observed`
receipt, `created|unchanged` durumu, dosya/entry sayıları ve eşit expected/observed tree digest'leri
içerir. Source gövdesi, indirme referansı veya shell komutu dönmez.

## `project_blueprint` / `proje_plani`

İki yüzeyde de bulunur. Zorunlu girdiler `project_intent` ve lowercase-hyphenated `primary_domain`;
ürün kimliği, prefix'ler, tenant header, locales ve observability opsiyoneldir. Bounded metadata döner,
dosya oluşturmaz.

## `governance_catalog` / `yonetisim_katalogu`

Gövdesiz artifact metadata listeler. `kind`, `authority` ve `scope` filtreleri opsiyoneldir.

## `governance_artifacts_get` / `yonetisim_ogelerini_getir`

Benzersiz ve boş olmayan `ids` listesini alır; yalnız açıkça seçilen public gövdeleri döndürür.

## `governance_update_check` / `yonetisim_guncellemelerini_kontrol_et`

Bounded `.kt-scaffold/project-manifest.json` metadata'sını alır ve deterministik
`GovernanceUpdateProposal` döndürür. Workspace'i incelemez.

## `reconciliation_validate` / `uyumlastirmayi_dogrula`

Her proposal item'ı için bir kararı doğrular; workspace-execution kanıtı değil,
`local-agent-attested` karar receipt'i döndürür.

Streamable HTTP yalnız son beş iki-dilli blueprint/governance çiftini sunar; prompt veya oluşturma
aracı yoktur. Ayrıntı: [MCP kullanım rehberi](../07-mcp-kullanim-rehberi.md).
