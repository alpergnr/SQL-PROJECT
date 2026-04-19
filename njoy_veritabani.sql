-- ==============================================================================
-- NJOY EMLAK VERİTABANI OLUŞTURMA SCRIPT'I
-- ==============================================================================

-- 1. TABLOLARI OLUŞTURMA

CREATE TABLE Ekip (
    DanismanID INTEGER PRIMARY KEY AUTOINCREMENT,
    AdSoyad VARCHAR(100) NOT NULL,
    Unvan VARCHAR(50),
    Telefon VARCHAR(20)
);

CREATE TABLE Emlaklar (
    IlanID INTEGER PRIMARY KEY AUTOINCREMENT,
    DanismanID INT,
    Baslik VARCHAR(255) NOT NULL,
    Fiyat DECIMAL(18, 2) NOT NULL,
    İl VARCHAR(50),
    İlce VARCHAR(50),
    Mahalle VARCHAR(100),
    EmlakTipi VARCHAR(50),
    BrutM2 INT,
    NetM2 INT,
    OdaSayisi VARCHAR(20),
    FOREIGN KEY (DanismanID) REFERENCES Ekip(DanismanID)
);

CREATE TABLE Ozellik_Kategorileri (
    KategoriID INTEGER PRIMARY KEY AUTOINCREMENT,
    KategoriAdi VARCHAR(50) NOT NULL -- (İç Özellik, Dış Özellik, Cephe vb.)
);

CREATE TABLE Ozellikler (
    OzellikID INTEGER PRIMARY KEY AUTOINCREMENT,
    KategoriID INT,
    OzellikAdi VARCHAR(100) NOT NULL,
    FOREIGN KEY (KategoriID) REFERENCES Ozellik_Kategorileri(KategoriID)
);

CREATE TABLE Emlak_Ozellikleri (
    IlanID INT,
    OzellikID INT,
    PRIMARY KEY (IlanID, OzellikID),
    FOREIGN KEY (IlanID) REFERENCES Emlaklar(IlanID),
    FOREIGN KEY (OzellikID) REFERENCES Ozellikler(OzellikID)
);

-- ==============================================================================
-- 2. ÖRNEK VERİLERİ EKLEME (INSERT İşlemleri)

-- Ekip (Danışmanlar) Verileri
INSERT INTO Ekip (AdSoyad, Unvan, Telefon) VALUES
('Selim Gürses', 'Danışman', '0 (531) 700 34 74'),
('Fatih Işık', 'Mağaza Sahibi', '0 (532) 495 16 50');

-- Kategori Verileri
INSERT INTO Ozellik_Kategorileri (KategoriAdi) VALUES 
('İç Özellik'), ('Dış Özellik'), ('Cephe');

-- Özellik Verileri
-- İç Özellikler (KategoriID = 1)
INSERT INTO Ozellikler (KategoriID, OzellikAdi) VALUES
(1, 'ADSL'), (1, 'Ahşap Doğrama'), (1, 'Akıllı Ev'), (1, 'Alarm (Hırsız)'),
(1, 'Alarm (Yangın)'), (1, 'Alaturka Tuvalet'), (1, 'Alüminyum Doğrama'), (1, 'Amerikan Kapı'),
(1, 'Ankastre Fırın'), (1, 'Barbekü'), (1, 'Beyaz Eşya'), (1, 'Boyalı'),
(1, 'Bulaşık Makinesi'), (1, 'Buzdolabı'), (1, 'Çamaşır Kurutma Makinesi'), (1, 'Çamaşır Makinesi'),
(1, 'Çamaşır Odası'), (1, 'Çelik Kapı'), (1, 'Duşakabin'), (1, 'Duvar Kağıdı'),
(1, 'Ebeveyn Banyosu'), (1, 'Fiber İnternet'), (1, 'Fırın'), (1, 'Giyinme Odası'),
(1, 'Gömme Dolap'), (1, 'Görüntülü Diyafon'), (1, 'Hilton Banyo'), (1, 'Intercom Sistemi'),
(1, 'Isıcam'), (1, 'Jakuzi'), (1, 'Kapalı / Cam Balkon'), (1, 'Kartonpiyer'),
(1, 'Kiler'), (1, 'Klima'), (1, 'Küvet'), (1, 'Laminat Zemin'),
(1, 'Marley'), (1, 'Mobilya'), (1, 'Mutfak (Ankastre)'), (1, 'Mutfak (Laminat)'),
(1, 'Mutfak Doğalgazı'), (1, 'Panjur/Jaluzi'), (1, 'Parke Zemin'), (1, 'PVC Doğrama'),
(1, 'Seramik Zemin'), (1, 'Set Üstü Ocak'), (1, 'Spot Aydınlatma'), (1, 'Şofben'),
(1, 'Şömine'), (1, 'Teras'), (1, 'Termosifon'), (1, 'Vestiyer'),
(1, 'Yüz Tanıma & Parmak İzi');

-- Dış Özellikler (KategoriID = 2)
INSERT INTO Ozellikler (KategoriID, OzellikAdi) VALUES
(2, '24 Saat Güvenlik'), (2, 'Apartman Görevlisi'), (2, 'Araç Şarj İstasyonu'), (2, 'Buhar Odası'),
(2, 'Çocuk Oyun Parkı'), (2, 'Hamam'), (2, 'Hidrofor'), (2, 'Isı Yalıtımı'),
(2, 'Jeneratör'), (2, 'Kablo TV'), (2, 'Kamera Sistemi'), (2, 'Köpek Parkı'),
(2, 'Kreş'), (2, 'Müstakil Havuzlu'), (2, 'Sauna'), (2, 'Ses Yalıtımı'),
(2, 'Siding'), (2, 'Spor Alanı'), (2, 'Su Deposu'), (2, 'Tenis Kortu'),
(2, 'Uydu'), (2, 'Yangın Merdiveni'), (2, 'Yüzme Havuzu (Açık)'), (2, 'Yüzme Havuzu (Kapalı)');

-- Cephe (KategoriID = 3)
INSERT INTO Ozellikler (KategoriID, OzellikAdi) VALUES 
(3, 'Doğu'), (3, 'Batı'), (3, 'Güney'), (3, 'Kuzey');

-- Emlak İlanları Verileri
INSERT INTO Emlaklar (IlanID, DanismanID, Baslik, Fiyat, İl, İlce, Mahalle, EmlakTipi, BrutM2, NetM2, OdaSayisi) VALUES 
(1000, 1, 'CİHANGİR FİRUZAĞA DA KİRALIK TERASLI DAİRE MANZARALI FOR RENT', 40000, 'İstanbul', 'Beyoğlu', 'Firuzağa Mh.', 'Kiralık Daire', 80, 60, '1+1'),
(1001, 1, 'TAKSİM GÜMÜŞSUYU KİRALIK 2+1 DAİRE FOR RENT APARTMENT NEAR METRO', 50000, 'İstanbul', 'Beyoğlu', 'Gümüşsuyu Mh.', 'Kiralık Daire', 100, 90, '2+1'),
(1002, 2, 'FOR RENT ELYSIUM TAKSİM RESIDENCE FURNISHED APARTMENT KİRALIK', 49000, 'İstanbul', 'Şişli', 'İnönü Mh.', 'Kiralık Rezidans', 100, 76, '1+1'),
(1003, 1, 'CİHANGİR SIRASELVİLER CADDESİ ÜZERİ KİRALIK OFİS BÜRO FOR RENT', 30000, 'İstanbul', 'Beyoğlu', 'Cihangir Mah.', 'Kiralık Ofis', 60, 60, '1+1'),
(1004, 2, 'TAKSİM İSTİKLAL CADDE PARALELİ KİRALIK DAİRE FOR RENT NEAR METRO', 35000, 'İstanbul', 'Beyoğlu', 'İstiklal Mh.', 'Kiralık Daire', 80, 65, '2+1'),
(1005, 2, 'CİHANGİR FİRUZAĞA KİRALIK 2+1 DAİRE APARTMENT FOR RENT NEAR TRAM', 42000, 'İstanbul', 'Beyoğlu', 'Firuzağa Mh.', 'Kiralık Daire', 80, 70, '2+1'),
(1006, 1, 'FOR RENT SEA VIEW APARTMENT IN CIHANGIR NEW CARE BUILDING LIFT', 66000, 'İstanbul', 'Beyoğlu', 'Cihangir Mh.', 'Kiralık Daire', 75, 65, '1+1'),
(1007, 2, 'CİHANGİR FİRUZAĞA DA KİRALIK LÜKS DUBLEKS DAİRE BAHÇELİ FOR RENT', 56000, 'İstanbul', 'Beyoğlu', 'Firuzağa Mh.', 'Kiralık Daire', 70, 65, '1+1'),
(1008, 2, 'FOR RENT FURNISHED APARTMENT CİHANGİR KİRALIK EŞYALI 2+1 DAİRE', 57000, 'İstanbul', 'Beyoğlu', 'Firuzağa Mh.', 'Kiralık Daire', 70, 60, '2+1'),
(1009, 2, 'CİHANGİR KİRALIK EŞYALI 1+1 DAİRE FOR RENT FURNISHED APARTMENT', 35000, 'İstanbul', 'Beyoğlu', 'Kuloğlu Mh.', 'Kiralık Daire', 45, 40, '1+1');

-- İlanların Özelliklerini Eşleştirme Sistemi

-- 1. İlan (Cihangir Teraslı Daire - ID: 1000)
INSERT INTO Emlak_Ozellikleri (IlanID, OzellikID) VALUES
-- İç Özellikler
(1000, 1),  -- ADSL
(1000, 8),  -- Amerikan Kapı
(1000, 9),  -- Ankastre Fırın
(1000, 10), -- Barbekü
(1000, 11), -- Beyaz Eşya
(1000, 12), -- Boyalı
(1000, 14), -- Buzdolabı
(1000, 18), -- Çelik Kapı
(1000, 19), -- Duşakabin
(1000, 22), -- Fiber İnternet
(1000, 27), -- Hilton Banyo
(1000, 29), -- Isıcam
(1000, 32), -- Kartonpiyer
(1000, 36), -- Laminat Zemin
(1000, 39), -- Mutfak (Ankastre)
(1000, 40), -- Mutfak (Laminat)
(1000, 41), -- Mutfak Doğalgazı
(1000, 44), -- PVC Doğrama
(1000, 45), -- Seramik Zemin
(1000, 46), -- Set Üstü Ocak
(1000, 47), -- Spot Aydınlatma
(1000, 50), -- Teras
-- Dış Özellikler
(1000, 61), -- Isı Yalıtımı
(1000, 64), -- Kamera Sistemi
(1000, 74), -- Uydu
-- Cephe
(1000, 78), -- Doğu
(1000, 80); -- Güney

-- 2. İlan (Gümüşsuyu 2+1 - ID: 1001)
INSERT INTO Emlak_Ozellikleri (IlanID, OzellikID) VALUES
-- İç Özellikler
(1001, 1),  -- ADSL
(1001, 12), -- Boyalı
(1001, 18), -- Çelik Kapı
(1001, 19), -- Duşakabin
(1001, 27), -- Hilton Banyo
(1001, 29), -- Isıcam
(1001, 32), -- Kartonpiyer
(1001, 36), -- Laminat Zemin
(1001, 40), -- Mutfak (Laminat)
(1001, 41), -- Mutfak Doğalgazı
(1001, 44), -- PVC Doğrama
-- Dış Özellikler
(1001, 61), -- Isı Yalıtımı
(1001, 74), -- Uydu
-- Cephe
(1001, 78), -- Doğu
(1001, 79); -- Batı

-- 3. İlan (Elysium Taksim Residence - ID: 1002)
INSERT INTO Emlak_Ozellikleri (IlanID, OzellikID) VALUES
-- İç Özellikler
(1002, 1),  -- ADSL
(1002, 8),  -- Amerikan Kapı
(1002, 9),  -- Ankastre Fırın
(1002, 11), -- Beyaz Eşya
(1002, 12), -- Boyalı
(1002, 13), -- Bulaşık Makinesi
(1002, 14), -- Buzdolabı
(1002, 16), -- Çamaşır Makinesi
(1002, 18), -- Çelik Kapı
(1002, 19), -- Duşakabin
(1002, 22), -- Fiber İnternet
(1002, 25), -- Gömme Dolap
(1002, 26), -- Görüntülü Diyafon
(1002, 27), -- Hilton Banyo
(1002, 29), -- Isıcam
(1002, 32), -- Kartonpiyer
(1002, 34), -- Klima
(1002, 36), -- Laminat Zemin
(1002, 38), -- Mobilya
(1002, 39), -- Mutfak (Ankastre)
(1002, 40), -- Mutfak (Laminat)
(1002, 41), -- Mutfak Doğalgazı
(1002, 42), -- Panjur/Jaluzi
(1002, 43), -- Parke Zemin
(1002, 44), -- PVC Doğrama
(1002, 46), -- Set Üstü Ocak
(1002, 47), -- Spot Aydınlatma
-- Dış Özellikler
(1002, 54), -- 24 Saat Güvenlik
(1002, 55), -- Apartman Görevlisi
(1002, 56), -- Araç Şarj İstasyonu
(1002, 57), -- Buhar Odası
(1002, 60), -- Hidrofor
(1002, 61), -- Isı Yalıtımı
(1002, 62), -- Jeneratör
(1002, 63), -- Kablo TV
(1002, 64), -- Kamera Sistemi
(1002, 68), -- Sauna
(1002, 69), -- Ses Yalıtımı
(1002, 70), -- Siding
(1002, 71), -- Spor Alanı
(1002, 72), -- Su Deposu
(1002, 74), -- Uydu
(1002, 75), -- Yangın Merdiveni
(1002, 77), -- Yüzme Havuzu (Kapalı)
-- Cephe
(1002, 79), -- Batı
(1002, 80); -- Güney

-- 4. İlan (Cihangir Sıraselviler Ofis - ID: 1003)
INSERT INTO Emlak_Ozellikleri (IlanID, OzellikID) VALUES
-- İç Özellikler
(1003, 1),  -- ADSL
(1003, 18); -- Çelik Kapı

-- 5. İlan (Taksim İstiklal Paralel Daire - ID: 1004)
INSERT INTO Emlak_Ozellikleri (IlanID, OzellikID) VALUES
-- İç Özellikler
(1004, 18), -- Çelik Kapı
(1004, 29), -- Isıcam
(1004, 36), -- Laminat Zemin
(1004, 40), -- Mutfak (Laminat)
(1004, 41), -- Mutfak Doğalgazı
(1004, 44), -- PVC Doğrama
(1004, 46), -- Set Üstü Ocak
-- Dış Özellikler
(1004, 61), -- Isı Yalıtımı
-- Cephe
(1004, 78), -- Doğu
(1004, 79); -- Batı

-- 6. İlan (Cihangir 2+1 - ID: 1005)
INSERT INTO Emlak_Ozellikleri (IlanID, OzellikID) VALUES
-- İç Özellikler
(1005, 1),  -- ADSL
(1005, 8),  -- Amerikan Kapı
(1005, 9),  -- Ankastre Fırın
(1005, 11), -- Beyaz Eşya
(1005, 12), -- Boyalı
(1005, 13), -- Bulaşık Makinesi
(1005, 18), -- Çelik Kapı
(1005, 19), -- Duşakabin
(1005, 22), -- Fiber İnternet
(1005, 27), -- Hilton Banyo
(1005, 29), -- Isıcam
(1005, 32), -- Kartonpiyer
(1005, 34), -- Klima
(1005, 36), -- Laminat Zemin
(1005, 39), -- Mutfak (Ankastre)
(1005, 40), -- Mutfak (Laminat)
(1005, 41), -- Mutfak Doğalgazı
(1005, 44), -- PVC Doğrama
(1005, 45), -- Seramik Zemin
(1005, 46), -- Set Üstü Ocak
(1005, 47), -- Spot Aydınlatma
-- Dış Özellikler
(1005, 61), -- Isı Yalıtımı
(1005, 74), -- Uydu
-- Cephe
(1005, 78), -- Doğu
(1005, 80); -- Güney

-- 7. İlan (Cihangir Sea View - ID: 1006)
INSERT INTO Emlak_Ozellikleri (IlanID, OzellikID) VALUES
-- İç Özellikler
(1006, 1),  -- ADSL
(1006, 8),  -- Amerikan Kapı
(1006, 9),  -- Ankastre Fırın
(1006, 12), -- Boyalı
(1006, 16), -- Çamaşır Makinesi
(1006, 18), -- Çelik Kapı
(1006, 19), -- Duşakabin
(1006, 22), -- Fiber İnternet
(1006, 25), -- Gömme Dolap
(1006, 26), -- Görüntülü Diyafon
(1006, 27), -- Hilton Banyo
(1006, 28), -- Intercom Sistemi
(1006, 29), -- Isıcam
(1006, 32), -- Kartonpiyer
(1006, 34), -- Klima
(1006, 36), -- Laminat Zemin
(1006, 40), -- Mutfak (Laminat)
(1006, 41), -- Mutfak Doğalgazı
(1006, 44), -- PVC Doğrama
(1006, 46), -- Set Üstü Ocak
(1006, 47), -- Spot Aydınlatma
-- Dış Özellikler
(1006, 60), -- Hidrofor
(1006, 61), -- Isı Yalıtımı
(1006, 64), -- Kamera Sistemi
(1006, 65), -- Köpek Parkı
(1006, 69), -- Ses Yalıtımı
(1006, 72), -- Su Deposu
(1006, 74), -- Uydu
-- Cephe
(1006, 78), -- Doğu
(1006, 79); -- Batı

-- 8. İlan (Cihangir Lüks Dubleks - ID: 1007)
INSERT INTO Emlak_Ozellikleri (IlanID, OzellikID) VALUES
-- İç Özellikler
(1007, 1),  -- ADSL
(1007, 8),  -- Amerikan Kapı
(1007, 11), -- Beyaz Eşya
(1007, 12), -- Boyalı
(1007, 13), -- Bulaşık Makinesi
(1007, 14), -- Buzdolabı
(1007, 16), -- Çamaşır Makinesi
(1007, 19), -- Duşakabin
(1007, 22), -- Fiber İnternet
(1007, 25), -- Gömme Dolap
(1007, 26), -- Görüntülü Diyafon
(1007, 27), -- Hilton Banyo
(1007, 29), -- Isıcam
(1007, 31), -- Kapalı / Cam Balkon
(1007, 32), -- Kartonpiyer
(1007, 34), -- Klima
(1007, 36), -- Laminat Zemin
(1007, 38), -- Mobilya
(1007, 39), -- Mutfak (Ankastre)
(1007, 40), -- Mutfak (Laminat)
(1007, 41), -- Mutfak Doğalgazı
(1007, 42), -- Panjur/Jaluzi
(1007, 44), -- PVC Doğrama
(1007, 46), -- Set Üstü Ocak
(1007, 47), -- Spot Aydınlatma
-- Dış Özellikler
(1007, 60), -- Hidrofor
(1007, 61), -- Isı Yalıtımı
(1007, 64), -- Kamera Sistemi
(1007, 69), -- Ses Yalıtımı
(1007, 72), -- Su Deposu
(1007, 74), -- Uydu
-- Cephe
(1007, 79); -- Batı

-- 9. İlan (Cihangir Eşyalı 2+1 - ID: 1008)
INSERT INTO Emlak_Ozellikleri (IlanID, OzellikID) VALUES
-- İç Özellikler
(1008, 1),  -- ADSL
(1008, 8),  -- Amerikan Kapı
(1008, 11), -- Beyaz Eşya
(1008, 12), -- Boyalı
(1008, 13), -- Bulaşık Makinesi
(1008, 14), -- Buzdolabı
(1008, 16), -- Çamaşır Makinesi
(1008, 19), -- Duşakabin
(1008, 22), -- Fiber İnternet
(1008, 25), -- Gömme Dolap
(1008, 26), -- Görüntülü Diyafon
(1008, 27), -- Hilton Banyo
(1008, 29), -- Isıcam
(1008, 32), -- Kartonpiyer
(1008, 34), -- Klima
(1008, 36), -- Laminat Zemin
(1008, 38), -- Mobilya
(1008, 39), -- Mutfak (Ankastre)
(1008, 40), -- Mutfak (Laminat)
(1008, 41), -- Mutfak Doğalgazı
(1008, 42), -- Panjur/Jaluzi
(1008, 44), -- PVC Doğrama
(1008, 46), -- Set Üstü Ocak
(1008, 47), -- Spot Aydınlatma
-- Dış Özellikler
(1008, 60), -- Hidrofor
(1008, 61), -- Isı Yalıtımı
(1008, 64), -- Kamera Sistemi
(1008, 69), -- Ses Yalıtımı
(1008, 70), -- Siding
(1008, 72), -- Su Deposu
(1008, 74), -- Uydu
-- Cephe
(1008, 78), -- Doğu
(1008, 79); -- Batı

-- 10. İlan (Cihangir Eşyalı 1+1 - ID: 1009)
INSERT INTO Emlak_Ozellikleri (IlanID, OzellikID) VALUES
-- İç Özellikler
(1009, 1),  -- ADSL
(1009, 8),  -- Amerikan Kapı
(1009, 11), -- Beyaz Eşya
(1009, 12), -- Boyalı
(1009, 14), -- Buzdolabı
(1009, 18), -- Çelik Kapı
(1009, 19), -- Duşakabin
(1009, 22), -- Fiber İnternet
(1009, 25), -- Gömme Dolap
(1009, 27), -- Hilton Banyo
(1009, 29), -- Isıcam
(1009, 32), -- Kartonpiyer
(1009, 34), -- Klima
(1009, 36), -- Laminat Zemin
(1009, 38), -- Mobilya
(1009, 39), -- Mutfak (Ankastre)
(1009, 40), -- Mutfak (Laminat)
(1009, 41), -- Mutfak Doğalgazı
(1009, 42), -- Panjur/Jaluzi
(1009, 44), -- PVC Doğrama
(1009, 46), -- Set Üstü Ocak
(1009, 47), -- Spot Aydınlatma
-- Dış Özellikler
(1009, 61), -- Isı Yalıtımı
(1009, 74), -- Uydu
-- Cephe
(1009, 78), -- Doğu
(1009, 79); -- Batı
