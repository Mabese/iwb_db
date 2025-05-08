CREATE DATABASE iwb_system_db;
USE iwb_system_db;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role ENUM('Sales', 'Finance', 'Developer', 'Investor', 'Client', 'Partner') NOT NULL,
    mfa_secret VARCHAR(32) NOT NULL
);

CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category ENUM('RAM', 'Hard Drives', 'Motherboard Components') NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    image VARCHAR(100) NOT NULL
);

CREATE TABLE sales (
    id VARCHAR(36) PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    date DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE queries (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    status ENUM('pending', 'complete') NOT NULL,
    response TEXT
);

CREATE TABLE income_statements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    month VARCHAR(7) NOT NULL,
    revenue DECIMAL(10, 2) NOT NULL,
    expenses DECIMAL(10, 2) NOT NULL
);

INSERT INTO products (name, category, price, image) VALUES
('4GB DDR3 RAM', 'RAM', 250.00, 'images/ram1.jpg'),
('8GB DDR4 RAM', 'RAM', 450.00, 'images/ram2.jpg'),
('16GB DDR4 RAM', 'RAM', 800.00, 'images/ram3.jpg'),
('1TB SATA HDD', 'Hard Drives', 500.00, 'images/hdd1.jpg'),
('2TB SATA HDD', 'Hard Drives', 750.00, 'images/hdd2.jpg'),
('500GB SSD', 'Hard Drives', 600.00, 'images/hdd3.jpg'),
('Capacitor Set', 'Motherboard Components', 150.00, 'images/mb1.jpg'),
('Chipset Cooler', 'Motherboard Components', 200.00, 'images/mb2.jpg'),
('VRM Module', 'Motherboard Components', 300.00, 'images/mb3.jpg');