# Görevler — Sade çalışma alanı tasarımı

- [x] T01 Ortak stil kuralları ve yan menü sadeleştirmesi.
- [x] T02 Ana sayfa.
- [x] T03 Toplantılar ve yeni toplantı akışı.
- [x] T04 Toplantı sonucu sekmeleri.
- [x] T05 Konuşmacılar ve yeni profil paneli.
- [x] T06 Giriş ekranı.
- [x] T07 Birim testleri, tarayıcı senaryoları, ön yüz kapısı, ekran görüntüleri ve koşum raporu.

30 Ekim 2026 kanıtı: Decision 8a için `14-workspace-navigation.mjs` önce kırmızıydı (yan
menü iki kez belgeden çıktı), tek kalıcı Suspense sınırı ve sayfa kodunun önceden
yüklenmesiyle iki ardışık koşumda geçti. Ön yüz kapısı 257/257 (sekmelerin klavye
davranışı, ana sayfa eylem kartları ve yeni toplantı akışı için yeni testler dahil).
Tarayıcı senaryoları 02, 07, 08, 12, 13, 14 yerel test hesaplarıyla geçti. 01, 03, 04, 05,
06, 09, 10, 11 yeni akışa göre güncellendi ancak gerçek ses, model veya önceden hazırlanmış
fikstür gerektirdikleri için bu çalışmada koşulmadı. Ana sayfalar TR 1440 ve EN 390 px'te
yatay taşma ve sayfa hatası olmadan görüntülendi. Kullanıcının görsel kabulü (L3) bekleniyor.
