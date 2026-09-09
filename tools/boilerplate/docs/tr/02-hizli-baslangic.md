# Hızlı başlangıç

Bu akış yerel CLI ile deterministik bir proje üretir, ilk PRD'yi oluşturur ve kalite kanıtına kadar
olan sınırları gösterir. Komutları kurumunuzun onaylı Python/wheel/OCI dağıtımıyla çalıştırın; kapalı
ağda genel paket indeksine çıkmayın.

## 1. CLI'yi doğrulayın

Boilerplate geliştiricisi bu depoda şu ortamı kullanabilir:

~~~sh
python3.13 -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/kt-scaffold --version
~~~

Proje kullanıcıları bunun yerine bankanın yazılım tedarik zincirinden geçirilmiş, pinlenmiş
`kt-scaffold` wheel'ini veya OCI paketini kullanmalıdır. Python 3.13 gereklidir.

## 2. Boş dizinden proje üretin

~~~sh
kt-scaffold init \
  --target-dir ./payment-reconciliation \
  --intent "Build an internal payment reconciliation service" \
  --primary-domain payments \
  --product-name "Payment Reconciliation"
cd payment-reconciliation
~~~

`init` sabit Python/FastAPI ve SQLAlchemy/Alembic profilini çözer; başka backend seçimi sunmaz. Sonuç
JSON'u değişen dosyaları ve sonraki adımları bildirir. Başlıca çıktılar:

- `AGENTS.md`, `CLAUDE.md`, `.claude/`, `.codex/`, `.cursor/` — istemci projeksiyonları;
- `specs/payments/` — domain bağlamı, roadmap ve PRD alanı;
- `app/backend/`, `app/frontend/`, `schema/` — sabit uygulama profili;
- `scripts/` — bootstrap, veritabanı, drift, güvenlik, E2E ve kalite girişleri;
- `.kt-scaffold/` — answers, managed state, bounded project manifest ve kanıt kayıtları.

Commit etmeden önce ürün adı, intent, domain ve `technology-profile.yml` değerlerini gözden geçirin.

## 3. Platform temelini çalıştırın

Üretilen `README.md` ve kurumunuzun onaylı offline bundle kaydı yetkindir. Temel sıra:

~~~sh
scripts/bootstrap.sh
scripts/stack.sh up -d --build --wait
scripts/db.sh apply
scripts/create-super-admin.sh
scripts/quality-gate.sh all
~~~

Browser E2E için onaylı bundle yolunu ve `SHA256SUMS` kabul digest'ini sağlayın, ardından:

~~~sh
export KT_SCAFFOLD_OFFLINE_BUNDLE=/approved/bundles/<platform-matrix>
export KT_SCAFFOLD_OFFLINE_BUNDLE_SHA256=<bank-admission-sha256-of-SHA256SUMS>
scripts/e2e.sh auth
~~~

Bu değerleri repoya yazmayın. Gerçek yollar ve digest'ler banka ortamı tarafından sağlanır.

## 4. İlk iş kabiliyetini tanımlayın

~~~sh
kt-scaffold spec \
  --target-dir . \
  --domain payments \
  --capability transaction-search \
  --intent "Let an authorized operator find reconciliation transactions" \
  --mode comprehensive
~~~

Komut `spec_path` alanını döndürür; bu örnekte yol
`specs/payments/PRDs/001-transaction-search/PRD.md` olur. PRD'deki aktörleri, sınırları, güvenlik ve
veri etkisini, acceptance criteria'yı doldurun. İnsan incelemesi tamamlanınca yalnızca
`Status: Draft` satırını `Status: Accepted` yapın. Bu durum değişikliği iş kodu üretme yetkisidir;
ajan tek başına kabul kararı vermemelidir.

`plan.md` her etkilenen katmanı acceptance kriterlerine, `tasks.md` ise kontrol edilebilir çıktılara
bağlamalıdır. Akış `Spec → Plan → Tasks → Implement` sırasını korur.

## 5. Kabul edilmiş PRD'den dikey dilimi hazırlayın

~~~sh
SPEC_PATH=specs/payments/PRDs/001-transaction-search/PRD.md

kt-scaffold domain --target-dir . --spec-path "$SPEC_PATH" \
  --permission read=transaction_search:read
kt-scaffold schema --target-dir . --spec-path "$SPEC_PATH" \
  --change-summary "Add transaction search desired state" \
  --migration-name add-transaction-search
kt-scaffold page --target-dir . --spec-path "$SPEC_PATH" \
  --page transaction-search --route /transaction-search \
  --permission transaction_search:read
kt-scaffold scenario --target-dir . --spec-path "$SPEC_PATH" \
  --suite payments --scenario-title "Authorized transaction search" \
  --acceptance-point "Authorized operator sees matching transactions"
~~~

Bu komutlar tamamlanmış özellik iddia etmez. Özellikle browser senaryosu, acceptance metnini
çalıştırılabilir test saymaz ve gerçek assertion yazılana kadar bilinçli olarak başarısız olur.
Üretilen iskeleti PRD/plan/tasks doğrultusunda tamamlayın.

## 6. Kalite ve teslim kanıtını üretin

Doğrudan, repo tarafından sağlanan kapıyı çalıştırabilirsiniz:

~~~sh
scripts/quality-gate.sh all --include-browser
~~~

Aynı kapıyı CLI üzerinden çalıştırırken hedef depodaki project-owned betiğe güvendiğinizi açıkça
onaylamanız gerekir:

~~~sh
kt-scaffold gate --target-dir . --scope all --include-browser \
  --allow-project-code-execution
kt-scaffold done --target-dir . \
  --change-summary "Deliver transaction search vertical slice" \
  --claimed-tier L2
~~~

`done`, kaydedilmiş kanıtın desteklemediği bir tier'ı onaylamaz. L3 ayrıca ürün sahibinin temsilî
gerçek veriyle kabulünü gerektirir.

## MCP bu akışın neresinde?

Trusted local stdio MCP deterministik `project_create`; HTTP MCP ise `project_blueprint` ve
workspace-blind governance operasyonlarını sağlar. Hiçbiri modele scaffold'u yeniden yazdırmaz veya
executable kod indirmez. Yerel stdio ile CLI aynı digest'i üretmelidir. Ayrıntılı sınır ve
yapılandırma: [Local Project Factory ve uzak yönetişim MCP](../global-mcp.md).
