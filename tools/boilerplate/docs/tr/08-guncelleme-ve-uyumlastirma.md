# Güncelleme ve uyumlaştırma

İki farklı güncelleme yolunu ayırın:

- **Yerel scaffold güncellemesi:** `kt-scaffold update`, answers ve generator sürümünden managed
  dosyaları hesaplar.
- **Merkezi yönetişim güncellemesi:** MCP `governance_update_check`, bounded proje metadata'sını
  kanonik artifact kataloğuyla karşılaştırır ve yerel ajana karar niyeti döndürür.

MCP, `update` komutunu uzaktan çağırmaz; CLI da merkezi katalog varmış gibi davranmaz.

## Yerel scaffold güncellemesi

1. Çalışma ağacını ve kullanıcı değişikliklerini inceleyin.
2. Onaylı yeni `kt-scaffold` sürümünü kapalı tedarik zincirinden alın.
3. Önce değişiklik kapsamını ve release evidence'ı okuyun.
4. `kt-scaffold update --target-dir ... --set key=value` çalıştırın.
5. Conflict ve warning'leri çözmeden başarı iddia etmeyin.
6. Client projeksiyon drift'i, config sync, dependency admission ve kalite kapısını çalıştırın.
7. Generator sürümü ve kabul kanıtını aynı değişiklik setinde kaydedin.

Backend/persistence sabit olduğundan bunları “update seçeneği” gibi değiştirmeye çalışmak geçerli bir
migration değildir. Böyle bir mimari değişiklik yeni profil tasarımı ve ayrı yönetişim kararı ister.

## Merkezi artifact uyumlaştırması

`governance_update_check` yalnız manifest inventory digest/version değerlerinden değişen veya
bilinmeyen artifact'leri çıkarır. Sonraki işlem:

1. önerideki `artifact_id`, `authority`, `required_behaviors` ve `local_instruction` alanlarını okuyun;
2. yalnız gerekli artifact gövdelerini getirin;
3. yerel dosyayı semantik olarak karşılaştırın;
4. her artifact için `accepted`, `adapted`, `deferred` veya `rejected` kararı ve gerekçe kaydedin;
5. `mandatory` adaptasyonda korunan davranışları açık listeleyin;
6. yerel kapıları çalıştırın;
7. karar setini `reconciliation_validate` ile doğrulatın;
8. receipt ve güncel inventory'yi ancak değişiklik kabulünden sonra saklayın.

Mandatory bir davranışı sessizce zayıflatmak, ertelemek veya reddetmek unresolved reconciliation'dır.
Recommended artifact gerekçeyle farklı ele alınabilir. Project-owned içerik merkezi gövdeyle
değiştirilmez.

## Çakışma ilkesi

Managed dosya ile proje ihtiyacı çelişirse otomatik overwrite yapmayın. Çakışmayı şu üç soruyla
sunup karar kaydedin:

- Hangi kanonik davranış zorunlu?
- Yerel değişiklik hangi ürün ihtiyacını ve kabul edilmiş PRD'yi karşılıyor?
- Her ikisini koruyan en küçük semantik adaptasyon nedir?

Sonuç, source rule'a veya kabul edilmiş PRD'ye taşınmalı; yalnız chat geçmişinde kalmamalıdır.
