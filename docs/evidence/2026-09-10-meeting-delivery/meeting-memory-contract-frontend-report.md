# Koşum raporu — 2026-09-11 · Toplantı hafıza işleme sürümünün üretilmiş sözleşme ve ön yüze taşınması.

1. Sonuç: Yeni işleme sürümü üretilmiş sözleşmede yer aldı ve ön yüz kontrolleri geçti — birim 89 başarılı / tarayıcı 0 başarılı / atlanan 0; karar bekleyen: yok. Bu değişiklik için L1.
2. Koşulan: `kt-vibecoding-python-web-v2`; çalışan yerel backend/frontend konteynerleri, Python 3.13, Node 22, React 19 ve Vite 8.

   | Komut | Sonuç |
   | --- | --- |
   | `scripts/export-openapi.sh` | Backend otoritesinden OpenAPI yeniden üretildi. |
   | `scripts/generate-types.sh` | Frontend API türleri sözleşmeden yeniden üretildi. |
   | `npm run lint` | Başarılı. |
   | `npm run build` | Tip kontrolü ve üretim derlemesi başarılı. |
   | `npm test -- --reporter=default --reporter=json --outputFile=/tmp/meeting-frontend-current.json` | 20 dosyada 89 test başarılı; 8,22 saniye. |
   | `scripts/export-openapi.sh --check`; `scripts/generate-types.sh --check` | İki üretilmiş sözleşmede drift yok. |

3. Maddeler:

   **KUSUR** — yok
   **TUZAK**
   M1 Üretilmiş dosyalar elle düzenlenmedi; `SpeakerResult.preprocessing_version` alanında `meeting-natural-context-v1` backend literal'inden üretildi. Özel model vektörleri ve kalite uçları genel API'ye açılmadı.
   **GÖZLEM**
   M2 Ön yüz kaynak davranışında değişiklik gerekmedi; mevcut üç işleme sürümünü taşıyan sözleşme derlendi, 89 regresyon geçti. Koşum çıktısı Git dışı `outputs/2026-09-10-meeting-delivery/meeting-memory-contract-frontend.txt` altında.
   **AÇIK**
   M3 Bu koşum yeni hafıza modeliyle gerçek kullanıcı/tarayıcı kabulünü, A/B/D/C kimlik doğruluğunu veya tam profil kapısını çalıştırmaz; bunlar ana teslimin bağımsız kanıtıdır.
   **YAN-ETKİ**
   M4 Yalnız üretilmiş OpenAPI ve API türleri yenilendi; model, kullanıcı sesi veya profil verisi değişmedi. Derleme/test çıktıları oluşturuldu, commit yapılmadı.
