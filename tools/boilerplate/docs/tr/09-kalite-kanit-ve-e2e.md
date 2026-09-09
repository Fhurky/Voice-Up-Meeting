# Kalite, kanıt ve E2E

## Temel ilke

Bir capability'nin durumu ajanın ifadesinden değil, gözlenen ve kaydedilen kontrolden türetilir.
“Kod yazıldı”, “test yazıldı” ve “test çalıştırılıp geçti” üç ayrı durumdur.

## Yerel kalite kapısı

`scripts/quality-gate.sh` onaylı giriş noktasıdır:

- `backend`: statik/backend kontrolleri ve read-only migration validation; canlı test DB akışından
  daha dardır;
- `frontend`: frontend'in profil-native kontrolleri;
- `all`: backend + frontend + canlı, benzersiz PostgreSQL test database'i, migration/drift ve ortak
  policy kontrolleri;
- `--include-browser`: admitted offline browser bundle ile E2E senaryolarını ekler.

Kapı stabil `KT_GATE_SCOPE`, `KT_GATE_STEP` ve `KT_GATE_TESTS` satırları üretir. Makine evidence bu
satırlardan kurulur; normal stdout insan incelemesi içindir.

## Evidence provenance

| Provenance | Anlam |
|---|---|
| `local-executed` | CLI, güveni açıkça onaylanmış proje betiğini yerelde çalıştırdı |
| `runner-attested` | Onaylı runner prepare/finalize challenge sözleşmesini tamamladı |
| `client-reported` | İstemci sonucu raporladı; bağımsız yürütme ile aynı güçte değildir |
| `unrecorded` | Çalıştırma kanıtı yok |

Exit code 0 tek başına yeterli değildir. Beklenen step'lerin başlaması ve `passed` ile bitmesi,
test sayıları, skipped/failure kayıtları ve challenge bütünlüğü de doğrulanır.

## Browser kanıtı

`kt-scaffold scenario`, kabul kriterlerini yorum satırı olarak taşıyan ve bilinçli failing guard
içeren bir dosya üretir. L2 için:

1. gerçek kullanıcı rolü ve izin sınırı kurulmalı;
2. browser gerçek UI üzerinden davranışı tetiklemeli;
3. sonuç ve önemli hata/boş/yükleniyor durumu executable assertion ile doğrulanmalı;
4. senaryo `e2e/QUALITY_MANIFEST.md` içindeki acceptance noktasıyla eşleşmeli;
5. admitted Playwright/Chromium bundle ile offline çalıştırılmalı.

Yalnız API çağrısı yapan veya acceptance prose'unu loglayan senaryo browser evidence değildir.

## Teslim raporu

~~~sh
kt-scaffold done --target-dir . \
  --change-summary "Deliver accepted capability" \
  --claimed-tier L2
~~~

Rapor değişikliği, supported/claimed tier'ı, observed test sayılarını ve provenance'ı birlikte
sunmalıdır. Çalıştırılamayan kontrol varsa nedenini ve bu nedenle hangi iddianın yapılamadığını açık
yazın.

Boilerplate'in kendi regresyon suite'i üretilen projenin kalite kapısının yerine geçmez. İkisi farklı
ürünleri doğrular.
