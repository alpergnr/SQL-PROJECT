# 📐 Database Schema — ERD and Table Descriptions

## 👥 Team Members

**Altay Yeles · Alper Güner · Mustafa Ulaş Karaaslan · Mehmet Can Öztürk · Emre Aslan**

\---

## Entity Relationship Diagram

\[!\[Schema ERD](https://github.com/alpergnr/SQL-PROJECT/raw/main/docs/screenshots/schema\_erd.png)](https://github.com/alpergnr/SQL-PROJECT/blob/main/docs/screenshots/schema\_erd.png)

\---

## Table Details

### 1\. `Ekip`

Stores information about agents and store owners in the real estate office.

|Column|Type|Constraint|Description|
|-|-|-|-|
|`DanismanID`|INTEGER|PK, AUTOINCREMENT|Unique identifier for the agent|
|`AdSoyad`|VARCHAR(100)|NOT NULL|Full name of the staff member|
|`Unvan`|VARCHAR(50)|—|Agent / Store Owner, etc.|
|`Telefon`|VARCHAR(20)|—|Contact number|

\---

### 2\. `Emlaklar`

Stores core data of rental and for-sale property listings in the portfolio.

|Column|Type|Constraint|Description|
|-|-|-|-|
|`IlanID`|INTEGER|PRIMARY KEY|Unique listing number (1000–1009)|
|`DanismanID`|INT|FK → Ekip|Reference to the associated agent|
|`Baslik`|VARCHAR(255)|NOT NULL|Listing title|
|`Fiyat`|DECIMAL(18,2)|NOT NULL|Monthly rent / sale price (TL)|
|`İl`|VARCHAR(50)|—|City|
|`İlce`|VARCHAR(50)|—|District (Beyoğlu, Şişli, etc.)|
|`Mahalle`|VARCHAR(100)|—|Neighborhood name|
|`EmlakTipi`|VARCHAR(50)|—|Rental Apartment, Rental Office, etc.|
|`BrutM2`|INT|—|Gross square meters|
|`NetM2`|INT|—|Net square meters|
|`OdaSayisi`|VARCHAR(20)|—|Room layout such as 1+1, 2+1|
|`Aktif`|INTEGER|DEFAULT 1|Soft-delete flag; `0` means the listing is hidden from site/admin lists|

\---

### 3\. `Ozellik\_Kategorileri`

Main headings that provide grouping for features.

|Column|Type|Constraint|Description|
|-|-|-|-|
|`KategoriID`|INTEGER|PK, AUTOINCREMENT|Category identifier|
|`KategoriAdi`|VARCHAR(50)|NOT NULL|Interior Feature / Exterior Feature / Orientation|

**Existing Categories:**

|ID|Category Name|Example Features|
|-|-|-|
|1|İç Özellik (Interior Feature)|ADSL, Air Conditioning, Steel Door, Terrace, Double Glazing...|
|2|Dış Özellik (Exterior Feature)|Security Camera, Thermal Insulation, Satellite, Generator...|
|3|Cephe (Orientation)|East, West, South, North|

\---

### 4\. `Ozellikler`

Contains the full feature pool linked to categories.

|Column|Type|Constraint|Description|
|-|-|-|-|
|`OzellikID`|INTEGER|PK, AUTOINCREMENT|Feature identifier|
|`KategoriID`|INT|FK → Ozellik\_Kategorileri|The category it belongs to|
|`OzellikAdi`|VARCHAR(100)|NOT NULL|Feature text|

**Total:** 81 features — 53 Interior Features · 24 Exterior Features · 4 Orientations

\---

### 5\. `Emlak\_Ozellikleri` *(Bridge / Junction Table)*

Resolves the **many-to-many (M:N)** relationship between Emlaklar and Ozellikler.

|Column|Type|Constraint|Description|
|-|-|-|-|
|`IlanID`|INT|FK → Emlaklar|Reference to the listing|
|`OzellikID`|INT|FK → Ozellikler|Reference to the feature|
|*(IlanID + OzellikID)*|—|COMPOSITE PK|Composite primary key|

> A listing can have multiple features; the same feature can be assigned to multiple listings.

\---

### 6\. `Fiyat\_Degisim\_Log`

Stores price change audit records generated automatically by the update trigger.

|Column|Type|Constraint|Description|
|-|-|-|-|
|`LogID`|INTEGER|PK, AUTOINCREMENT|Unique audit record identifier|
|`IlanID`|INT|FK → Emlaklar|Listing whose price changed|
|`EskiFiyat`|DECIMAL(18,2)|NOT NULL|Previous listing price|
|`YeniFiyat`|DECIMAL(18,2)|NOT NULL|Updated listing price|
|`DegisimYuzdesi`|REAL|NOT NULL|Percentage change|
|`DegisimTarihi`|TEXT|DEFAULT datetime|Local timestamp of the change|
|`Aciklama`|TEXT|—|Trigger or application note|

\---

### 7\. `Ilan\_Degisim\_Log`

Stores admin panel listing changes, including listing creation, field updates, and price updates.

|Column|Type|Constraint|Description|
|-|-|-|-|
|`LogID`|INTEGER|PK, AUTOINCREMENT|Unique history record identifier|
|`IlanID`|INT|FK → Emlaklar|Listing affected by the admin action|
|`IslemTipi`|VARCHAR(30)|NOT NULL|Action type such as EKLEME, GUNCELLEME, FIYAT\_GUNCELLEME|
|`AlanAdi`|VARCHAR(50)|—|Field changed, such as Fiyat or Mahalle|
|`EskiDeger`|TEXT|—|Previous value|
|`YeniDeger`|TEXT|—|New value|
|`DegisimTarihi`|TEXT|DEFAULT datetime|Local timestamp of the change|
|`Kullanici`|VARCHAR(100)|DEFAULT admin|Admin user that made the change|
|`Aciklama`|TEXT|—|Admin note|

\---

### 8\. `Kullanicilar`

Stores registered customer accounts.

|Column|Type|Constraint|Description|
|-|-|-|-|
|`KullaniciID`|INTEGER|PK, AUTOINCREMENT|Customer identifier|
|`AdSoyad`|VARCHAR(100)|NOT NULL|Customer full name|
|`Email`|VARCHAR(120)|UNIQUE, NOT NULL|Login e-mail|
|`SifreHash`|TEXT|NOT NULL|Hashed password|
|`Rol`|VARCHAR(20)|DEFAULT musteri|User role|
|`KayitTarihi`|TEXT|DEFAULT datetime|Registration timestamp|

\---

### 9\. `Kaydedilen\_Ilanlar`

Stores customer saved/favorite listings.

|Column|Type|Constraint|Description|
|-|-|-|-|
|`KullaniciID`|INT|FK → Kullanicilar|Customer|
|`IlanID`|INT|FK → Emlaklar|Saved listing|
|`KayitTarihi`|TEXT|DEFAULT datetime|Save timestamp|
|*(KullaniciID + IlanID)*|—|COMPOSITE PK|Prevents duplicate saves|

\---

### 10\. `Musteri\_Sorulari`

Stores questions sent by customers and answers written by admins.

|Column|Type|Constraint|Description|
|-|-|-|-|
|`SoruID`|INTEGER|PK, AUTOINCREMENT|Question identifier|
|`KullaniciID`|INT|FK → Kullanicilar|Customer who asked|
|`IlanID`|INT|FK → Emlaklar, nullable|Related listing, if any|
|`SoruMetni`|TEXT|NOT NULL|Customer question|
|`CevapMetni`|TEXT|—|Admin answer|
|`Durum`|VARCHAR(20)|DEFAULT Açık|Question status|
|`SoruTarihi`|TEXT|DEFAULT datetime|Question timestamp|
|`CevapTarihi`|TEXT|—|Answer timestamp|
|`Cevaplayan`|VARCHAR(100)|—|Admin e-mail|

\---

### 11\. `Bildirimler`

Stores customer notifications for admin answers and saved-listing changes.

|Column|Type|Constraint|Description|
|-|-|-|-|
|`BildirimID`|INTEGER|PK, AUTOINCREMENT|Notification identifier|
|`KullaniciID`|INT|FK → Kullanicilar|Recipient customer|
|`IlanID`|INT|FK → Emlaklar, nullable|Related listing|
|`Tip`|VARCHAR(30)|NOT NULL|Notification type|
|`Baslik`|VARCHAR(160)|NOT NULL|Notification title|
|`Mesaj`|TEXT|NOT NULL|Notification body|
|`Okundu`|INTEGER|DEFAULT 0|Read flag|
|`OlusturmaTarihi`|TEXT|DEFAULT datetime|Notification timestamp|

\---

## Advanced SQL Objects

### Views

|View|SQL Topic|Purpose|
|-|-|-|
|`v\_ilan\_detay`|VIEW + JOIN|Reusable listing detail view with agent info and m² price|
|`v\_danisman\_portfoy`|VIEW + GROUP BY|Agent portfolio totals and averages|
|`v\_ozellikli\_ilanlar`|VIEW + GROUP\_CONCAT|Listing features grouped by category|
|`v\_bolge\_fiyat\_analizi`|CTE|District-level price analysis|
|`v\_ilan\_fiyat\_siralamasi`|Window Function|Listing price ranking with `RANK()` and `ROW\_NUMBER()`|
|`v\_danisman\_portfoy\_siralamasi`|Window Function|Agent ranking by portfolio value and listing count|
|`v\_ilce\_oda\_pivot`|Pivot|Room-count pivot using `CASE WHEN`|
|`v\_fiyat\_gecmisi`|Audit View|Human-readable price history|
|`v\_ilan\_gecmisi`|Admin History View|Human-readable listing create/update history|

### Indexes

|Index|Columns|Purpose|
|-|-|-|
|`idx\_emlaklar\_fiyat`|`Fiyat`|Price sorting/filtering|
|`idx\_emlaklar\_ilce\_fiyat`|`İlce`, `Fiyat`|Composite district + price search|
|`idx\_emlaklar\_danisman`|`DanismanID`|Agent portfolio joins|
|`idx\_ozellikler\_ad`|`OzellikAdi`|Feature search|
|`idx\_emlak\_ozellikleri\_ozellik`|`OzellikID`, `IlanID`|Feature-to-listing junction lookups|

### Trigger

|Trigger|Timing|Purpose|
|-|-|-|
|`trg\_emlaklar\_fiyat\_audit`|`AFTER UPDATE OF Fiyat`|Inserts a row into `Fiyat\_Degisim\_Log` whenever a listing price changes|

\---

## Data Summary

|Table|Record Count|Note|
|-|-|-|
|Ekip|2|1 Agent, 1 Store Owner|
|Emlaklar|10|IlanID: 1000–1009|
|Ozellik\_Kategorileri|3|Interior / Exterior / Orientation|
|Ozellikler|81|Full feature pool|
|Emlak\_Ozellikleri|246|Listing–feature mappings|
|Fiyat\_Degisim\_Log|0+|Trigger-generated audit rows|
|Ilan\_Degisim\_Log|0+|Admin listing create/update history rows|
|Kullanicilar|0+|Registered customer accounts|
|Kaydedilen\_Ilanlar|0+|Customer saved listings|
|Musteri\_Sorulari|0+|Customer questions and admin answers|
|Bildirimler|0+|Customer notifications|

\---

> \*\*Data Source:\*\* All data was manually collected (data scraping) from \*\*\[njoyemlak.com](https://njoy.sahibinden.com/)\*\*.

