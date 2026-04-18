# 📐 Veritabanı Şeması — ERD ve Tablo Açıklamaları

## 👥 Ekip Üyeleri
**Altay Yeles · Alper Güner · Mustafa Ulaş Karaaslan · Mehmet Can Öztürk · Emre Aslan**

---

## İlişki Diyagramı

```
┌──────────────┐        ┌────────────────────────────────────────┐
│     Ekip     │  1  N  │             Emlaklar                   │
│──────────────│────────│────────────────────────────────────────│
│ DanismanID   │◄───────│ IlanID        (PK)                     │
│ AdSoyad      │        │ DanismanID    (FK → Ekip)              │
│ Unvan        │        │ Baslik, Fiyat                          │
│ Telefon      │        │ Il, Ilce, Mahalle                      │
└──────────────┘        │ EmlakTipi                              │
                        │ BrutM2, NetM2, OdaSayisi               │
                        └────────────────┬───────────────────────┘
                                         │ N
                                         ▼
                        ┌────────────────────────────────────────┐
                        │        Emlak_Ozellikleri               │
                        │      (Köprü / Junction Tablosu)        │
                        │────────────────────────────────────────│
                        │ IlanID     (FK → Emlaklar)             │
                        │ OzellikID  (FK → Ozellikler)           │
                        │ [Bileşik PK: IlanID + OzellikID]       │
                        └────────────────┬───────────────────────┘
                                         │ N
                                         ▼
                        ┌────────────────────────────────────────┐
                        │          Ozellikler                    │
                        │────────────────────────────────────────│
                        │ OzellikID  (PK)                        │
                        │ KategoriID (FK → Ozellik_Kategorileri) │
                        │ OzellikAdi                             │
                        └────────────────┬───────────────────────┘
                                         │ N
                                         │ 1
                        ┌────────────────▼───────────────────────┐
                        │       Ozellik_Kategorileri             │
                        │────────────────────────────────────────│
                        │ KategoriID  (PK)                       │
                        │ KategoriAdi                            │
                        │   → 'İç Özellik'                       │
                        │   → 'Dış Özellik'                      │
                        │   → 'Cephe'                            │
                        └────────────────────────────────────────┘
```

---

## Tablo Detayları

### 1. `Ekip`
Emlak ofisindeki danışman ve mağaza sahiplerinin bilgilerini tutar.

| Sütun | Tip | Kısıt | Açıklama |
|---|---|---|---|
| `DanismanID` | INTEGER | PK, AUTOINCREMENT | Danışmanın benzersiz kimliği |
| `AdSoyad` | VARCHAR(100) | NOT NULL | Personelin tam adı |
| `Unvan` | VARCHAR(50) | — | Danışman / Mağaza Sahibi vb. |
| `Telefon` | VARCHAR(30) | — | İletişim numarası |

---

### 2. `Emlaklar`
Portföydeki kiralık ve satılık gayrimenkul ilanlarının temel verilerini saklar.

| Sütun | Tip | Kısıt | Açıklama |
|---|---|---|---|
| `IlanID` | INTEGER | PRIMARY KEY | İlanın benzersiz numarası (1000–1004) |
| `DanismanID` | INT | FK → Ekip | İlgili danışmanın referansı |
| `Baslik` | VARCHAR(255) | NOT NULL | İlan başlığı |
| `Fiyat` | DECIMAL(18,2) | NOT NULL | Aylık kira / satış fiyatı (TL) |
| `İl` | VARCHAR(50) | — | Şehir |
| `İlce` | VARCHAR(50) | — | İlçe (Beyoğlu, Şişli vb.) |
| `Mahalle` | VARCHAR(100) | — | Mahalle adı |
| `EmlakTipi` | VARCHAR(50) | — | Kiralık Daire, Kiralık Ofis vb. |
| `BrutM2` | INT | — | Brüt metrekare |
| `NetM2` | INT | — | Net metrekare |
| `OdaSayisi` | VARCHAR(20) | — | 1+1, 2+1 gibi oda düzeni |

---

### 3. `Ozellik_Kategorileri`
Özelliklerin gruplanmasını sağlayan ana başlıklardır.

| Sütun | Tip | Kısıt | Açıklama |
|---|---|---|---|
| `KategoriID` | INTEGER | PK, AUTOINCREMENT | Kategori kimliği |
| `KategoriAdi` | VARCHAR(50) | NOT NULL | İç Özellik / Dış Özellik / Cephe |

**Mevcut Kategoriler:**

| ID | Kategori Adı | Örnek Özellikler |
|---|---|---|
| 1 | İç Özellik | ADSL, Klima, Çelik Kapı, Teras, Isıcam... |
| 2 | Dış Özellik | Asansör, Güvenlik, Otopark, Isı Yalıtımı... |
| 3 | Cephe | Doğu, Batı, Güney, Kuzey |

---

### 4. `Ozellikler`
Kategorilere bağlı tüm özellik havuzunu içerir.

| Sütun | Tip | Kısıt | Açıklama |
|---|---|---|---|
| `OzellikID` | INTEGER | PK, AUTOINCREMENT | Özellik kimliği |
| `KategoriID` | INT | FK → Ozellik_Kategorileri | Ait olduğu kategori |
| `OzellikAdi` | VARCHAR(100) | NOT NULL | Özellik metni |

**Toplam:** 33 özellik — 19 İç Özellik · 10 Dış Özellik · 4 Cephe

---

### 5. `Emlak_Ozellikleri` *(Köprü / Junction Tablosu)*
Emlaklar ile Ozellikler arasındaki **çoka-çok (M:N)** ilişkiyi çözer.

| Sütun | Tip | Kısıt | Açıklama |
|---|---|---|---|
| `IlanID` | INT | FK → Emlaklar | İlanın referansı |
| `OzellikID` | INT | FK → Ozellikler | Özelliğin referansı |
| *(IlanID + OzellikID)* | — | COMPOSITE PK | Bileşik birincil anahtar |

> Bir ilan birden fazla özelliğe sahip olabilir; aynı özellik birden fazla ilana atanabilir.

---

## Veri Özeti

| Tablo | Kayıt Sayısı | Not |
|---|---|---|
| Ekip | 2 | 1 Danışman, 1 Mağaza Sahibi |
| Emlaklar | 5 | IlanID: 1000–1004 |
| Ozellik_Kategorileri | 3 | İç / Dış / Cephe |
| Ozellikler | 33 | Tüm özellik havuzu |
| Emlak_Ozellikleri | 26 | İlan-özellik eşleştirmeleri |

---

> **Veri Kaynağı:** Tüm veriler njoyemlak.com adresinden manuel olarak toplanmıştır (data scraping).