> Güncel toplam: 21 ön yüz testi ve 3 canlı CUA akışı başarılı. Bu dosya kronolojik koşumları korur; gerçek CUDA ile tamamlanan son akış en son bölümdedir. Kalıcı Playwright paketi ve gerçek kişi veri deneyi açık kalır.

# Koşum raporu — 2026-09-09 · yerel konuşmacı pilotu ön yüzü

1. Sonuç: Güncel ön yüz otomasyonu başarılı; canlı salt okunur ve negatif yükleme akışları gözlendi — birim 21 başarılı / tarayıcı 2 başarılı / atlanan 1; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`, Node 22.23.2 Compose `frontend`, gerçek ters vekil `http://127.0.0.1:8081`; son otomatik koşum 00:22 Türkiye saati.

   | Koşum | Dosya veya komut | Gözlenen sonuç |
   | --- | --- | --- |
   | Birim | `src/lib/apiClient.test.ts` | 4 başarılı |
   | Birim | `src/lib/authStorage.test.ts` | 1 başarılı |
   | Birim | `src/locales/catalogues.test.ts` | 1 başarılı |
   | Birim | `src/pages/HomePage.test.tsx` | 1 başarılı |
   | Birim | `src/pages/LoginPage.test.tsx` | 1 başarılı |
   | Bileşen | `src/components/AudioJobForm.test.tsx` | 4 başarılı |
   | Bileşen | `src/components/SpeakerResultCard.test.tsx` | 4 başarılı |
   | Bileşen | `src/pages/SpeakerProfilesPage.test.tsx` | 3 başarılı |
   | Bileşen | `src/pages/SpeakerJobPage.test.tsx` | 2 başarılı |
   | Statik | `npm run lint` | Çıkış 0; hata 0, uyarı 0 |
   | Tip ve üretim derlemesi | `npm run build` | Çıkış 0; TypeScript ve Vite başarılı |
   | Gerçek sözleşmeden üretim | `scripts/generate-types.sh` ve `scripts/generate-types.sh --check` | Çıkış 0; backend OpenAPI kullanıldı |
   | Canlı tarayıcı | CUA: sıradan `voiceup-reader` ile gerçek giriş → İngilizce/Türkçe boş profiller → Türkçe salt okunur analiz | Yazma/yükleme denetimleri yok; doğru açıklamalar görünür |
   | Canlı tarayıcı | CUA: `voiceup-admin` ile gerçek giriş → bozuk WAV → sessiz WAV → kaydedilmiş iş → sayfa yenileme → İngilizce iş durumu | Bozuk kayıt reddedildi; geçerli yükleme aynı iş URL'sinde sırada kaldı; yenileme iş üretmedi |
   | Kalıcı tarayıcı senaryosu | `scripts/e2e.sh speaker-identity` | Ortam engeli: kabul edilmiş, platformla eşleşen çevrimdışı paket yok |
   | Senaryo sözdizimi | Node 22 `node --input-type=module --check`, `e2e/auth/01-super-admin-login.mjs`, `e2e/speaker-identity/01-local-pilot.mjs` ve `02-read-only.mjs` | Üç dosyada çıkış 0; tarayıcı koşumu sayılmaz |

3. Maddeler:

   **KUSUR**

   M1 Paylaşılan istemci multipart yüklemeye JSON başlığı ekliyor, her 401'de oturumu siliyor ve 204 yanıtı JSON çözüyordu; düzeltildi, `src/lib/apiClient.test.ts` ile korunuyor.

   M2 Canlı dil değişiminde giriş hatası eski dilde kalıyordu; `src/pages/LoginPage.test.tsx` önce 1 başarısız, düzeltmeden sonra 1 başarılı. Hata artık mesaj anahtarıyla tutuluyor.

   M3 Gerçek OpenAPI nullable benzerlik alanlarını isteğe bağlı üretti; ilk derlemede 2 tip hatası görüldü, eksik/null değer gösterimi düzeltildi. İki test seçici seçeneği de geçerli Testing Library imzasıyla düzeltildi.

   M4 Geçici gereksiz test içe aktarımı lint'te yakalandı; kaldırıldı. Son lint çıktısı temiz.

   **TUZAK**

   M5 Dört form testi ilk koşumda happy-dom'un dosya alanı yerel doğrulaması nedeniyle submit tetiklemedi; dosya seçimini takiben React form sınırına submit olayı gönderildi. Gerçek dosya seçimi ve tıklama ayrıca CUA'da doğrulandı.

   M6 İlk yönetici girişleri 401 döndü; Windows parola bootstrap akışındaki CRLF sorunu backend çalışmasında giderilip aynı hesapla gerçek giriş başarılı oldu.

   M7 Kalıcı senaryo `APP_E2E_ENROLL_AUDIO` ile en az 10 saniyelik kullanılabilir konuşma, `APP_E2E_OTHER_AUDIO` ile başka bir kişinin kaydını bekler. Tekrarlı dosyalar bağlantı kanıtıdır, ayrı oturum doğruluk ölçümü değildir.

   **GÖZLEM**

   M8 Ağ yanıtı kaybında aynı upload/job anahtarıyla tekrar, hedef profil kimliği, dosya sınırı, salt okunur yetki, ad değiştirme, açık silme onayı, durum yenileme, bilinmeyen/belirsiz/silinmiş kimliğin gizlenmesi otomatik test edildi.

   M9 CUA tarayıcı konsolunda son kontrol hata 0/uyarı 0; gerçek ters vekil ve uygulama giriş formu kullanıldı, oturum bilgisi enjekte edilmedi.

   M10 Konuşmacı ekranı 390×844 görünümde görsel olarak incelendi; form tek sütuna geçti, dosya/gönderim denetimleri ve liste taşmadan görünüyordu. Geçici görünüm boyutu geri alındı.

   **AÇIK**

   M11 GPU çalışma ortamı bu koşum sırasında henüz hazır değildi; başarılı profil oluşturma/tanıma, sessiz sesin terminal kalite hatası ve gerçek cihaz çıkarımı burada tamamlandı sayılmaz.

   M12 Çevrimdışı tarayıcı paketinin yokluğu nedeniyle kalıcı Playwright senaryosu çalıştırılamadı. CUA canlı kanıtı bu senaryonun koşulduğu anlamına gelmez.

   M13 Kullanıcının beş kişi ve ayrı oturum sorgularından oluşan veri seti yok; gerçek Türkçe tanıma doğruluğu ölçülmedi.

   **YAN-ETKİ**

   M14 TR/EN katalogları, profil/analiz/iş sayfaları, lazy route ve locale yükleme, tema tokenları, typed servis ve generated API tipleri eklendi; ön yüz bağımlılıkları değiştirilmedi.

   M15 Kalıcı senaryo `e2e/speaker-identity/` altında yazıldı, manifest ve npm komutu kaydedildi; mevcut auth senaryosu güncel yerelleştirilmiş ekranlara uyarlandı.

   M16 Yalnız yerel test için `outputs/live-browser/invalid.wav`, `silence.wav` ve `d5c370be-6b7e-4ebe-9577-c3c709a62042` işi oluşturuldu. Bunlar gerçek kişi doğruluk verisi değildir.

   M17 Pozitif bağlantı denemesi için resmi SpeechBrain `spk1_snt1.wav` tek kaynak PCM'i tekrar edilip tam 30 saniyeye kesildi; `outputs/live-browser/repeated-public-sample-30s.wav` ve kaynak/çıktı hashleri `fixture.json` içinde. Bu oluşturulmuş ses, ayrı oturum veya doğal 30 saniyelik konuşma kanıtı değildir.

   M18 Yanlış hedef/bilinmeyen bağlantı denemesi için aynı yöntemle yalnız resmi `spk2_snt1.wav` kullanıldı; `repeated-other-public-sample-30s.wav` ve `other-fixture.json` aynı çıktı klasöründe. Kaynak Git blob kimliği ve SHA-256 doğrulandı; farklı kişiler karıştırılmadı.

# Koşum raporu — 2026-09-09 · kalıcı senaryo kapsamı ve hedef adresi

1. Sonuç: Dört senaryo/harness dosyasının Node 22 sözdizimi kontrolü başarılı — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 1; karar bekleyen: yok.
2. Koşulan: Compose `frontend` Node 22 `node --input-type=module --check`; `e2e/auth/01-super-admin-login.mjs`, `e2e/speaker-identity/01-local-pilot.mjs`, `02-read-only.mjs`, `e2e/shared/harness.mjs` çıkış 0. Bu kontrol tarayıcı çalıştırmaz.
3. Maddeler:

   **KUSUR**

   M1 Ortak harness hâlâ başka yerel uygulamanın kullandığı 8080 adresini varsayıyordu; `127.0.0.1:8081` ve ilgili README, Accepted PRD Decision 5 ile eşitlendi.

   **TUZAK**

   M2 `APP_E2E_BASE` açıkça verilirse bu değer kullanılır; gerçek SPA/API ters vekili olmalıdır.

   **GÖZLEM**

   M3 Sıradan rol senaryosu, doğru/yanlış hedefe örnek ekleme ve bilinmeyen ses denetimleri kalıcı senaryoya eklendi; kullanıcı sesleri gereken kalite deneyiyle karıştırılmadı.

   **AÇIK**

   M4 Kabul edilmiş çevrimdışı tarayıcı paketi bulunmadığından kalıcı senaryo koşumu atlandı; sözdizimi kontrolü bu boşluğu kapatmaz.

   **YAN-ETKİ**

   M5 Senaryo ve harness/README değişiklikleri kaydedildi; canlı uygulama veya kullanıcı kayıtları değiştirilmedi.

# Koşum raporu — 2026-09-09 · CUDA Torch paketinin doğrulanmış indirilmesi

1. Sonuç: Resmi Torch wheel dosyasının tamamı beklenen SHA-256 ile eşleşti — birim 0 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok.
2. Koşulan: Windows Python ile `outputs/torch-range-download.py`; resmi `download.pytorch.org` üzerinden 12 paralel HTTP Range bağlantısı. 12 yanıtın 206 durumu, Content-Range ve Content-Length değerleri doğrulandı; toplam 889.052.836 bayt, 229,28 saniye, yeniden deneme 0. Kanıt `outputs/torch-download/verification.json` içindedir.
3. Maddeler:

   **KUSUR** — yok

   **TUZAK**

   M1 İndirme yalnız derleme önbelleği içindir; ürün çalışma anında ağdan model veya paket indirmez. Paket indirilmesi GPU çıkarımının çalıştığını kanıtlamaz.

   **GÖZLEM**

   M2 Tam dosya SHA-256 değeri `3a852369a38dec343d45ecd0bc3660f79b88a23e0c878d18707f7c13bf49538f`; beklenen değerle eşleşmeden wheelhouse dosyası yayımlanmadı.

   **AÇIK**

   M3 GPU image kurulumu ve gerçek çıkarım doğrulaması bu indirme adımının dışında devam ediyor.

   **YAN-ETKİ**

   M4 Doğrulanan dosya `models/inference-wheelhouse/torch-2.8.0+cu128-cp313-cp313-manylinux_2_28_x86_64.whl` içine alındı; 12 parça, yardımcı ve kanıt çıktıları yok sayılan `outputs/` altında korundu. Kurulum veya bağımlılık pin değişikliği yapılmadı.

# Koşum raporu — 2026-09-09 · gerçek CUDA ile canlı pilot akışı

1. Sonuç: Tam teknik akış gerçek tarayıcı, API ve CUDA üzerinde gözlendi; L2 canlı bağlantı kanıtı elde edildi — birim 0 başarılı / tarayıcı 1 başarılı / atlanan 1; karar bekleyen: yok.
2. Koşulan: `kt-vibecoding-python-web-v2`, Compose React/Vite → ters vekil `http://127.0.0.1:8081` → FastAPI/PostgreSQL → worker → `cuda:0`. Gerçek giriş formu ve CUA dosya seçicisi kullanıldı. Bu koşumda kod değişmediği için önceki 21 başarılı birim testi yeniden koşulmadı. Önceki iki canlı akışla toplam üç CUA akışı gözlendi.

   | Canlı denetim | Gözlenen sonuç |
   | --- | --- |
   | İlk profil oluşturma | `e809701e-87b4-4f7b-a81f-ce29d3b951e6`: enrolled; 26,886 saniye kullanılabilir konuşma, 5 pencere, cuda:0 |
   | Aynı profile doğru örnek ekleme | `eda78cd4-e013-48e2-a57b-986670d8e0a4`: enrolled; örnek sayısı 1 → 2 |
   | Farklı ses örneğini hedefe ekleme | `fb688461-9277-43e1-af05-ee5c6b2190ad`: beklenen target_mismatch; örnek sayısı 2 olarak kaldı |
   | Ad değiştirme ve aynı sesi tanıma | `ae8b9d50-1cb7-4edb-8c9b-5db6d2de7213`: recognized; güncel ad, ham kosinüs 1; TR/EN sonuç metinleri gözlendi |
   | Diğer sesin bilinmeyen sonucu | `91020636-9fd5-42cc-891c-63e476151ea1`: unknown; kosinüs 0,08692628145217896, kimlik gösterilmedi ve yeni profil oluşmadı |
   | Kontrollü belirsizlik | Aynı teknik sesle geçici ikinci profil oluşturuldu; `0d9227b5-af34-41d5-9146-b2db024362e6`: ambiguous, iki puan 1, insufficient_margin, kimlik gösterilmedi |
   | Sessiz kayıt | `2aae85fd-d3b7-4d5b-a563-36a95f21f71a`: beklenen insufficient_speech ve yerelleştirilmiş hata |
   | Silme ve geçmiş sonuç | İki teknik profil açık UI onayıyla silindi; liste sıfıra döndü; eski recognized URL'si silinmiş profil durumunu gösterdi, adı gizledi |
   | Performans koşumu için bırakılan tek profil | `9bca476c-660c-4e55-ad85-c46c4319e59c`: enrolled; `Teknik deneme (tekrarlı örnek)`, 1 örnek, aktif profil sayısı 1 |
   | Konsol ve görünüm | Son kontrolde hata 0 / uyarı 0; tek profil ekranı görsel incelendi; ekran görüntüleri CUA araç çıktısındadır, ayrı PNG üretilmedi |

3. Maddeler:

   **KUSUR** — yok

   **TUZAK**

   M1 Bu koşum iki resmi kısa ses örneğinin ayrı ayrı 30 saniyeye tekrarlanmış kopyalarını kullanır. Aynı dosyanın yeniden tanınması ve aynı sesle iki profil oluşturulması teknik denetimdir; ayrı oturum doğruluğu veya iki farklı kişiyi ayırt etme kanıtı değildir.

   M2 Eşikler değiştirilmedi: eşleşme 0,75, yeni kişi 0,45, fark 0,10. Ham kosinüs değerleri yüzde güven olarak sunulmadı; bilinmeyen ve belirsiz sonuçlar kimlik atamadı.

   **GÖZLEM**

   M3 Dokuz GPU işi terminal durumda: 7 succeeded, 2 beklenen failed. Önceki rapordaki GPU hazır olmadığı için açık kalan teknik UI akışları bu koşumla gözlendi; GPU öncesi işin inference_unavailable sonucu başarı olarak sayılmadı.

   M4 Sonuç ve politika alanlarının salt okunur gerçek API kaydı `outputs/live-browser/browser-evidence.json` içindedir; token, parola veya embedding kaydedilmedi. Kaynak/çıktı hashleri `fixture.json` ve `other-fixture.json` içinde korunuyor.

   **AÇIK**

   M5 Kabul edilmiş platforma uygun çevrimdışı tarayıcı paketi bulunmadığı için kalıcı `scripts/e2e.sh speaker-identity` koşumu hâlâ atlandı. CUA gözlemi, bu harness'in çalıştırıldığı anlamına gelmez.

   M6 Beş gerçek kişi ve ayrı oturum kayıtlarından oluşan kullanıcı veri seti henüz yok. Türkçe ses doğruluğu, onlarca kişi genellemesi ve L3 kullanıcı kabulü bu teknik koşumla ölçülmedi.

   **YAN-ETKİ**

   M7 İki geçici teknik profil UI üzerinden silindi. Sonraki performans deneyi için yalnız `92346bd9-86ef-4953-9c83-f0ea491454b0` kimlikli açıkça etiketlenmiş teknik profil bırakıldı; yeni GPU işi gönderilmedi.

   M8 Yerel teknik iş geçmişi ve kayıtları normal saklama kurallarıyla kalır. Kanıt JSON dosyaları yalnız yok sayılan `outputs/live-browser/` altında yazıldı; ürün kodu, eşik veya bağımlılık bu doğrulama için değiştirilmedi.
