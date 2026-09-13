# Plan — Genişletilmiş Türkçe test kapsamı

Kaynak: [Accepted PRD](PRD.md); profil `kt-vibecoding-python-web-v2`.

1. Requirement 1: Mevcut `scripts/evaluate-turkish-asr.py` sınırlarını kullanarak
   ayrı kaynak manifestleri ve güvenli hazırlama ekle. FLEURS resmî kaynak
   incelemesi ve MediaSpeech eski klip dışlama kanıtını kaydet.
2. Requirement 1, 3, 4: Yeniden kullanılabilir ASR çıkarım/kanıt sınırını
   genişlet; kaynak bağlı devamı ve klip toplamasını `tests/` içinde kırmızı/
   yeşil doğrula. Geçmiş 009 komut ve günlük sözleşmelerini koru.
3. Requirement 2: Türkçe toplantı hazırlama/yürütme araçlarına açık sürümlü
   iki yeni pencere protokolü ekle; zamanları kaydır, kesişen referansları açık
   say, yanlış protokol ve ses değiştirme regresyonlarını çalıştır.
4. Requirement 1–3: CPU indirme/hazırlama ile bağımsız geliştirmeyi paralel,
   gerçek GPU koşumlarını sırayla çalıştır. Yeni sıradan tenant ile gerçek
   toplantı HTTP sınırını kullan. Her deneyin toplu sonucu günlüğe yazılsın.
5. Requirement 3–4: Kaynak bazlı skor, süre, örnek sayısı ve hata dağılımını
   yayınla. `scripts/quality-gate.sh all`, dar Python testleri ve güvenlik
   kapısını çalıştır; sabit rapor, rehber, roadmap ve görevleri tamamla.

API/şema/UI/dağıtım değişiklikleri PRD'deki N/A gerekçeleriyle uygulanmaz.
Özel çıktılar `outputs/2026-09-13-expanded-turkish/`; toplu kanıtlar
`docs/evidence/2026-09-13-expanded-turkish/` altında tutulur.
