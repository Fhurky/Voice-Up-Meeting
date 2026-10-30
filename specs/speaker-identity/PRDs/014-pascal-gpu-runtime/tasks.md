# Görevler — Pascal NVIDIA GPU üzerinde yerel çalışma

- [x] T01 `x86_64-cu126` çıkarım profili, Whisper `int8` seçimi ve profil testleri.
- [x] T02 CUDA 12.6 hash kilidi, sürüm anahtarlı wheelhouse hazırlayıcı ve kabul kaydı.
- [x] T03 Dockerfile/Compose seçimi, GPU algılayan yerel yapılandırma ve toplantı wheelhouse doğrulaması.
- [x] T04 Windows/Pascal kurulum rehberi.
- [x] T05 WSL2/Docker kurulumu, ağsız imaj derlemeleri ve GTX 1080 Ti CUDA hazırlığı.
- [x] T06 Yerel uygulama, ilk yönetici, gerçek analiz akışı ve koşum raporu.

29 Ekim 2026 kanıtı (GTX 1080 Ti, compute capability 6.1, Windows 11 / Docker Desktop
WSL2): 62 paketli cu126 wheelhouse hash doğrulamasıyla indirildi; base ve toplantı
imajları ağsız derlendi. Konteynerde `torch 2.8.0+cu126`, CUDA 12.6 ve GPU görüldü;
`/meeting-ready` üç sabit modeli `cuda:0` ile 200 döndürdü. Yerel admin girişi, 37
saniyelik sentetik tek sesli İngilizce WAV yükleme, analiz ve metin akışı nginx
üzerinden gerçek HTTP ile `succeeded` oldu; metin kaynak cümlelerle eşleşti ve
20 saniyeyi aşan temiz konuşma yeni profil oluşturdu. Bu bir teknik duman testidir;
Türkçe veya çok konuşmacılı doğruluk kanıtı değildir.

Tam profil kapısı 15/15 adımda geçti: 877 backend (canlı PostgreSQL) ve 207 frontend
testi. Inference paketi 236/236. Kök paket 1345 başarılı, 17 atlanan, 97 başarısız;
başarısızların tamamı bu bilgisayarda PowerShell betik ilkesinin `.ps1` çalıştırmayı
engellemesinden kaynaklanır. Kalıcı `e2e/auth` senaryoları Node 22.23.2 ve headless
Chromium ile 2/2 geçti. 008 tasarımından kalan eski ana sayfa başlığı nedeniyle
`01-super-admin-login.mjs` önce başarısız oldu; başlık artık `home.title` kataloğundan
okunur. Sıradan okuyucu hesabı gerektiren speaker-identity senaryoları ve güvenlik
kapısı (onaylı tarayıcı paketi yok) bu bilgisayarda çalıştırılmadı.
