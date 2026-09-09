# MCP kullanım rehberi

Proje oluşturma ile merkezi yönetişim iki açık MCP yetki yüzeyi kullanır.

## Yerel proje oluşturma

Onaylı kurulu paketi stdio server olarak kaydedin ve açık workspace'e bağlayın:

~~~json
{
  "servers": {
    "kt": {
      "type": "stdio",
      "command": "kt-scaffold",
      "args": ["mcp", "--workspace-root", "${workspaceFolder}"]
    }
  }
}
~~~

Proje dizininin tamamen boş başlayabilmesi için user/organization kaydı tercih edin. Üretilen proje
MCP registration içermez.

`proje_baslat` prompt'unu seçin veya doğrudan `proje_olustur` çağırın. Tek iş özeti/onayından sonra
tool kurulu generator'ı in-process çalıştırır. Archive indirme, runtime applicator, terminal komutu
veya modelin yüzlerce dosyayı tek tek yazması yoktur. Expected ve observed tree digest'leri eşit bir
`local-mcp-observed` receipt zorunludur.

VS Code kayıtlı prompt'u `/mcp.kt.proje_baslat` olarak gösterebilir; bu yalnız client UI söz dizimidir.

Tool şemasında hedef dizin yoktur. Server başlangıcı kökü sabitler; istemci sandbox'ı da yalnız bu
kökü writable yapmalıdır. Güvensiz veya sahiplenilmemiş dolu kökler reddedilir. Exact retry
`unchanged` döner.

VS Code/Copilot scaffold için şu alanı gönderin:

~~~json
{"agent_clients": ["github-copilot-vscode"]}
~~~

Bu yalnız VS Code projection'larını inert store'a derler. Canlı `.github/agents/` activation ayrı
conformance/admission adımıdır.

## Uzak yönetişim

İç Streamable HTTP servisi yalnız blueprint ve governance operasyonlarını sunar:

~~~sh
kt-scaffold mcp --transport streamable-http \
  --host 127.0.0.1 --port 8000 --path /mcp
~~~

Project-start prompt'u, oluşturma tool'u, target path, bundle, applicator veya executable indirme
yoktur. Servis kurum OAuth/TLS gateway arkasında kalır; Rancher LAB sidecar yalnız taşıma doğrulama
sınırıdır.

## Yönetişim güncelleme akışı

1. Generated helper ile yalnız `.kt-scaffold/project-manifest.json` export edin.
2. `governance_update_check` çağırın.
3. Yalnız seçili değişen artifact'leri getirin.
4. Değişiklikleri yerelde uygulayıp kalite/veritabanı/browser kapılarını çalıştırın.
5. Her item için bir kararla `reconciliation_validate` çağırın.

Reconciliation receipt proje-execution kanıtı değildir.

Şema özeti: [MCP araçları](referans/mcp-araclari.md).
