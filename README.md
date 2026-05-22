# Clean Code Analyzer

Python kaynak kodlarını statik analiz yöntemleriyle inceleyen, temiz kod ihlallerini tespit eden ve refactoring önerileri sunan bir web tabanlı kalite raporlama aracıdır. Tek dosya, kod yapıştırma veya ZIP proje arşivi üzerinden analiz yapılabilir.

---

## Özellikler

- Python AST (Abstract Syntax Tree) tabanlı derin kod analizi
- McCabe döngüsel karmaşıklığı (Cyclomatic Complexity)
- Halstead yazılım metrikleri (hacim, zorluk, çaba, tahmini hata sayısı)
- Bakım Yapılabilirlik Endeksi (Maintainability Index)
- LCOM (Lack of Cohesion of Methods) uyum skoru
- Tespit edilen ihlal türleri:
  - Long Method
  - God Class
  - Deep Nesting
  - Too Many Arguments
  - Feature Envy
  - Unused Local Variable
  - Unused Import
  - Duplicate Code (proje analizinde dosyalar arası)
- Teknik borç hesaplama (dakika cinsinden tahmini refactoring süresi)
- Kalite kapısı (Quality Gate): PASSED / FAILED
- Kalite notu: A, B, C, D, F
- İhlale tıklayınca **Google Gemini AI** destekli dinamik refactoring önerisi ve satır bazlı temiz kod örnekleri
- JSON raporu dışa aktarma
- PDF yazdırma desteği
- Üç analiz modu: Kod Yapıştır, Tek .py Dosyası, .zip Proje Arşivi

---

## Gereksinimler

- Python 3.10 veya üzeri
- pip

---

## Kurulum

```bash
# Repoyu klonlayın
git clone https://github.com/EmreYnlk/CleanCodeAnalysis.git
cd CleanCodeAnalysis

# Sanal ortam oluşturun
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# Bağımlılıkları yükleyin
pip install -r requirements.txt

# Çevre değişkenlerini (API Key) yapılandırın
# Proje kök dizininde .env dosyası oluşturun ve Gemini API anahtarınızı ekleyin
echo 'GEMINI_API_KEY="sizin_api_anahtariniz"' > .env
```

---

## Çalıştırma

```bash
uvicorn api:app --reload
```

Sunucu başladıktan sonra tarayıcıda açın:

```
http://localhost:8000
```

---

## Proje Yapısı

```
CleanCodeAnalysis/
├── api.py                    # FastAPI uygulama ve endpoint tanımları
├── requirements.txt          # Python bağımlılıkları
├── analyzer_engine/
│   └── core.py               # AST analizi, metrik hesaplama, ihlal tespiti
├── static/
│   ├── index.html            # Ana sayfa
│   ├── styles.css            # Arayüz stilleri
│   └── app.js                # İstemci tarafı mantık ve rapor görselleştirme
└── test.py                   # Kasıtlı ihlal örnekleri (demo amaçlı)
```

---

## API Referansı

### POST /api/v1/analyze

Yapıştırılan Python kodunu analiz eder.

İstek gövdesi (JSON):
```json
{
  "kaynak_kod": "def ornek():\n    pass"
}
```

### POST /api/v1/analyze/file

Tek bir `.py` dosyasını multipart form olarak alır ve analiz eder.

Form alanı: `file` (`.py` uzantılı dosya, maks. 1 MB)

### POST /api/v1/analyze/project

Bir `.zip` arşivini alır; içindeki tüm `.py` dosyalarını analiz eder ve dosyalar arası kopya kod tespiti yapar.

Form alanı: `file` (`.zip` uzantılı arşiv, maks. 10 MB)

### POST /api/v1/suggest

Bir kural ihlali için Gemini AI modelini kullanarak düzeltilmiş örnek kod ve açıklama üretir.

İstek gövdesi (JSON):
```json
{
  "violation_type": "Long Method",
  "description": "Fonksiyon 30 satırdan uzun.",
  "file": "ornek.py",
  "line": 15,
  "content": "def ornek():\n..."
}
```

Tüm analiz endpoint'leri aynı rapor yapısını döner:
```json
{
  "mesaj": "Analiz başarıyla tamamlandı.",
  "rapor": { ... }
}
```

---

## Teknik Borç Tablosu

| İhlal Türü                  | Tahmini Düzeltme Süresi |
|-----------------------------|------------------------|
| Sözdizimi Hatası            | 120 dk                 |
| God Class                   | 60 dk                  |
| Long Method                 | 15 dk                  |
| McCabe Karmaşıklığı         | 20 dk                  |
| Too Many Arguments          | 15 dk                  |
| Deep Nesting                | 20 dk                  |
| Feature Envy                | 20 dk                  |
| Gereksiz Değişken           | 5 dk                   |
| Gereksiz Import             | 5 dk                   |
| Kopya Kod                   | 30 dk                  |

---

## Güvenlik ve Limitler

- Yüklenen dosyalar sunucuda kalıcı olarak saklanmaz (Zero Retention).
- Tek dosya analizi: maks. 1 MB
- ZIP arşivi: maks. 10 MB
- ZIP içi tek dosya: maks. 750 KB
- ZIP içi toplam Python boyutu: maks. 5 MB
- ZIP içi maksimum Python dosya sayısı: 200
- `venv`, `__pycache__`, `.git`, `node_modules` ve benzeri dizinler arşiv içinde otomatik olarak atlanır.

---

## Geliştirme Notları

- Analiz motoru `analyzer_engine/core.py` içinde, API katmanı `api.py` içindedir.
- Frontend tamamen Vanilla JS ile yazılmıştır; harici framework kullanılmamaktadır.
- Çoklu encoding desteği vardır: UTF-8, CP1254, Latin-1.

---

## Lisans

Bu proje eğitim amaçlıdır.
