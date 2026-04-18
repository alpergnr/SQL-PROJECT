# 📐 Database Schema — ERD and Table Descriptions

## 👥 Team Members
**Altay Yeles · Alper Güner · Mustafa Ulaş Karaaslan · Mehmet Can Öztürk · Emre Aslan**

---

## Entity Relationship Diagram

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
                        │      (Bridge / Junction Table)         │
                        │────────────────────────────────────────│
                        │ IlanID     (FK → Emlaklar)             │
                        │ OzellikID  (FK → Ozellikler)           │
                        │ [Composite PK: IlanID + OzellikID]     │
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

## Table Details

### 1. `Ekip`
Stores information about agents and store owners in the real estate office.

| Column | Type | Constraint | Description |
|---|---|---|---|
| `DanismanID` | INTEGER | PK, AUTOINCREMENT | Unique identifier for the agent |
| `AdSoyad` | VARCHAR(100) | NOT NULL | Full name of the staff member |
| `Unvan` | VARCHAR(50) | — | Agent / Store Owner, etc. |
| `Telefon` | VARCHAR(30) | — | Contact number |

---

### 2. `Emlaklar`
Stores core data of rental and for-sale property listings in the portfolio.

| Column | Type | Constraint | Description |
|---|---|---|---|
| `IlanID` | INTEGER | PRIMARY KEY | Unique listing number (1000–1004) |
| `DanismanID` | INT | FK → Ekip | Reference to the associated agent |
| `Baslik` | VARCHAR(255) | NOT NULL | Listing title |
| `Fiyat` | DECIMAL(18,2) | NOT NULL | Monthly rent / sale price (TL) |
| `İl` | VARCHAR(50) | — | City |
| `İlce` | VARCHAR(50) | — | District (Beyoğlu, Şişli, etc.) |
| `Mahalle` | VARCHAR(100) | — | Neighborhood name |
| `EmlakTipi` | VARCHAR(50) | — | Rental Apartment, Rental Office, etc. |
| `BrutM2` | INT | — | Gross square meters |
| `NetM2` | INT | — | Net square meters |
| `OdaSayisi` | VARCHAR(20) | — | Room layout such as 1+1, 2+1 |

---

### 3. `Ozellik_Kategorileri`
Main headings that provide grouping for features.

| Column | Type | Constraint | Description |
|---|---|---|---|
| `KategoriID` | INTEGER | PK, AUTOINCREMENT | Category identifier |
| `KategoriAdi` | VARCHAR(50) | NOT NULL | Interior Feature / Exterior Feature / Orientation |

**Existing Categories:**

| ID | Category Name | Example Features |
|---|---|---|
| 1 | İç Özellik (Interior Feature) | ADSL, Air Conditioning, Steel Door, Terrace, Double Glazing... |
| 2 | Dış Özellik (Exterior Feature) | Elevator, Security, Parking, Thermal Insulation... |
| 3 | Cephe (Orientation) | East, West, South, North |

---

### 4. `Ozellikler`
Contains the full feature pool linked to categories.

| Column | Type | Constraint | Description |
|---|---|---|---|
| `OzellikID` | INTEGER | PK, AUTOINCREMENT | Feature identifier |
| `KategoriID` | INT | FK → Ozellik_Kategorileri | The category it belongs to |
| `OzellikAdi` | VARCHAR(100) | NOT NULL | Feature text |

**Total:** 33 features — 19 Interior Features · 10 Exterior Features · 4 Orientations

---

### 5. `Emlak_Ozellikleri` *(Bridge / Junction Table)*
Resolves the **many-to-many (M:N)** relationship between Emlaklar and Ozellikler.

| Column | Type | Constraint | Description |
|---|---|---|---|
| `IlanID` | INT | FK → Emlaklar | Reference to the listing |
| `OzellikID` | INT | FK → Ozellikler | Reference to the feature |
| *(IlanID + OzellikID)* | — | COMPOSITE PK | Composite primary key |

> A listing can have multiple features; the same feature can be assigned to multiple listings.

---

## Data Summary

| Table | Record Count | Note |
|---|---|---|
| Ekip | 2 | 1 Agent, 1 Store Owner |
| Emlaklar | 5 | IlanID: 1000–1004 |
| Ozellik_Kategorileri | 3 | Interior / Exterior / Orientation |
| Ozellikler | 33 | Full feature pool |
| Emlak_Ozellikleri | 26 | Listing–feature mappings |

---

> **Data Source:** All data was manually collected (data scraping) from **[njoyemlak.com](https://njoy.sahibinden.com/)**.
