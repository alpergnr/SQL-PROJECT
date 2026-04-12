# NJOY EMLAK VERİTABANI PROJESİ - TEKNİK RAPOR

## 1. GİRİŞ VE PROJENİN AMACI
Bu proje kapsamında gerçek hayattan, aktif olarak faaliyet gösteren **Njoy Emlak (http://www.njoyemlak.com/)** platformu baz alınarak rölyasyonel (ilişkisel) bir veritabanı tasarlanmıştır. Veritabanının amacı; gayrimenkul ofisinin portföyündeki ilanları, emlak danışmanlarını, gayrimenkullerin iç, dış ve cephe gibi detaylı özelliklerini tek bir sistemde bütünleşik bir biçimde saklamak ve bu verilerden anlamlı raporlar çekebilmektir. 

Veritabanı yapılandırılırken platformdaki güncel 5 farklı ilan veri olarak çekilmiş, özellikle **Cihangir Sıraselviler Ofis** ve **Taksim İstiklal Paralel Daire** gibi spesifik ilanların tüm teknik özellikleri (iç, dış ve cephe verileri) baz alınarak sisteme dahil edilmiştir. SQL kodları platform bağımsız, en yaygın kullanılan dosya tabanlı veritabanı sistemi olan **SQLite** altyapısına uyumlu olarak (`AUTOINCREMENT` yapısıyla) yazılmış ve derlenmiştir.

## 2. VERİTABANI MİMARİSİ VE TABLOLAR

Sistemdeki verilerin tekrarını (redundancy) önlemek ve veri bütünlüğünü (integrity) sağlamak amacıyla normalizasyon kurallarına uyularak 5 temel tablo tasarlanmıştır.

### 2.1. Ekip Tablosu
Emlak ofisinde çalışan danışmanların verilerini tutar.
- **DanismanID (Primary Key):** Danışmanın sistemdeki benzersiz numarası (Otomatik artan).
- **AdSoyad:** Personelin tam adı.
- **Unvan:** Mağaza Sahibi veya Danışman gibi pozisyon bilgisi.
- **Telefon:** İletişim numarası.

### 2.2. Emlaklar (İlanlar) Tablosu
Platformda yayınlanan kiralık ve satılık gayrimenkul kayıtlarının temel ana verilerini saklar.
- **IlanID (Primary Key):** İlanın benzersiz sistem numarası. Örnek verilerde 1000'den 1004'e kadar özel olarak atanmıştır.
- **DanismanID (Foreign Key):** İlanla ilgilenen danışmanın referansı.
- **Baslik, Fiyat, EmlakTipi:** İlanın temel verileri.
- **İl, İlce, Mahalle:** Gayrimenkul lokasyon bilgisi.
- **BrutM2, NetM2, OdaSayisi:** Fiziksel donanım bilgileri.

### 2.3. Ozellik_Kategorileri Tablosu
Njoy Emlak platformundaki özelliklerin gruplandığı ana başlıklardır.
- **KategoriID (Primary Key)**
- **KategoriAdi:** 'İç Özellik', 'Dış Özellik', 'Cephe' gibi sınıflandırmalar.

### 2.4. Ozellikler Tablosu
Kategorilere bağlı olan alt özelliklerin havuzudur (Adsl, Çelik Kapı, Asansör, Doğu Cephe vb.).
- **OzellikID (Primary Key)**
- **KategoriID (Foreign Key):** Özelliğin ait olduğu kategorinin referansı.
- **OzellikAdi:** Özelliğin açık metni.

### 2.5. Emlak_Ozellikleri (Junction / Köprü Tablosu)
Çoka çok (Many-to-Many) ilişkiyi çözen bağlayıcı tablodur. Örneğin Cihangir'deki bir ofisin/dairenin veya Taksim İstiklal Paraleli'ndeki bir dairenin kendisine ait asansör, çelik kapı, ADSL bağlamları vardır. Aynı zamanda 'Asansör' özelliği onlarca ilanda bulunabilir.
- **IlanID (Foreign Key)**
- **OzellikID (Foreign Key)**
*(Primary Key olarak bu iki anahtarın bileşimi Composite Key tanımlanmıştır.)*

---

## 3. VERİ ÇEKME - SQL SORGULARI VE ANALİZLER

Veritabanı oluşturulduktan sonra çekilen veriler üzerinde iş zekası ve raporlama süreçleri için aşağıdaki 5 farklı SQL sorgusu geliştirilmiştir.

### Sorgu 1: Genel İlan Listesi ve İletişim Bilgileri (INNER JOIN)
Müşterilerin en çok ihtiyaç duyduğu "Hangi ilana kim bakıyor?" sorusunun yanıtı için `Emlaklar` ve `Ekip` tabloları birleştirilmiştir.

```sql
SELECT E.Baslik, E.Fiyat, E.İlce, E.Mahalle, E.EmlakTipi, 
       K.AdSoyad AS [Danisman_Adi], K.Telefon 
FROM Emlaklar E
INNER JOIN Ekip K ON E.DanismanID = K.DanismanID;
```
**Açıklama:** İlanların sadece başlık, fiyat ve mahalle bilgisiyle birlikte ondan sorumlu olan emlak danışmanının iletişim numarası tek bir sonuç seti olarak listelenir.

### Sorgu 2: Bütçe ve Bölge Filtrelemesi (WHERE, IN)
Özellikle Şişli ve Beyoğlu lokasyonlarında (İstiklal, Cihangir, Firuzağa vb) uygun 40.000 TL ve altı bütçeli dairelerin getirilmesi hedeflenmiştir.

```sql
SELECT Baslik, Fiyat, İlce, Mahalle 
FROM Emlaklar 
WHERE Fiyat <= 40000 AND İlce IN ('Şişli', 'Beyoğlu')
ORDER BY Fiyat DESC;
```
**Açıklama:** `IN` operatörü ile çoklu lokasyon filtresi kullanılmış ve `ORDER BY` ile fiyatlar büyükten küçüğe sıralanmıştır.

### Sorgu 3: Personel Performans ve Portföy Analizi (GROUP BY, SUM, COUNT)
Yönetim kademesinin, hangi danışmanın ne kadarlık bir portföyü (TL olarak) yönettigini görmek için tasarlanan finansal sorgudur.

```sql
SELECT K.AdSoyad, COUNT(E.IlanID) AS ToplamIlanSayisi, SUM(E.Fiyat) AS ToplamPortfoyDegeri
FROM Ekip K
LEFT JOIN Emlaklar E ON K.DanismanID = E.DanismanID
GROUP BY K.AdSoyad;
```
**Açıklama:** Danışmanlar gruplanarak (`GROUP BY`), üzerlerine zimmetli ilanların toplam sayısı (`COUNT`) ve toplam kira geliri yönetimi (`SUM`) çıkarılmıştır.

### Sorgu 4: Lüks Kriterlere Göre Veri Filtreleme (ÇOKLU JOIN)
Siteden veri çekerken "Cephe" ve "İç Özellikler" kısımlarını tablolara aktarmamızın asıl amacı bu sorgudur. Asansörlü veya Klimalı bir portföy arayan gayrimenkul müşterileri için kullanılır.

```sql
SELECT DISTINCT E.Baslik, E.Fiyat, Oz.OzellikAdi, Kat.KategoriAdi
FROM Emlaklar E
INNER JOIN Emlak_Ozellikleri EO ON E.IlanID = EO.IlanID
INNER JOIN Ozellikler Oz ON EO.OzellikID = Oz.OzellikID
INNER JOIN Ozellik_Kategorileri Kat ON Oz.KategoriID = Kat.KategoriID
WHERE Oz.OzellikAdi IN ('Asansör', 'Klima');
```
**Açıklama:** 4 farklı tablo birbirine `INNER JOIN` ile bağlanmış, sonuçta sadece özellikleri arasında 'Asansör' veya 'Klima' geçen rezidans ve ofisler çıkartılmıştır. Veri tekrarını önlemek için `DISTINCT` komutu kullanılmıştır.

### Sorgu 5: Metrekare Verimliliği (BÖLME İŞLEMİ)
Ticari işletmelerde bir ilanın metrekare başına istenen ortalama kira rakamını bulmak için matemtatiksel operasyon gerçekleştirildi.

```sql
SELECT Baslik, Fiyat, BrutM2, NetM2, 
       (Fiyat / BrutM2) AS BrutM2_Fiyati, 
       (Fiyat / NetM2) AS NetM2_Fiyati
FROM Emlaklar
WHERE BrutM2 > 0 AND NetM2 > 0;
```
**Açıklama:** Belirtilen fiyata oranla gayrimenkulün brüt ve net metrekare başına maliyeti otomatik olarak hesaplanır.

---

## 4. SONUÇ
Njoy Emlak platformundan çekilen gerçek veriler kullanılarak normalizasyon kurallarına uygun, genişletilebilir ve SQLite uyumlu ilişkisel veri tabanı sistemi başarıyla kurulmuştur. Gerçek ofis ve taksim daire ilanlarının özelliklerini çoktan çoka ilişkilerle sorunsuz harmanlayan bu sistem, tüm SQL motorlarında çalışabilmektedir. Üretilen veritabanı (db) dosyası modern yazılımlarla doğrudan rapor sunumuna hazırdır.
