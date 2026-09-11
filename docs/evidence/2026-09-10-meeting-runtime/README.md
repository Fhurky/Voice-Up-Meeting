# Koşum raporu — 2026-09-10 · Yerel toplantı bağımlılıklarının kaynak kabulü

1. Sonuç: Yerel x86_64 toplantı uzantısının 68 artifact'i bağımsız incelemeye ve gerçek byte doğrulamasına bağlandı; 211 koordinatlı kabul denetimi geçti — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 3; karar bekleyen: yok.
2. Koşulan: Windows yerel Python ile `scripts/check-dependency-admission.py`; 68 wheel için yeniden boyut/SHA-256 doğrulaması, bağımsız resmî metadata/kapanış ve upstream güvenlik düzeltmesi incelemesi. Profil: `kt-vibecoding-python-web-v2`. Kabul kimliği: `VOICEUP-MEETING-X86-ARTIFACT-SOURCES-2026-09-10`; envanter SHA-256: `403862bbd150130d09566193560c011863d2ece858028ca2ab5a487c39b14ef6`.
3. Maddeler:

   **KUSUR**

   M1 Araştırmadaki Lightning 2.6.5 paketlerinin CVE-2026-58659 bulgusu için iki paket 2.6.6 güvenlik düzeltmesiyle kabul edildi; [gerçek wheel kaynak kontrolü](production-candidate-actual-wheel-audit.json), [üretici sürüm kaydı](https://github.com/Lightning-AI/pytorch-lightning/releases/tag/2.6.6).

   **TUZAK**

   M2 GHSA-qqmf-gpg7-g8gw içindeki çelişkili sürüm aralığı sessizce bastırılmadı; gerçek wheel düzeltmesi immutable upstream ile eşleşiyor, bu inceleme tam güvenlik kapısı değildir.

   M3 Kök araştırma kilidi ürün otoritesi değildi; dokuz olgun ilk ürün adayı seçildi, mevcut 63 inference pini değiştirilmedi. [İlk adaylar](independent-candidate-source-review.json), [değişen adaylar](mature-production-candidate-replacements.json).

   **GÖZLEM**

   M4 131 birleşik dağıtım üzerindeki 252 aktif koşulda çatışma yok; [bağımsız kapanış](proposed-meeting-closure-review.json). Gerçek wheel metadata kontrolleri bu kaydı destekliyor.

   **AÇIK**

   M5 Tam konuşmayı metne çevirme ve toplantı HTTP/tarayıcı kabulü bu kaynak kabulünde atlandı; model hazırlığı ve ayrı canlı koşum gerektiriyor.

   M6 Yeni toplantı uzantısının yerel ARM64/Spark ve fiziksel Mac çalışması bu koşumda atlandı; x86_64 kanıtı o cihazların yerine geçmez.

   M7 Tam güvenlik tarayıcı kapısı bu kaynak kabulünde atlandı; bağımsız OSV sorguları ve kod incelemesi kapının yerine geçmez.

   **YAN-ETKİ**

   M8 Ürün otoriteleri, hash bağlı kanıtlar ve iki güvenlik istisnası `dependency-admission.json` içine kaydedildi; model servisi bu işlemle değiştirilmedi.
