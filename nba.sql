-- ===========================================
-- NBA Ligi Veritabanı (MySQL)
-- ===========================================

-- Önce güvenli şekilde sil
DROP TABLE IF EXISTS oyuncu_mac_istatistikleri;
DROP TABLE IF EXISTS stadyumlar;
DROP TABLE IF EXISTS maclar;
DROP TABLE IF EXISTS oyuncular;
DROP TABLE IF EXISTS takimlar;

-- ===========================================
-- 1) TAKIMLAR TABLOSU
-- ===========================================
CREATE TABLE takimlar (
    takim_id        INT AUTO_INCREMENT PRIMARY KEY,
    takim_adi       VARCHAR(100) NOT NULL UNIQUE,
    konferans       ENUM('Doğu', 'Batı') NOT NULL,
    sehir           VARCHAR(100),
    kurulus_yili    SMALLINT
);

-- ===========================================
-- 2) OYUNCULAR TABLOSU
-- ===========================================
CREATE TABLE oyuncular (
    oyuncu_id       INT AUTO_INCREMENT PRIMARY KEY,
    takim_id        INT,
    ad_soyad        VARCHAR(100) NOT NULL,
    pozisyon        VARCHAR(10),
    boy_cm          DECIMAL(5,1),
    kilo_kg         DECIMAL(5,1),
    dogum_tarihi    DATE,
    ulke            VARCHAR(100),

    FOREIGN KEY (takim_id)
        REFERENCES takimlar(takim_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
);

-- ===========================================
-- 3) MAÇLAR TABLOSU
-- ===========================================
CREATE TABLE maclar (
    mac_id                  INT AUTO_INCREMENT PRIMARY KEY,
    ev_sahibi_takim_id      INT NOT NULL,
    deplasman_takim_id      INT NOT NULL,
    mac_tarihi              DATE NOT NULL,
    sezon                   VARCHAR(9) NOT NULL,  -- Örn: 2015-2016
    arena_adi               VARCHAR(150),

    CONSTRAINT fk_ev_sahibi
        FOREIGN KEY (ev_sahibi_takim_id)
        REFERENCES takimlar(takim_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT fk_deplasman
        FOREIGN KEY (deplasman_takim_id)
        REFERENCES takimlar(takim_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT mac_takimlari_farkli_olmali
        CHECK (ev_sahibi_takim_id <> deplasman_takim_id)
);

-- ===========================================
-- 4) STADYUMLAR TABLOSU
-- ===========================================
CREATE TABLE stadyumlar (
    stadyum_id          INT AUTO_INCREMENT PRIMARY KEY,
    ev_sahibi_takim_id  INT UNIQUE,
    stadyum_adi         VARCHAR(150) NOT NULL,
    sehir               VARCHAR(100),
    kapasite            INT CHECK (kapasite > 0),

    FOREIGN KEY (ev_sahibi_takim_id)
        REFERENCES takimlar(takim_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
);

-- ===========================================
-- 5) OYUNCU MAÇ İSTATİSTİKLERİ TABLOSU
-- ===========================================
CREATE TABLE oyuncu_mac_istatistikleri (
    istatistik_id       INT AUTO_INCREMENT PRIMARY KEY,
    oyuncu_id           INT NOT NULL,
    mac_id              INT NOT NULL,
    attigi_sayi         SMALLINT DEFAULT 0,
    asist_sayisi        SMALLINT DEFAULT 0,
    ribaund_sayisi      SMALLINT DEFAULT 0,
    oynadigi_dakika     DECIMAL(4,1) DEFAULT 0,

    -- İlişkiler
    FOREIGN KEY (oyuncu_id)
        REFERENCES oyuncular(oyuncu_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    FOREIGN KEY (mac_id)
        REFERENCES maclar(mac_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    -- Bir oyuncu bir maçta sadece bir kayıt tutabilir
    UNIQUE (oyuncu_id, mac_id)
);

-- ===========================================
-- Performans Index'leri
-- ===========================================
CREATE INDEX idx_oyuncular_takim_id ON oyuncular(takim_id);
CREATE INDEX idx_maclar_tarih ON maclar(mac_tarihi);
CREATE INDEX idx_istatistikler_mac_id ON oyuncu_mac_istatistikleri(mac_id);
CREATE INDEX idx_istatistikler_oyuncu_id ON oyuncu_mac_istatistikleri(oyuncu_id);

