# Manifest referansı

| Dosya | İçerik | MCP'ye gider mi? |
|---|---|---|
| `.kt-scaffold/answers.yml` | Secret olmayan scaffold girdileri ve generator sürümü | Hayır |
| `.kt-scaffold/project-manifest.json` | Blueprint/governance sürümü, intent/domain, sabit profiller, locales ve content-addressed artifact envanteri | Evet, `governance_update_check` girdisi olarak |
| `.kt-scaffold/managed-manifest.json` | CLI'nin yönettiği yerel dosyaların state/digest bilgisi | Hayır |
| `.kt-scaffold/evidence.json` | Yerel/runner test provenance, tier ve gözlenen sayılar | Hayır |
| `dependency-admission.json` | Doğrudan package, OCI ve workflow action kabul envanteri | Hayır |
| `e2e/QUALITY_MANIFEST.md` | Browser suite, scenario ve acceptance izleri | Hayır |

`scripts/export-project-metadata.py` yalnız `project-manifest.json` bounded alanlarını stdout'a
çıkarır; workspace walk yapmaz. Bu çıktı yine de ürün intent'i ve iç artifact kimlikleri içerdiği için
yalnız onaylı banka MCP endpoint'ine gönderilmelidir.

Manifest sürüm/digest ilerletme sırası: değişikliği uygula → yerel kapıları çalıştır → reconciliation
receipt al → kullanıcı/owner kabulünü kaydet → inventory'yi ilerlet. Önceden ilerletmek drift'i
gizler.
