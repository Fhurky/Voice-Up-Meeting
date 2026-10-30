# Görevler — Kurumsal görsel tema

- [x] T01 Kontrast ve palet testi (kırmızı → yeşil).
- [x] T02 `:root` paleti ve dekoratif gradyan/vurgu öğeleri.
- [x] T03 Zenginleştirilmiş TR/EN metinler.
- [x] T04 Ön yüz kapısı, tarayıcı ekran görüntüleri ve mevcut senaryolar.
- [x] T05 008 notu, yol haritası ve koşum raporu.

30 Ekim 2026 kanıtı: `src/theme.test.ts` önce 26 testte kırmızı, palet sonrası 27/27;
Decision 1–4 rolleri, 24 metin çiftinde en az 4,5:1, turuncuda 3:1 ve `:root` dışında
renk değeri olmaması doğrulanır. Ön yüz kapısı 254/254. Giriş, ana sayfa, toplantılar,
toplantı sonucu, konuşmacılar ve ses tanıma TR 1440 ve EN 390 px'te gerçek tarayıcıda
yatay taşma ve sayfa hatası olmadan görüntülendi; `13-microphone-profile-enrollment.mjs`
yeniden geçti. Kullanıcının görsel kabulü (L3) bekleniyor.
