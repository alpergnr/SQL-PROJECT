-- ==============================================================================
-- NJOY EMLAK VERİTABANI OLUŞTURMA SCRIPT'I
-- ==============================================================================

-- 1. TABLOLARI OLUŞTURMA

CREATE TABLE Ekip (
    DanismanID INTEGER PRIMARY KEY AUTOINCREMENT,
    AdSoyad VARCHAR(100) NOT NULL,
    Unvan VARCHAR(50),
    Telefon VARCHAR(30)
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
(1, 'ADSL'), (1, 'Amerikan Kapı'), (1, 'Ankastre Fırın'), (1, 'Barbekü'), 
(1, 'Beyaz Eşya'), (1, 'Boyalı'), (1, 'Buzdolabı'), (1, 'Çelik Kapı'), 
(1, 'Duşakabin'), (1, 'Fiber İnternet'), (1, 'Hilton Banyo'), (1, 'Isıcam'), 
(1, 'Kartonpiyer'), (1, 'Laminat Zemin'), (1, 'Teras'), (1, 'Klima'), 
(1, 'Parke Zemin'), (1, 'Mobilyalı'), (1, 'Bulaşık Makinesi');

-- Dış Özellikler (KategoriID = 2)
INSERT INTO Ozellikler (KategoriID, OzellikAdi) VALUES 
(2, 'Isı Yalıtımı'), (2, 'Uydu'), (2, 'Asansör'), (2, 'Güvenlik'), 
(2, 'Kapıcı'), (2, 'Otopark'), (2, 'Site İçerisinde'), (2, 'Spor Alanı'), 
(2, 'Su Deposu'), (2, 'Jeneratör');

-- Cephe (KategoriID = 3)
INSERT INTO Ozellikler (KategoriID, OzellikAdi) VALUES 
(3, 'Doğu'), (3, 'Batı'), (3, 'Güney'), (3, 'Kuzey');

-- Emlak İlanları Verileri
INSERT INTO Emlaklar (IlanID, DanismanID, Baslik, Fiyat, İl, İlce, Mahalle, EmlakTipi, BrutM2, NetM2, OdaSayisi) VALUES 
(1000, 1, 'CİHANGİR FİRUZAĞA DA KİRALIK TERASLI DAİRE MANZARALI FOR RENT', 40000, 'İstanbul', 'Beyoğlu', 'Firuzağa Mh.', 'Kiralık Daire', 80, 60, '1+1'),
(1001, 1, 'TAKSİM GÜMÜŞSUYU KİRALIK 2+1 DAİRE FOR RENT APARTMENT NEAR METRO', 50000, 'İstanbul', 'Beyoğlu', 'Gümüşsuyu Mh.', 'Kiralık Daire', 100, 90, '2+1'),
(1002, 2, 'FOR RENT ELYSIUM TAKSİM RESIDENCE FURNISHED APARTMENT KİRALIK', 49000, 'İstanbul', 'Şişli', 'İnönü Mh.', 'Kiralık Rezidans', 100, 76, '1+1'),
(1003, 1, 'CİHANGİR SIRASELVİLER CADDESİ ÜZERİ KİRALIK OFİS BÜRO FOR RENT', 30000, 'İstanbul', 'Beyoğlu', 'Cihangir Mah.', 'Kiralık Ofis', 60, 60, '1+1'),
(1004, 2, 'TAKSİM İSTİKLAL CADDE PARALELİ KİRALIK DAİRE FOR RENT NEAR METRO', 35000, 'İstanbul', 'Beyoğlu', 'İstiklal Mh.', 'Kiralık Daire', 80, 65, '2+1');

-- İlanların Özelliklerini Eşleştirme Sistemi

-- 1. İlan (Cihangir Teraslı Daire - ID: 1000)
INSERT INTO Emlak_Ozellikleri (IlanID, OzellikID) VALUES 
(1000, 1), (1000, 8), (1000, 15), -- ADSL, Çelik Kapı, Teras (İç Özellik)
(1000, 20), (1000, 21),           -- Isı yalıtımı, Uydu (Dış Özellik)
(1000, 30), (1000, 32);           -- Doğu, Güney (Cephe)

-- 2. İlan (Gümüşsuyu 2+1 - ID: 1001)
INSERT INTO Emlak_Ozellikleri (IlanID, OzellikID) VALUES 
(1001, 8), (1001, 9), (1001, 12), -- Çelik Kapı, Duşakabin, Isıcam
(1001, 20), (1001, 21),           -- Isı yalıtımı, Uydu
(1001, 31), (1001, 30);           -- Batı, Doğu

-- 3. İlan (Elysium Taksim Residence - ID: 1002)
INSERT INTO Emlak_Ozellikleri (IlanID, OzellikID) VALUES 
(1002, 16), (1002, 18), (1002, 19), -- Klima, Mobilyalı, Bulaşık Makinesi
(1002, 22), (1002, 23), (1002, 24), -- Asansör, Güvenlik, Kapıcı
(1002, 31), (1002, 32);             -- Batı, Güney

-- 4. İlan (Cihangir Sıraselviler Ofis - ID: 1003)
INSERT INTO Emlak_Ozellikleri (IlanID, OzellikID) VALUES 
(1003, 1), (1003, 8), -- ADSL, Çelik Kapı (İç)
(1003, 22);           -- Asansör (Dış)

-- 5. İlan (Taksim İstiklal Paralel Daire - ID: 1004)
INSERT INTO Emlak_Ozellikleri (IlanID, OzellikID) VALUES 
(1004, 8), (1004, 12), -- Çelik Kapı, Isıcam (İç)
(1004, 20),            -- Isı Yalıtımı (Dış)
(1004, 30);            -- Doğu (Cephe)
