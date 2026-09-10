# Koşum raporu — 2026-09-09 · Veri deneyi öncesi tarayıcı ve araç hazırlığı

1. Sonuç: Altı canlı tarayıcı kontrolü geçti; iki kalıcı kapı ortam nedeniyle çalışamadı — birim 0 başarılı / tarayıcı 6 başarılı / atlanan 2; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`, Windows ve gerçek `http://127.0.0.1:8081` uygulaması; CUA tarayıcı akışı ve Git Bash giriş noktaları.

   | Kontrol | Sonuç |
   | --- | --- |
   | Korumalı rota ve gerçek giriş formu | Yeni, ayrı test tenant'ı hesabıyla başarılı. |
   | Türkçe ses analizi ekranı | Kapsam ve yükleme sınırları görünür. |
   | İngilizce ses analizi ekranı | Başlık ve tek konuşmacı açıklaması görünür. |
   | Bozuk WAV yüklemesi | Açık çözülebilirlik hatası, analiz işi oluşturulmadı. |
   | Dört saniyelik sessiz WAV | Kalıcı iş başarısız, kullanılabilir konuşma hatası görünür. |
   | Yenileme ve profil izolasyonu | Aynı başarısız iş URL'si korundu, test tenant'ında profil sayısı sıfır, konsol hata/uyarı kaydı yok. |
   | `scripts/security-gate.sh` | Exit 2; [ham çıktı](security-gate.txt). |
   | `scripts/e2e.sh speaker-identity` | Exit 2; [ham çıktı](permanent-browser.txt). |

3. Maddeler:

   **KUSUR**

   M1 PowerShell 7 başlangıcında geçerli tarih farklı tipe çevriliyordu; ayrı [regresyon raporunda](../2026-09-09-powershell-compatibility/README.md) düzeltildi ve iki motorda doğrulandı.

   **TUZAK**

   M2 Tarayıcı testi gerçek giriş formunu kullandı. Hesap ve fixture oluşturma yerel test hazırlığıdır; kullanıcı profilleri değiştirilmedi.

   **GÖZLEM**

   M3 Model/ses doğruluk deneyi henüz bu ön koşumda çalıştırılmadı; sessizlik kalite sınırını ölçer.

   **AÇIK**

   M4 Güvenlik kapısı için onaylı çevrimdışı gitleaks/Semgrep/Trivy paketi, kalıcı tarayıcı giriş noktası için onaylı Playwright paketi yok. Bu koşullar başarı sayılmadı; CUA kalıcı paket kanıtının yerine geçmez.

   **YAN-ETKİ**

   M5 Kalibrasyon, kör test ve tarayıcı için üç ayrı yerel hesap/tenant oluşturuldu. Özel kimlik bilgileri ve iki ses fixture'ı Git dışındaki `outputs/public-speaker-evaluation/` dizinindedir.
