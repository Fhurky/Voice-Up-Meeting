# Plan — Yerel yönetici için tek tıkla giriş

1. Requirement 1 / Decision 2–3: Backend config, auth repository/service/transport
   ve tipli yanıtları mevcut auth örüntüsünden türet; önce sınır testlerini kırmızı çalıştır.
2. Requirement 3: Gerçek PostgreSQL auth entegrasyonunda aynı hesap/tenant/JWT
   ve değişmeyen kayıtlar ile iptal edilen rolü doğrula; yeni migration yoktur.
3. Requirement 2–3: Sözleşme çıktısını `scripts/export-openapi.sh` ve
   `scripts/generate-types.sh` ile üret; auth servisi/context/login/TR/EN ve testleri tamamla.
4. Requirement 4: Örnek ayarlar ve yerel Compose'u, Mac/NVIDIA kurulum rehberlerini
   güncelle; config sync ile tek Secret dağıtım sınırını doğrula.
5. Kabul: Mevcut backend/frontend yerel servislerini yeni kodla çalıştır; model
   servisini değiştirmeden kayıtlı browser senaryosunu TR/EN uygula.
6. Kabul: Dar testler, `scripts/quality-gate.sh all`, `scripts/security-gate.sh`,
   hash/sır kapsamı ve sabit koşum raporundan sonra yetkilendirilen commit/push'u yap.
