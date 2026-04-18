# 🏢 Njoy Emlak — İlişkisel Veritabanı Projesi

> 📍 Gerçek veri kaynağı: **[njoyemlak.com](http://www.njoyemlak.com/)** — İstanbul'da aktif bir gayrimenkul ofisinin portföyü üzerine tasarlanmış SQLite veritabanı.

---

## 👥 Ekip Üyeleri

| | | |
|:---|:---|:---|
| Altay Yeles | Alper Güner | Mustafa Ulaş Karaaslan |
| Mehmet Can Öztürk | Emre Aslan | 

---

## 📌 Proje Fikri

Bu proje, **gerçek hayattaki bir problemin çözümü** olarak ortaya çıkmıştır. Ekip arkadaşımız **Alper Güner**'in dayısının aktif olarak faaliyet gösteren emlak şirketi **[Njoy Emlak](http://www.njoyemlak.com/)** bu projenin doğrudan ilham ve veri kaynağıdır.

Küçük ve orta ölçekli emlak ofisleri, portföyleri büyüdükçe ilan, danışman ve özellik verilerini sağlıklı biçimde yönetmekte zorlanır. Dağıtık Excel dosyaları ve hazır platformlara bağımlılık; **veri tekrarı**, **güncelleme anomalileri** ve **yetersiz raporlama** gibi kritik sorunlara yol açmaktadır.

Bu proje, söz konusu sorunları çözmek amacıyla Njoy Emlak ofisinin **gerçek portföyü** üzerinden normalize edilmiş ve sorgulanabilir bir ilişkisel veritabanı tasarlamak için başlatılmıştır.

> ⚠️ **Veri Toplama Yöntemi:** Veritabanındaki tüm ilan verileri **njoyemlak.com** sitesinden **manuel olarak toplanmıştır (data scraping)**. 5 aktif ilan ile bu ilanların tüm iç özellik, dış özellik ve cephe bilgileri sisteme girilmiştir. Yapay veya uydurma veri kullanılmamıştır.

---

## 🎯 Neden Önemli?

| Mevcut Sorun | Sağlanan Çözüm |
|:---|:---|
| Dağıtık ilan yönetimi | Tek merkezi, normalize edilmiş veritabanı |
| Danışman değişince veriler bozulur | Foreign Key ile referans bütünlüğü |
| Özellik bazlı arama yapılamıyor | Junction tablosu + zincirleme JOIN |
| Portföy performansı ölçülemiyor | GROUP BY + SUM + COUNT analizleri |
| m² başına fiyat hesaplanamıyor | Aritmetik operatörlerle anlık hesaplama |

---

## 📁 Repo Yapısı

```
njoy-emlak-db/
├── README.md                          ← Bu dosya
├── SCHEMA.md                          ← ERD ve tablo açıklamaları
├── njoy_veritabani.sql                ← Veritabanı oluşturma + veri scripti
├── njoyemlak.db                       ← Derlenmiş SQLite veritabanı
└── Teknik_Rapor.pdf                   ← Teknik rapor
```

---

## 🗄️ Şema Özeti

3NF hedeflenerek **5 tablo** tasarlanmıştır. Tablolar arası ilişkiler Foreign Key ile yönetilmekte; Emlaklar ile Özellikler arasındaki çoka-çok ilişki ayrı bir köprü tablosuyla çözülmektedir.

```
Ekip ──(1:N)──► Emlaklar
                    │
                   (N)
                    ▼
          Emlak_Ozellikleri   ← köprü tablosu (M:N)
                    │
                   (N)
                    ▼
             Ozellikler ──(N:1)──► Ozellik_Kategorileri
```

| Tablo | Kayıt | Açıklama |
|:---|:---:|:---|
| Ekip | 2 | Danışman ve mağaza sahibi |
| Emlaklar | 5 | IlanID 1000–1004 arası gerçek ilanlar |
| Ozellik_Kategorileri | 3 | İç Özellik / Dış Özellik / Cephe |
| Ozellikler | 33 | Tüm özellik havuzu |
| Emlak_Ozellikleri | 26 | İlan–özellik eşleştirmeleri |

Tam ERD ve sütun detayları için → **[SCHEMA.md](./SCHEMA.md)**

---

## ⚙️ Kullanılması Planlanan SQL Özellikleri

| # | Özellik | Amaç |
|:---:|:---|:---|
| 1 | `INNER JOIN` / `LEFT JOIN` | Tablolar arası birleştirme; danışman–ilan eşleştirmesi |
| 2 | `WHERE` + `IN` / `BETWEEN` | Bölge, fiyat aralığı ve çoklu kriter filtresi |
| 3 | `GROUP BY` + `HAVING` | Danışman bazlı portföy gruplama ve filtreleme |
| 4 | `COUNT` / `SUM` / `AVG` | Toplam ilan, portföy değeri, ortalama m² fiyatı |
| 5 | `ORDER BY` | Fiyat veya metrekareye göre sıralama |
| 6 | `VIEW` | Sık kullanılan sorguların yeniden kullanılabilir görünüme dönüştürülmesi |
| 7 | `CTE`  | Adım adım yapılandırılmış, okunabilir karmaşık sorgular |
| 8 | `INDEX` | Fiyat ve ilçe sütunlarına index ile sorgu hızlandırma |

---

## 🔍 Örnek Sorgular

### Sorgu 1 — Genel İlan Listesi `(INNER JOIN)`

Tüm aktif ilanları sorumlu danışmanın adı ve iletişim bilgisiyle listeler.

```sql
SELECT E.Baslik, E.Fiyat, E.İlce, E.EmlakTipi,
       K.AdSoyad AS Danisman_Adi,
       K.Telefon
FROM   Emlaklar E
INNER JOIN Ekip K ON E.DanismanID = K.DanismanID;
```

---

### Sorgu 2 — Personel Portföy Analizi `(GROUP BY + SUM + COUNT)`

Her danışmanın yönettiği ilan sayısını ve toplam portföy değerini (TL) hesaplar. LEFT JOIN sayesinde henüz ilanı olmayan danışmanlar da listeye dahil edilir.

```sql
SELECT K.AdSoyad,
       COUNT(E.IlanID) AS ToplamIlanSayisi,
       SUM(E.Fiyat)    AS ToplamPortfoyDegeri
FROM   Ekip K
LEFT JOIN Emlaklar E ON K.DanismanID = E.DanismanID
GROUP BY K.AdSoyad;
```

---

### Sorgu 3 — Özellik Bazlı Filtreleme `(4 Tablo JOIN)`

Asansörlü veya klimalı ilanları özellik kategorisiyle birlikte getirir. Dört tablonun zincirleme JOIN ile birleştirildiği bu sorgu, köprü tablosunun pratik kullanımını göstermektedir.

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

### Sorgu 4 — m² Başına Kira Maliyeti `(Aritmetik)`

Her ilanın brüt ve net metrekare başına düşen aylık kira maliyetini hesaplar.

```sql
SELECT Baslik, Fiyat, BrutM2, NetM2,
       ROUND(Fiyat / BrutM2, 0) AS BrutM2_Fiyati,
       ROUND(Fiyat / NetM2, 0)  AS NetM2_Fiyati
FROM   Emlaklar
WHERE  BrutM2 > 0 AND NetM2 > 0
ORDER BY NetM2_Fiyati DESC;
```

---

## 🚀 Çalıştırma

```bash
# Mevcut veritabanını aç
sqlite3 njoyemlak.db

# SQL scriptinden sıfırdan oluştur
sqlite3 yeni.db < njoy_veritabani.sql
```

---

> Veri Kaynağı: njoyemlak.com · Veriler aktif portföyden manuel olarak toplanmıştır.
