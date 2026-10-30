# PRD — Okunabilir metin satırları

Status: Accepted

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [026 — readable-transcript-lines](../../roadmap.md)
Profil: `kt-vibecoding-python-web-v2`; şema profili `sqlalchemy-alembic`.
Kaynak ve kabul (30 Ekim 2026): Kullanıcı aynı kişinin art arda gelen tek kelimelik satırlarının birleştirilmesini istedi ve
çözüm sordu. Kabul edilirse 002 satır gruplamasındaki işaret kuralı Decision 1 ile değişir.

## Amaç ve önceki durum

`align_words` kelimeleri konuşmacı, üst üste konuşma ve belirsizlik işareti aynıysa aynı satıra alır. İşaretler kelime başına
değiştiği için cümleler bölünür. 84 dakikalık gerçek toplantıda aynı kişinin 1082 satır geçişinin 959'unda tek fark işarettir ve
1449 satırın 779'u bir veya iki kelimeliktir. Hedef: aynı kişinin konuşması tek satırda okunsun, işaretler görünür kalsın.

## Kararlar

Decision 1: Satır sınırını yalnız konuşmacı değişimi, 1,5 saniyeden uzun boşluk, araya giren başka konuşmacı ve 500 karakter sınırı
belirler. İşaret farkı satırı bölmez. Konuşmacısı belirsiz kelimeler kişiye atanmaz; kendi satırında kalır.

Decision 2: Satır, kelimelerinin en az %30'u işaretliyse "üst üste konuşma" veya "belirsiz" sayılır. Kelime düzeyindeki işaret
saklanmaz; tek kelimelik işaretli satır işaretli kalır.

Decision 3: Yalnız yeni işlenen toplantılar etkilenir; eski kayıtlar değişmez. Şema, API, ön yüz ve konuşmacı süreleri değişmez.

## Gereksinimler

Requirement 1: `align_words` Decision 1 ve 2'ye göre değişir; birim testleri bölme ve işaret paylarını kapsar.

Requirement 2: İki gerçek Türkçe kayıt yeniden işlenip satır sayısı ve işaretli satır payı raporlanır.

## Katmanlar

Şema, API, OpenAPI, ön yüz, vektör, gözlemlenebilirlik ve Kubernetes: N/A — yalnız `app/domain/meeting_timeline.py` değişir.

## Kabul ölçütleri

- [ ] Birim testleri ve tam kalite kapısı geçer.
- [ ] Gerçek kayıtta bir veya iki kelimelik satır sayısı belirgin düşer; metin ve konuşmacı süreleri korunur.
- [ ] Kullanıcı sonucu kabul eder (L3).
