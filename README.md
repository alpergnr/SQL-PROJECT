# 🏢 Njoy Emlak — Relational Database Project

> 📍 Real data source: **[njoyemlak.com]([http://www.njoyemlak.com/](https://njoy.sahibinden.com/))** — An SQLite database designed based on the portfolio of an active real estate office in Istanbul.

---

## 👥 Team Members

| | | |
|:---|:---|:---|
| Altay Yeles | Alper Güner | Mustafa Ulaş Karaaslan |
| Mehmet Can Öztürk | Emre Aslan | 

---

## 📌 Project Idea

This project was created as a **solution to a real-world problem**. Our team member **Alper Güner**'s uncle's actively operating real estate company **[Njoy Emlak]([http://www.njoyemlak.com/](https://njoy.sahibinden.com/))** is the direct inspiration and data source for this project.

As their portfolios grow, small and medium-sized real estate offices struggle to manage listing, agent, and feature data effectively. Dependency on scattered Excel files and third-party platforms leads to critical issues such as **data redundancy**, **update anomalies**, and **insufficient reporting**.

This project was initiated to design a normalized and queryable relational database based on the **actual portfolio** of the Njoy Emlak office to solve these problems.

> ⚠️ **Data Collection Method:** All listing data in the database was **manually collected (data scraping)** from **njoyemlak.com**. 5 active listings along with all their interior features, exterior features, and orientation details were entered into the system. No artificial or fabricated data was used.

---

## 🎯 Why Is It Important?

| Current Problem | Provided Solution |
|:---|:---|
| Scattered listing management | Single centralized, normalized database |
| Data breaks when agents change | Referential integrity via Foreign Keys |
| No feature-based search capability | Junction table + chained JOINs |
| Portfolio performance cannot be measured | GROUP BY + SUM + COUNT analyses |
| Price per m² cannot be calculated | Instant calculation with arithmetic operators |

---

## 📁 Repository Structure

```
njoy-emlak-db/
├── README.md                          ← This file
├── SCHEMA.md                          ← ERD and table descriptions
├── njoy_veritabani.sql                ← Database creation + data script
├── njoyemlak.db                       ← Compiled SQLite database
└── Teknik_Rapor.pdf                   ← Technical report
```

---

## 🗄️ Schema Overview

**5 tables** were designed targeting 3NF. Relationships between tables are managed with Foreign Keys; the many-to-many relationship between Emlaklar and Ozellikler is resolved through a separate junction table.

```
Ekip ──(1:N)──► Emlaklar
                    │
                   (N)
                    ▼
          Emlak_Ozellikleri   ← junction table (M:N)
                    │
                   (N)
                    ▼
             Ozellikler ──(N:1)──► Ozellik_Kategorileri
```

| Table | Records | Description |
|:---|:---:|:---|
| Ekip | 2 | Agent and store owner |
| Emlaklar | 5 | Real listings with IlanID 1000–1004 |
| Ozellik_Kategorileri | 3 | Interior Feature / Exterior Feature / Orientation |
| Ozellikler | 33 | Full feature pool |
| Emlak_Ozellikleri | 26 | Listing–feature mappings |

For the full ERD and column details → **[SCHEMA.md](./SCHEMA.md)**

---

## ⚙️ Planned SQL Features

| # | Feature | Purpose |
|:---:|:---|:---|
| 1 | `INNER JOIN` / `LEFT JOIN` | Table joins; agent–listing matching |
| 2 | `WHERE` + `IN` / `BETWEEN` | Region, price range, and multi-criteria filtering |
| 3 | `GROUP BY` + `HAVING` | Agent-based portfolio grouping and filtering |
| 4 | `COUNT` / `SUM` / `AVG` | Total listings, portfolio value, average price per m² |
| 5 | `ORDER BY` | Sorting by price or square meters |
| 6 | `VIEW` | Converting frequently used queries into reusable views |
| 7 | `CTE` | Step-by-step structured, readable complex queries |
| 8 | `INDEX` | Query acceleration via indexing on price and district columns |

---

## 🔍 Example Queries

### Query 1 — General Listing List `(INNER JOIN)`

Lists all active listings with the responsible agent's name and contact information.

```sql
SELECT E.Baslik, E.Fiyat, E.İlce, E.EmlakTipi,
       K.AdSoyad AS Danisman_Adi,
       K.Telefon
FROM   Emlaklar E
INNER JOIN Ekip K ON E.DanismanID = K.DanismanID;
```

---

### Query 2: Budget and Region Filtering (WHERE, IN)

The goal is to retrieve apartments with a budget of 40,000 TL or less, specifically in the Şişli and Beyoğlu districts (İstiklal, Cihangir, Firuzağa, etc.).

```sql
SELECT Baslik, Fiyat, İlce, Mahalle 
FROM Emlaklar 
WHERE Fiyat <= 40000 AND İlce IN ('Şişli', 'Beyoğlu')
ORDER BY Fiyat DESC;
```
---

### Query 3 — Staff Portfolio Analysis `(GROUP BY + SUM + COUNT)`

Calculates the number of listings managed by each agent and the total portfolio value (TL). Thanks to LEFT JOIN, agents with no listings yet are also included in the list.

```sql
SELECT K.AdSoyad,
       COUNT(E.IlanID) AS ToplamIlanSayisi,
       SUM(E.Fiyat)    AS ToplamPortfoyDegeri
FROM   Ekip K
LEFT JOIN Emlaklar E ON K.DanismanID = E.DanismanID
GROUP BY K.AdSoyad;
```

---

### Query 4 — Feature-Based Filtering `(4-Table JOIN)`

Retrieves listings with elevator or air conditioning along with the feature category. This query, which chains four tables via JOIN, demonstrates the practical use of the junction table.

```sql
SELECT DISTINCT E.Baslik, E.Fiyat,
                Oz.OzellikAdi, Kat.KategoriAdi
FROM   Emlaklar E
INNER JOIN Emlak_Ozellikleri EO     ON E.IlanID      = EO.IlanID
INNER JOIN Ozellikler Oz            ON EO.OzellikID  = Oz.OzellikID
INNER JOIN Ozellik_Kategorileri Kat ON Oz.KategoriID = Kat.KategoriID
WHERE  Oz.OzellikAdi IN ('Asansör', 'Klima');
```

---

### Query 5 — Rent Cost per m² `(Arithmetic)`

Calculates the monthly rent cost per gross and net square meter for each listing.

```sql
SELECT Baslik, Fiyat, BrutM2, NetM2,
       ROUND(Fiyat / BrutM2, 0) AS BrutM2_Fiyati,
       ROUND(Fiyat / NetM2, 0)  AS NetM2_Fiyati
FROM   Emlaklar
WHERE  BrutM2 > 0 AND NetM2 > 0
ORDER BY NetM2_Fiyati DESC;
```

---

## 🚀 Running

```bash
# Open the existing database
sqlite3 njoyemlak.db

# Create from scratch using the SQL script
sqlite3 new.db < njoy_veritabani.sql
```

---
