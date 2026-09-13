# Koşum raporu — 2026-09-11 · Modern toplantı çalışma alanı

1. Sonuç: Yeni görünüm gerçek uygulamada doğrulandı ve son kaynakta tam profil kapısı geçti — birim 691 başarılı / tarayıcı 22 başarılı / atlanan 2; karar bekleyen: yok.
2. Koşulan: Windows, Docker ve gerçek `http://127.0.0.1:8081` ters proxy kökeni; sabit profil `kt-vibecoding-python-web-v2`.

   | Kontrol | Komut veya kapsam | Gözlenen sonuç |
   |---|---|---|
   | Tam kalite kapısı | `scripts/quality-gate.sh all` | exit 0; backend 595/595, frontend 96/96 |
   | Statik ve sözleşme kapıları | Aynı tam kapının lint, format, tür, OpenAPI/tip, yapılandırma, bağımlılık kabulü, yönetişim ve chart adımları | Başarılı; geçici `_test` veritabanı oluşturuldu, migration uygulandı ve sonunda düşürüldü |
   | Dar ön yüz testleri | `scripts/stack.sh exec -T frontend npm test -- <dosyalar>` | Giriş/profil/iş/ses formu/sonuç: 42/42; toplantı: 18/18; ana sayfa: 7/7; bunlar final 96 testin alt kümeleridir |
   | İlk ana sayfa regresyonu | `HomePage.test.tsx`, uygulama öncesi | 1 başarılı, 2 beklendiği gibi başarısız; uygulama sonrasında 3/3 |
   | Kapsam değişimi regresyonu | `HomePage.test.tsx`, kullanıcı/tenant/izin değişimi | Önce 4 başarılı, 3 başarısız; düzeltmeden sonra 7/7 |
   | Kapalı seçenek regresyonu | `MeetingUploadForm.test.tsx` | Önce 3 başarılı, 1 başarısız; geçersiz alanın açılmasıyla 4/4 |
   | Ara bütünleştirme | Toplantı testleri, kataloglar henüz eklenmeden | 2 başarılı, 16 başarısız; eksik anahtarlar tamamlandığında 18/18 |
   | Gerçek salt okunur gezinme | Gerçek parola formundan sıradan hesap; 4 rota × TR/EN × 1440/390 CSS piksel | 16/16; etkin rota doğru, yazma formu yok, yatay taşma yok, görünür hata yok |
   | Gerçek toplantı sonucu | Ayrı sıradan yetkili hesap, önceki ölçümün B kaydı; TR/EN × 1440/390 CSS piksel | 4/4; 5 konuşmacı, 30 metin parçası, görünür belirsizlikler, klavyeyle metin başlığına odak, taşma yok |
   | Mobil giriş | TR/EN × 390 CSS piksel | 2/2; etiketli parola formu ve etkin yerel admin seçeneği, yatay taşma yok |
   | Ek gerçek etkileşimler | Yükleme formunda 5/4 ayrı sayı, dil değişimi; profil ad düzenleme/aç-vazgeç; içeriğe geçiş; tarihsel başarısız iş | Girdiler korundu; dosyasız gönderim kapalı; odak doğru; eski hata başarıya çevrilmedi |
   | Senaryo kaynağı | `node --check` → yeni 07 ve uyarlanan 04/05/auth02 | Dört sözdizimi kontrolü başarılı; çalıştırma kanıtı değildir |
   | Güvenlik | `scripts/security-gate.sh` | exit 2: `required offline security tool is unavailable: gitleaks` |
   | Kalıcı tarayıcı yürütücüsü | `scripts/e2e.sh speaker-identity` | exit 2: `KT_SCAFFOLD_OFFLINE_BUNDLE must point to an admitted, platform-matched bundle` |

3. Maddeler:

   **KUSUR**

   M1 Kullanıcı/tenant/okuma izni değişiminde eski ana sayfa verisinin kalması düzeltildi; `HomePage.tsx` ve dört kapsam regresyonu koruyor.

   M2 Gizli isteğe bağlı sayı alanı geçersiz olduğunda bölüm açılıyor; `MeetingUploadForm.test.tsx` doğruluyor.

   M3 Geçmiş iş bağlantısının simge/ad/tarih hizalaması gerçek görüntüde düzeltilip son derlemede doğrulandı; `globals.css`.

   **TUZAK**

   M4 Windows bağlı klasöründeki değişiklikleri çalışan Vite süreci ilk seferde algılamadı; mevcut `scripts/stack.sh restart frontend` ile yeni kaynak sunuldu.

   M5 Tarayıcı mevcut yüzde 80 yakınlaştırmasını korudu; boyut kontrolünde gerçek `innerWidth` 1440/390 olarak ölçüldü ve geçici viewport sonrasında sıfırlandı.

   M6 İlk tam kapı, ana sayfanın yeni kırmızı testleri yazılırken 595 backend/93 frontend başarı ve 3 hata gördü; son değişmeyen kaynakta bütün kapı yeniden geçti.

   **GÖZLEM**

   M7 Giriş, ana sayfa, yükleme, sonuç, profil, analiz ve iş görünümü ortak renk/boşluk/odak sistemi kullanıyor; yeni bağımlılık veya uzak görsel/yazı tipi yok.

   M8 Tarayıcı uyarı/hata kaydı 0; ters proxy penceresinde 61 HTTP 200 ve rota değişiminde iptal edilmiş 6 GET/499 görüldü. Günlük eşzamanlı yerel kullanımı da kapsar.

   M9 Sonuç incelemesi mevcut gerçek beş kişi kaydını kullandı; bu görsel doğrulama yeni model veya elli kişilik doğruluk kanıtı değildir.

   M10 Ürün görünümü için L2 canlı kanıt gözlendi. Son otomatik kapı 691 test geçti; aşağıdaki güvenlik/yürütücü sınırlamaları sürüm onayı gibi sunulmaz.

   **AÇIK**

   M11 Gitleaks bulunmadığı için güvenlik kapısı çalışamadı; sonraki Semgrep/Trivy adımları da yürütülmedi. Bu kapı başarılı sayılmadı.

   M12 Kabul edilmiş platform tarayıcı paketi olmadığından kalıcı senaryo yürütücüsü çalışmadı; 22 canlı kontrol bağlı gerçek tarayıcıyla ayrıca yapıldı.

   M13 L3 kullanıcı tasarım kabulü gözlenmedi; devam eden kayıt/model doğruluğu hedefleri bu sunum değişikliğinin sonucu değildir.

   **YAN-ETKİ**

   M14 Ön yüz yeniden başlatıldı, ters proxy yeniden yüklendi; test oturumları sonrasında başlangıçtaki yerel admin oturumu ve normal ekran boyutu geri getirildi.

   M15 008 PRD/plan/görevler, ortak tasarım, yerelleştirmeler, test ve senaryolar değişti; bu doğrulama yeni ses işi/profil oluşturmadı veya var olan iş/profili değiştirmedi.

   M16 Ham loglar ve ekran görüntüleri `outputs/2026-09-11-modern-workspace/` altında göz ardı edilen yerel kanıttır; kimlik bilgileri rapora alınmadı.

Yerel kanıtlar: `quality-gate-final.txt`, `browser-matrix.json`, `browser-extra.json`,
`browser-network.json`, `security.txt`, `e2e-wrapper.txt`, `home-scope-red.txt`,
`home-scope-green.txt` ve `result-<dil>-<genişlik>.png` dosyaları aynı çıktı dizinindedir.
Bu dizindeki ham ekranlar kişilerin görünen adlarını/metni içerebilir; sürüm kontrolüne eklenmez.

Kapsam: [Accepted 008 PRD](../../../specs/speaker-identity/PRDs/008-modern-workspace/PRD.md).
