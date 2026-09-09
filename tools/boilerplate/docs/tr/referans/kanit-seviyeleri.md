# Kanıt seviyeleri

| Seviye | Gerekli asgari kanıt | Sağlamadığı iddia |
|---|---|---|
| L0 — Written | Değişiklik diff/dosyada mevcut | Çalıştığı veya gereksinimi karşıladığı |
| L1 — Test observed | İlgili deterministik, unit ve integration testleri çalıştırılmış, geçmiş ve atlama/açık hata açıklanmış | Gerçek sınır acceptance/conformance veya owner kabulü |
| L2 — Real-boundary observed | L1 + domain'e uygun acceptance senaryosu gerçek sınırda geçmiş | Sorumlu owner kabulü veya runtime admission |
| L3 — Owner accepted/admitted | L2 + exact kapsam ve kanıt için kaydedilmiş sorumlu-owner kararı | Gelecek sürüm, model, tool, policy veya ortamların otomatik kabulü |

Kanıt her zaman şu metadata'yı taşımalıdır: komut veya senaryo, ortam/sürüm, exit code, gözlenen test
sayıları, skipped/failure, provenance ve tarih. “Agent completed” ifadesi tek başına L0'dan yukarı
çıkarmaz.

MCP reconciliation receipt yönetişim kararının biçimsel kanıtıdır; execution tier değildir. Client
session transcript'i yardımcı inceleme kaydı olabilir fakat bağımsız gate sonucu yerine geçmez.

L2 sınırı capability'ye göre değişir: generated web capability gerçek HTTP/browser stack'ini,
Project Factory gerçek local veya HTTP MCP session'ını ve bağımsız tree/tool gözlemini, Agent Platform
ise exact gerçek client/model/tool/policy/environment tuple'ını kullanır. Agent Platform L3 admission
imzalı, süreli ve geri alınabilirdir; yalnız PRD kabulü runtime tuple'ı admit etmez.
