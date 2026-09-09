# Spec, PRD, plan ve task yaşam döngüsü

## Yetki zinciri

Bir fikir doğrudan koda dönüşmez. Depodaki yetki zinciri:

`Domain context → Draft PRD → Human review → Accepted PRD → Plan → Tasks → Implementation → Evidence`

Her belge farklı bir soruyu yanıtlar:

- `DOMAIN.md`: Bu bounded context neye sahip, neye sahip değil?
- `PRD.md`: Hangi aktör için hangi ölçülebilir sonuç, sınır ve acceptance criteria isteniyor?
- `plan.md`: Kabul kriterlerini karşılamak için hangi katmanlar ve doğrulamalar değişecek?
- `tasks.md`: Sıralı, bağımsız kontrol edilebilir çıktılar neler?

## Domain ve roadmap

`init`, birincil domain için `specs/<domain>/DOMAIN.md` ve `roadmap.md` üretir. Yeni capability,
domain'in dilini ve sahiplik sınırını kullanmalıdır. Başka bir bounded context gerekiyorsa ayrı domain
tanımlayın; ortak bir “misc” alanı oluşturmayın.

## PRD üretme ve kabul

~~~sh
kt-scaffold spec --target-dir . \
  --domain payments \
  --capability transaction-search \
  --intent "Let an authorized operator find reconciliation transactions"
~~~

Yeni PRD `Status: Draft` ile gelir. Actor/outcome, invariants, authorization, veri/migration etkisi,
operasyonel risk ve acceptance criteria somutlaştırılır. Kapsamın bir parçasını belirsiz bir “later”
notuna park etmek yerine bağımsız teslim edilebiliyorsa ayrı PRD açılır.

İnceleme tamamlandığında insan sahibi `Status: Accepted` kararını kaydeder. `domain`, `page`, `schema`
ve `scenario` komutları draft veya eksik PRD'yi reddeder.

## Plan ve tasks

Plan, her acceptance kriterini etkilenen katmanlara bağlar: desired schema, migration, backend
domain/service/API, yetki, frontend, localization, gözlemlenebilirlik, unit/integration ve browser
kanıtı. Etkilenmeyen bir katman için sessizce atlamak yerine gerekçe yazılır.

Tasks sıralı ve çalıştırılabilir olmalıdır. Her task:

- üreteceği dosya veya davranışı;
- bağlı olduğu acceptance kriterini;
- bitişini kanıtlayan test/gate'i;
- bağımlı olduğu önceki task'i

belirtir. Plan ve tasks ikinci bir gereksinim deposu değildir; PRD ile çelişirse çalışma durur ve
çelişki sahibine sunulur.

## Uygulama ve senaryo

Kabul edilmiş aynı `spec_path`, backend, schema, page ve browser scenario işlemlerine verilir. Bu
iz, üretilen kod ile gereksinim arasındaki bağı korur. `scenario` yalnızca failing guard ve
acceptance açıklaması üretir; geliştirici gerçek browser assertion'larını yazmadan L2 iddia edemez.

## Tamamlama seviyeleri

| Seviye | Anlam |
|---|---|
| L0 | Değişiklik yazıldı; çalışma kanıtı yok |
| L1 | İlgili deterministik, unit ve integration davranışı çalıştırıldı ve geçti |
| L2 | Domain'e uygun gerçek sınır da geçti: HTTP/browser, gerçek MCP session veya exact client tuple |
| L3 | Sorumlu owner exact davranış/runtime kapsamını kayıtlı kanıtla kabul veya admit etti |

`kt-scaffold done`, `.kt-scaffold/evidence.json` içindeki gözlenen kanıttan daha yüksek seviyeyi
onaylamaz. Skipped test veya client-reported başarı, bağımsız yerel/runner kanıtıyla aynı değildir.

Generated iş capability'lerinde L2 normalde yukarıdaki canlı HTTP/browser yoludur. Project Factory ve
Agent Platform gerçek MCP ve exact-client conformance için kendi Accepted PRD tanımlarını kullanır;
bunlar generated uygulamanın browser iddiasını genişletmez.

Devam: [Ajan istemcileri](05-ajan-istemcileri.md).
