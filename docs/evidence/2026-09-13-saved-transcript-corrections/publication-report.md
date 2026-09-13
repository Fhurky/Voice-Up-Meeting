# Koşum raporu — 2026-09-13 · İncelenmiş uygulama değişikliklerinin GitHub yayını

1. Sonuç: Uygulama commit'i GitHub `main` dalına gönderildi ve uzak hash yerel hash ile eşleşti — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows yerel Git; kullanıcı tarafından istenen mevcut `origin/main` yayını, dal değiştirme veya geçmişi yeniden yazma olmadan.

   | Kontrol / işlem | Gözlenen sonuç |
   |---|---|
   | Son aday envanteri | 317 dosya, 2.605.380 byte; altı yerel sır değeri yalnız bellekte karşılaştırıldı, eşleşme yok; büyük/özel artifact veya kimlik bilgisi deseni bulunmadı. |
   | Bağlantı ve diff | Eksik yerel Markdown hedefi yok; `git diff --check` başarılı. |
   | İndeks | Aday dosya hash'leri tekrar eşleşti; stage edilen 317 yol incelenen listeyle birebir aynı; `git diff --cached --check` başarılı. |
   | Uygulama commit'i | `5d47874e6d3eb6ce60da4bf5f83b1f2ef8d94512`; 317 dosya, 31.671 ekleme, 698 çıkarma. |
   | İlk `git push origin main` | Kayıtlı farklı hesabın yetkisi olmadığı için HTTP 403; başarılı sayılmadı. |
   | Kullanıcının `.env` tokenıyla push | Başarılı; kimlik bilgisi yalnız süreç ortamında kullanıldı, URL/komut argümanı/kalıcı Git ayarı veya loga yazılmadı. |
   | `git ls-remote --exit-code origin refs/heads/main` | `5d47874e6d3eb6ce60da4bf5f83b1f2ef8d94512`; `git rev-parse HEAD` ile aynı. |
   | Yayın sonrası çalışma ağacı | `git status --porcelain=v1` boş; bu kabul kaydı bundan sonra ayrı belge güncellemesi olarak yazıldı. |

   Bu rapor doğrulanmış uygulama commit'ini tanımlar; kendi sonradan oluşan
   belge commit'inin hash'ini önceden tahmin etmez. [Son profil kapısı](quality-report.md)
   aynı üretim kodunda 1.084 testi doğrulamıştır; yayın kaydı üretim kodunu değiştirmez.

3. Maddeler:

   **KUSUR** — yok

   **TUZAK**
   M1 Sistem Git hesabının yetki sorunu kalıcı kimlik ayarı değiştirilmeden aşıldı; sonraki ayrı manuel push, aynı kayıtlı hesabı kullanırsa yeniden yetki hatası verebilir.

   **GÖZLEM**
   M2 Yerel ve uzak uygulama commit'i eşleşti; daha önce istenmiş mikrofon, arayüz, Türkçe değerlendirme ve metin inceleme değişiklikleri bu yayınla birlikte gönderildi.

   **AÇIK**
   M3 Sınırlı sır/dosya incelemesi güvenlik taraması değildir; eksik güvenlik araçları ve canlı ortam sınırları [ana raporda](README.md) korunur.

   **YAN-ETKİ**
   M4 İncelenen dosyalar stage edildi, commit oluşturuldu ve uzak `main` ilerletildi; model ağırlıkları, sesler, veritabanı, özel çıktılar ve `.env` yayımlanmadı.
