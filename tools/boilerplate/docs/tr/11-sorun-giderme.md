# Sorun giderme

| Belirti | Olası neden | Güvenli kontrol / çözüm |
|---|---|---|
| Proje komutu “project root” bulamıyor | Yanlış dizin veya eksik `.kt-scaffold` manifesti | `--target-dir` değerini açık verin; dizinde `.kt-scaffold/answers.yml` olduğunu doğrulayın |
| `domain`, `page`, `schema` veya `scenario` PRD'yi reddediyor | Yol yanlış ya da PRD hâlâ Draft | `spec_path` biçimini ve tam `Status: Accepted` satırını insan kararıyla doğrulayın |
| `update` conflict döndürüyor | Managed dosya kullanıcı tarafından değiştirildi | Dosyayı overwrite etmeyin; canonical davranış ile kabul edilmiş ürün ihtiyacını semantik birleştirin |
| `render --mode check` başarısız | Client projeksiyonu source rules'tan drift etti | Kaynak `rules/` değişikliğini doğrulayın, sonra `render --mode write` ve drift check çalıştırın |
| `gate` project code execution'ı reddediyor | Açık güven onayı yok | Hedef repo ve diff'i inceleyin; güveniyorsanız `--allow-project-code-execution` verin |
| Gate exit code 0 olsa da evidence oluşmuyor | `KT_GATE_*` step/test satırları eksik veya tutarsız | Project-owned betiği düzeltin; yalnız exit code'u kanıt saymayın |
| Browser E2E hemen hata veriyor | Generated failing guard henüz gerçek assertion ile değiştirilmedi | Acceptance noktasını gerçek UI üzerinden doğrulayan assertion yazın |
| Offline bundle doğrulanmıyor | Bundle eksik, platform yanlış veya admission digest uyuşmuyor | Bundle ve trust anchor'ı onaylı kanaldan yeniden alın; kontrolü bypass etmeyin |
| Streamable HTTP non-loopback bind olmuyor | Doğrudan dış listener güvenlik gereği reddediliyor | MCP'yi loopback'te çalıştırıp banka gateway sidecar üzerinden yayınlayın |
| `project_create` görünmüyor | İstemci HTTP governance kullanıyor veya local stdio'da `--workspace-root` yok | Trusted local stdio komutunu açık workspace'e karşı kaydedin |
| Yerel oluşturma reddediliyor | Kök güvensiz, symlink, sahiplenilmemiş/dolu, partial veya edited | Hedefi koruyun; exact completed scaffold veya yeni boş dizinle deneyin |
| MCP update tüm yerel değişiklikleri görmüyor | Yalnız bounded project manifest gönderilir | Artifact önerisini yerel diff ile ajan karşılaştırsın; kaynak ağacı MCP'ye göndermeyin |
| Yeni ajan session'ı bağlamı kaybetti | Karar yalnız chat geçmişindeydi | PRD/plan/tasks, decision log ve manifesti güncelleyin; yeni session'a bunları okutun |
| Yerel model basit kod yazıyor fakat uzun görevde sapıyor | Context yönetimi, model boyutu/quantization veya repo hafızası yetersiz | Görevi accepted tasks'a bölün; aynı kabul matrisini model/donanım kombinasyonunda yeniden çalıştırın |

## Teşhis sırası

1. Çalışma ağacı ve hedef dizini okuyun; kullanıcı değişikliklerini koruyun.
2. `kt-scaffold --version` ile generator sürümünü kaydedin.
3. `technology-profile.yml` ve `.kt-scaffold/answers.yml` uyumunu kontrol edin.
4. `python3 scripts/check-governance-drift.py` ve `python3 scripts/check-config-sync.py` çalıştırın.
5. Sorunu en dar CLI komutu veya testle yeniden üretin.
6. Çalıştırılan komut, exit code, stabil evidence satırları ve ortam kısıtını birlikte raporlayın.

Secret, müşteri verisi veya kapalı ağ adresini hata raporuna kopyalamayın. Gerekirse redacted,
yeniden üretilebilir fixture kullanın.
