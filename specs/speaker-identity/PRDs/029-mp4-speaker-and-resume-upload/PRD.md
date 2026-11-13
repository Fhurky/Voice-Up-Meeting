# PRD — Konuşmacı ve sürdürülen yüklemelerde MP4

Status: Accepted

Domain: [speaker-identity](../../DOMAIN.md)
Roadmap: [029 — mp4-speaker-and-resume-upload](../../roadmap.md)
Profil: `kt-vibecoding-python-web-v2`; şema profili `sqlalchemy-alembic`.
Kaynak ve kabul (13 Kasım 2026): Kullanıcı MP4 dosyalarının da yüklenebilmesini istedi; görüntünün kullanılmayacağını, yalnız
sesin yeterli olduğunu belirtti. Bu PRD [025](../025-mp4-meeting-upload/PRD.md) Decision 4'teki "profil kaydına eklenmez"
kararının yerine geçer.

## Amaç ve önceki durum

Yeni toplantı formu MP4 ve M4A kabul eder (025). Konuşmacı profili oluşturma, profile örnek ekleme, Sesi tanı formu ve yarım
kalan toplantı yüklemesini sürdürme paneli yalnız WAV ve FLAC kabul eder. Hedef: bu yerlerde de MP4 veya M4A seçilebilmesi.

## Kararlar

Decision 1: 025'teki yöntem kullanılır: dosya tarayıcıda çözülür, 16 kHz tek kanal WAV yapılır ve mevcut uç noktalara gider.
Görüntü sunucuya gönderilmez ve saklanmaz. Sunucu, API, şema, worker ve bağımlılık değişmez.

Decision 2: Konuşmacı formlarında video dosyası 2 GiB'a kadar seçilebilir. Çıkan ses 120 saniyeyi aşarsa yükleme başlamadan
hata gösterilir. Sunucunun 50 MiB ve 120 saniye sınırları çıkan WAV'a uygulanır; 120 saniyelik WAV yaklaşık 3,8 MB'tır.

Decision 3: Sürdürme panelinde MP4 seçilirse ses yeniden çıkarılır. Çıkan WAV kaydedilmiş parçalarla eşleşmezse mevcut
`source_mismatch` hatası gösterilir; bu, tarayıcı veya dosya değiştiğinde olabilir.

Decision 4: Bir dosya bir kez çözülür; ağ hatasından sonra yeniden denemede aynı ses kullanılır.

Decision 5: Ana sayfa ve yardım metinleri MP4'ü de anar.

## Gereksinimler

Requirement 1: `lib/mediaAudio.ts` süre sınırını çağırandan alır; birim testleri.

Requirement 2: `AudioJobForm` MP4 ve M4A kabul eder, çözme sırasında durum gösterir; hata ve yardım metinleri TR/EN; birim testleri.

Requirement 3: `MeetingSourceUpload` MP4 ve M4A kabul eder ve çözme sırasında durum gösterir; birim testleri.

Requirement 4: Kalıcı tarayıcı senaryosu: sıradan hesapla MP4'ten profil oluşturur, aynı kişinin başka bir MP4'ünü Sesi tanı
formuna yükler, sunucuya yalnız WAV gittiğini doğrular ve oluşturduğu profili siler.

## Katmanlar

Şema, API, OpenAPI, worker, vektör, gözlemlenebilirlik ve Kubernetes: N/A — yalnız ön yüz, metinler ve tarayıcı senaryosu değişir.

## Kabul ölçütleri

- [x] Birim testleri ve tam kalite kapısı geçer.
- [x] Gerçek MP4 ile profil oluşturma ve ses tanıma tarayıcıda geçer; sunucuya yalnız WAV gider.
- [ ] Kullanıcı kendi MP4 dosyasıyla dener (L3).
