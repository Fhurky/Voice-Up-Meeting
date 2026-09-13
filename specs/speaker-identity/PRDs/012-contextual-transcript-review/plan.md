# Plan — Bağlama göre konuşma sözcüklerini gözden geçirme

Kaynak: [Accepted PRD](PRD.md); `kt-vibecoding-python-web-v2`.

1. Requirement 1: Yeni `domain/transcript_correction.py`, servis/port, Ollama
   adaptörü, repo bağlam okuması ve router/şema. Önce gerçek hedef davranışı
   kırmızı testle oluştur; işlem/kilit HTTP çağrısı boyunca tutulmasın.
2. Requirement 1, 4: Tipli dört ayar, env örnekleri, consuming Compose ve
   kapalı nginx host köprüsü; kurum içi isteğe bağlı NetworkPolicy, test ve
   yerel kurulum yardımcısı. Var olan model dışında indirme/kurulum yapma.
3. Requirement 2: Ortak istemciden tipli hizmet, seçili satır paneli,
   orijinal/öneri ve küçük değişim listesi, iki dil, iptal/kimlik/HTML sınırları.
   API hazır olunca mevcut wrapper'larla OpenAPI/tip üret.
4. Requirement 3: Kalıcı, tekrar çalıştırılabilir deney yürütücüsü ve sabit
   Türkçe fikstür; aynı domain/adapter politikasını gerçek modelle kullan.
   İlk cevap süresini ölç; kontrollü ve gerçek ASR sonuçlarını ayır. Deney
   günlüğünün mevcut yazıcısını kullan, eski blokları yeniden yazma.
5. Requirement 2, 4: Gerçek ordinary HTTP ve tarayıcı; e2e kayıt/rehber.
   Dar testler sonrası tam kalite kapısı, güvenlik kapısı ve kanıt raporu.

Raporlar `docs/evidence/2026-09-13-contextual-transcript-review/`; özel metin,
model cevapları ve ham deney dosyaları yalnız Git dışı `outputs/` altındadır.
L2 preview işlevi ve model düzeltme kalitesi ayrı gözlenir; başarı yoksa gizleme.

Uygulanan ayrıntılar: yerel kamu proxy'sinde yalnız önizleme yolu 110 saniye
bekler; Kubernetes'te `textReview.enabled` açıkken mevcut backend Ingress'i
110 saniye bekler ve Prefix eşleştirmesi korunur. StrictMode iptal edilen
kurulumun model gönderimini durdurur. Yanıt sonrası `keep_alive:0` kullanılır.
Son [teslim raporu](../../../../docs/evidence/2026-09-13-contextual-transcript-review/README.md)
967 otomatik test, gerçek HTTP/tarayıcı ve model sonuçlarını bağlar;
güvenlik aracı ve gözlenmeyen ortamlar görev listesinde açık tutulur.
