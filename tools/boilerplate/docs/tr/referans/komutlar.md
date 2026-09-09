# Komut referansı

Bu özet `src/kt_scaffold/cli.py` sözleşmesini açıklar. Kurulu sürümün kesin seçenekleri için
`kt-scaffold <command> --help` yetkindir. Bütün Türkçe alias'lar İngilizce komutla aynı uygulamayı
çağırır.

| Komut / alias | Zorunlu girdiler | Önemli seçenekler |
|---|---|---|
| `init` / `baslat` | `--target-dir`; etkileşimsiz kullanımda `--intent`, `--primary-domain` | `--answers`, `--product-name`, `--product-slug`, `--env-prefix`, `--api-prefix`, `--tenant-header`, `--locales`, `--[no-]observability`, tekrarlanabilir `--agent-client` |
| `update` / `guncelle` | Proje kökü | Tekrarlanabilir `--set key=value` |
| `rules` / `kurallar` | Proje kökü | `--scope`, `--path`, `--trigger always|path-match|on-demand` |
| `rule` / `kural` | Bir veya daha çok rule ID | `--target-dir` |
| `render` / `yansit` | Proje kökü | Mühendislik-yönetişimi projeksiyonları için tekrarlanabilir `--client`, inert Agent Platform çıktıları için tekrarlanabilir `--agent-client`, `--mode write|check` |
| `spec` / `spesifikasyon` | `--domain`, `--capability`, `--intent` | `--mode lean|comprehensive` |
| `domain` / `alan` | Kabul edilmiş `--spec-path` | `--[no-]tenant-scoped`, tekrarlanabilir `--permission key=value` |
| `page` / `sayfa` | `--spec-path`, `--page`, `--route` | `--permission` |
| `schema` / `sema` | `--spec-path`, `--change-summary`, `--migration-name` | `--target-dir` |
| `gate` / `kalite-kapisi` | Proje kökü | `--scope backend|frontend|all`, `--include-browser`, `--allow-project-code-execution`, `--phase execute|prepare|finalize` |
| `scenario` / `senaryo` | `--spec-path`, `--suite`, `--scenario-title`, en az bir `--acceptance-point` | Tekrarlanabilir acceptance point |
| `done` / `tamamla` | `--change-summary`, `--claimed-tier L0|L1|L2|L3` | `--target-dir` |
| `apply-bundle` / `paketi-uygula` | `--archive`, `--descriptor`, `--target-dir` | Yalnızca boş hedefe veya aynı bundle'ın birebir tekrarına uygulanır |
| `mcp` / `mbp` | Yok | `--transport stdio|streamable-http`, trusted local stdio creation için `--workspace-root`, `--host`, `--port`, `--path` |

`--agent-client`; `claude-code`, `codex`, `cursor` ve `github-copilot-vscode` değerlerini kabul eder.
Seçim inert çıktı yazar; runtime'ı aktive veya admit
etmez. `--workspace-root` creation yetkisini yalnız local stdio yüzeyine verir; Streamable HTTP bu
yetkiyi reddeder ve workspace-blind kalır.

## Ortak sonuç zarfı

Yerel operasyonlar en az şu alanları kullanır:

- `ok`: operasyonun sözleşmeye göre başarılı olup olmadığı;
- `changes`: created/updated/conflict gibi dosya sonuçları;
- `warnings`: başarı iddiasını sınırlayan veya kullanıcı kararı isteyen bilgiler;
- `next_steps`: yapılandırılmış sonraki yerel adımlar.

Operasyona özgü alanlar bu zarfa eklenir; örneğin `spec_path`, `scenario_path`, evidence counts veya
render edilen client listesi. Unknown input'u sessizce kabul eden entegrasyon yazmayın.

## Exit code

- `0`: `ok: true` veya uzun ömürlü MCP prosesinin normal sonlanması;
- `1`: operation çalıştı fakat sonucu `ok: false`;
- `2`: girdi, validation, dosya sistemi veya çalışma sözleşmesi hatası.

Shell otomasyonunda hem exit code'u hem JSON `ok/warnings/changes` alanlarını kontrol edin.
