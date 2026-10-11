-- =====================================================================
-- GROCERY STORE EXTRA SEED DATA (100 PRODUCTS)
-- Database: grocery_shop_db
-- Run AFTER your existing seed.sql. Continues the IDs it created:
--   brand    1-5  (Amul, Tata, Fortune, Nestle, Britannia)  -> new brands 6-53
--   supplier 1-3                                            -> new suppliers 4-8
--   product  1-8                                            -> new products 9-108
-- Explicit IDs are used so the script is safe to re-run
-- (ON DUPLICATE KEY UPDATE hits the primary key instead of creating copies).
-- =====================================================================

USE grocery_shop_db;

-- 1. Brands (ids 1-5 already exist; 6-53 are new)
INSERT INTO brand (brand_id, brand_name) VALUES
(1, 'Amul'),
(2, 'Tata'),
(3, 'Fortune'),
(4, 'Nestle'),
(5, 'Britannia'),
(6, 'Mother Dairy'),
(7, 'Nandini'),
(8, 'Aashirvaad'),
(9, 'India Gate'),
(10, 'Tata Sampann'),
(11, 'Madhur'),
(12, 'Saffola'),
(13, 'Patanjali'),
(14, 'Daawat'),
(15, 'Rajdhani'),
(16, 'Pillsbury'),
(17, 'Organic Tattva'),
(18, 'PepsiCo'),
(19, 'Parle'),
(20, 'Haldiram''s'),
(21, 'ITC'),
(22, 'Mondelez'),
(23, 'Cadbury'),
(24, 'Act II'),
(25, 'Ferrero'),
(26, 'Brooke Bond'),
(27, 'Bru'),
(28, 'Coca-Cola'),
(29, 'Dabur'),
(30, 'Bisleri'),
(31, 'Tropicana'),
(32, 'Horlicks'),
(33, 'Local Farm'),
(34, 'HUL'),
(35, 'Reckitt'),
(36, 'P&G'),
(37, 'Godrej'),
(38, '3M'),
(39, 'Jyothy'),
(40, 'Colgate'),
(41, 'Himalaya'),
(42, 'Marico'),
(43, 'Gillette'),
(44, 'MDH'),
(45, 'Everest'),
(46, 'Catch'),
(47, 'Badshah'),
(48, 'Kissan'),
(49, 'Sundrop'),
(50, 'Kellogg''s'),
(51, 'Veeba'),
(52, 'Keggs'),
(53, 'Harvest Gold')
ON DUPLICATE KEY UPDATE brand_name = VALUES(brand_name);

-- 2. Suppliers (ids 1-3 already exist; 4-8 are new)
INSERT INTO supplier (supplier_id, name, phone, email) VALUES
(1, 'Verma Wholesalers', '9876543210', 'verma@wholesalers.com'),
(2, 'Nagpur Fresh Agro', '9876543211', 'agro@nagpurfresh.com'),
(3, 'Metro FMCG Distributors', '9876543212', 'info@metrofmcg.com'),
(4, 'Fresh Farms', '9876543213', 'sales@freshfarms.com'),
(5, 'Metro Wholesale', '9876543214', 'orders@metrowholesale.com'),
(6, 'Sai Agro', '9876543215', 'contact@saiagro.com'),
(7, 'Shree Traders', '9876543216', 'info@shreetraders.com'),
(8, 'Pune Grocery Hub', '9876543217', 'hello@punegroceryhub.com')
ON DUPLICATE KEY UPDATE name = VALUES(name);

-- 3. Products (ids 9-108)
-- Columns: product_id, product_name, price, category, brand_id, supplier_id, stock_qty, reorder_level
INSERT INTO product (product_id, product_name, price, category, brand_id, supplier_id, stock_qty, reorder_level) VALUES
-- Dairy
(9,   'Amul Taaza Milk 1L', 56.00, 'Dairy', 1, 4, 120, 30),
(10,  'Amul Butter 100g', 58.00, 'Dairy', 1, 4, 80, 20),
(11,  'Amul Cheese Slices 200g', 140.00, 'Dairy', 1, 4, 45, 10),
(12,  'Mother Dairy Curd 400g', 40.00, 'Dairy', 6, 4, 70, 20),
(13,  'Nandini Paneer 200g', 95.00, 'Dairy', 7, 4, 35, 10),
(14,  'Amul Masti Buttermilk 200ml', 15.00, 'Dairy', 1, 4, 90, 25),
(15,  'Britannia Cheese Cube 200g', 120.00, 'Dairy', 5, 5, 30, 8),
(16,  'Mother Dairy Toned Milk 500ml', 29.00, 'Dairy', 6, 4, 100, 30),
(17,  'Amul Fresh Cream 250ml', 70.00, 'Dairy', 1, 4, 25, 8),
(18,  'Amul Ghee 500ml', 330.00, 'Dairy', 1, 5, 40, 10),
-- Staples
(19,  'Aashirvaad Atta 5kg', 265.00, 'Staples', 8, 6, 60, 15),
(20,  'Fortune Sunlite Oil 1L', 140.00, 'Staples', 3, 6, 75, 20),
(21,  'Tata Salt 1kg', 28.00, 'Staples', 2, 6, 150, 40),
(22,  'India Gate Basmati Rice 5kg', 620.00, 'Staples', 9, 6, 30, 8),
(23,  'Tata Sampann Toor Dal 1kg', 165.00, 'Staples', 10, 6, 55, 15),
(24,  'Tata Sampann Moong Dal 1kg', 140.00, 'Staples', 10, 6, 50, 15),
(25,  'Fortune Besan 500g', 62.00, 'Staples', 3, 6, 45, 12),
(26,  'Madhur Sugar 1kg', 48.00, 'Staples', 11, 7, 110, 30),
(27,  'Saffola Gold Oil 1L', 185.00, 'Staples', 12, 5, 40, 10),
(28,  'Patanjali Mustard Oil 1L', 170.00, 'Staples', 13, 7, 35, 10),
(29,  'Daawat Rozana Basmati 5kg', 480.00, 'Staples', 14, 6, 25, 8),
(30,  'Tata Sampann Chana Dal 1kg', 110.00, 'Staples', 10, 6, 50, 15),
(31,  'Rajdhani Maida 1kg', 45.00, 'Staples', 15, 7, 60, 15),
(32,  'Pillsbury Suji 500g', 35.00, 'Staples', 16, 7, 55, 15),
(33,  'Organic Tattva Jaggery 500g', 70.00, 'Staples', 17, 8, 40, 10),
-- Snacks
(34,  'Lay''s Classic Salted 52g', 20.00, 'Snacks', 18, 5, 200, 50),
(35,  'Kurkure Masala Munch 90g', 20.00, 'Snacks', 18, 5, 180, 50),
(36,  'Parle-G 250g', 25.00, 'Snacks', 19, 8, 160, 40),
(37,  'Britannia Good Day Cashew 200g', 40.00, 'Snacks', 5, 5, 90, 25),
(38,  'Haldiram''s Aloo Bhujia 200g', 55.00, 'Snacks', 20, 8, 70, 20),
(39,  'Bingo Mad Angles 66g', 20.00, 'Snacks', 21, 5, 120, 30),
(40,  'Oreo Biscuits 120g', 35.00, 'Snacks', 22, 5, 100, 25),
(41,  'Cadbury Dairy Milk Silk 60g', 85.00, 'Snacks', 23, 5, 80, 20),
(42,  'Maggi 2-Minute Noodles 280g', 56.00, 'Snacks', 4, 5, 140, 40),
(43,  'Sunfeast Dark Fantasy 75g', 40.00, 'Snacks', 21, 5, 85, 20),
(44,  'Haldiram''s Moong Dal 200g', 50.00, 'Snacks', 20, 8, 65, 20),
(45,  'Act II Popcorn 70g', 30.00, 'Snacks', 24, 8, 60, 15),
(46,  'Britannia Marie Gold 250g', 35.00, 'Snacks', 5, 5, 95, 25),
(47,  'Kinder Joy 20g', 40.00, 'Snacks', 25, 5, 75, 20),
(48,  'Parle Monaco 200g', 30.00, 'Snacks', 19, 8, 80, 20),
-- Beverages
(49,  'Tata Tea Gold 500g', 290.00, 'Beverages', 2, 7, 40, 10),
(50,  'Brooke Bond Red Label 500g', 260.00, 'Beverages', 26, 7, 45, 12),
(51,  'Nescafe Classic 50g', 175.00, 'Beverages', 4, 5, 50, 12),
(52,  'Bru Instant Coffee 50g', 150.00, 'Beverages', 27, 5, 45, 12),
(53,  'Coca-Cola 750ml', 40.00, 'Beverages', 28, 5, 130, 35),
(54,  'Pepsi 750ml', 40.00, 'Beverages', 18, 5, 125, 35),
(55,  'Real Mixed Fruit Juice 1L', 120.00, 'Beverages', 29, 5, 55, 15),
(56,  'Bisleri Water 1L', 20.00, 'Beverages', 30, 8, 250, 60),
(57,  'Tropicana Orange Juice 1L', 115.00, 'Beverages', 31, 5, 50, 12),
(58,  'Horlicks Classic Malt 500g', 270.00, 'Beverages', 32, 5, 35, 10),
(59,  'Bournvita 500g', 245.00, 'Beverages', 23, 5, 40, 10),
(60,  'Sprite 750ml', 40.00, 'Beverages', 28, 5, 120, 35),
-- Fruits & Vegetables
(61,  'Onion 1kg', 35.00, 'Fruits & Vegetables', 33, 4, 200, 50),
(62,  'Potato 1kg', 30.00, 'Fruits & Vegetables', 33, 4, 220, 50),
(63,  'Tomato 1kg', 40.00, 'Fruits & Vegetables', 33, 4, 150, 40),
(64,  'Banana (1 dozen)', 60.00, 'Fruits & Vegetables', 33, 4, 80, 20),
(65,  'Apple Shimla 1kg', 160.00, 'Fruits & Vegetables', 33, 4, 60, 15),
(66,  'Carrot 500g', 30.00, 'Fruits & Vegetables', 33, 4, 70, 20),
(67,  'Green Capsicum 500g', 45.00, 'Fruits & Vegetables', 33, 4, 50, 15),
(68,  'Coriander Bunch', 20.00, 'Fruits & Vegetables', 33, 4, 60, 20),
(69,  'Lemon 250g', 25.00, 'Fruits & Vegetables', 33, 4, 70, 20),
(70,  'Cucumber 500g', 25.00, 'Fruits & Vegetables', 33, 4, 65, 20),
-- Household
(71,  'Surf Excel Matic 1kg', 230.00, 'Household', 34, 5, 45, 12),
(72,  'Vim Dishwash Gel 500ml', 105.00, 'Household', 34, 5, 60, 15),
(73,  'Harpic Toilet Cleaner 500ml', 95.00, 'Household', 35, 5, 55, 15),
(74,  'Lizol Floor Cleaner 975ml', 215.00, 'Household', 35, 5, 40, 10),
(75,  'Colin Glass Cleaner 500ml', 100.00, 'Household', 35, 5, 35, 10),
(76,  'Ariel Detergent 1kg', 245.00, 'Household', 36, 5, 40, 10),
(77,  'Rin Detergent Bar 250g', 10.00, 'Household', 34, 8, 150, 40),
(78,  'Good Knight Refill 45ml', 80.00, 'Household', 37, 8, 50, 15),
(79,  'Scotch-Brite Scrub Pad (3 pcs)', 50.00, 'Household', 38, 8, 70, 20),
(80,  'Exo Dishwash Bar 500g', 40.00, 'Household', 39, 8, 80, 20),
-- Personal Care
(81,  'Dettol Soap 125g', 45.00, 'Personal Care', 35, 5, 100, 25),
(82,  'Lux Soap 100g', 40.00, 'Personal Care', 34, 5, 110, 30),
(83,  'Colgate Strong Teeth 200g', 110.00, 'Personal Care', 40, 5, 80, 20),
(84,  'Clinic Plus Shampoo 340ml', 190.00, 'Personal Care', 34, 5, 45, 12),
(85,  'Dove Shampoo 340ml', 330.00, 'Personal Care', 34, 5, 30, 8),
(86,  'Pears Soap 125g', 70.00, 'Personal Care', 34, 5, 65, 18),
(87,  'Himalaya Face Wash 100ml', 150.00, 'Personal Care', 41, 8, 40, 10),
(88,  'Parachute Coconut Oil 500ml', 215.00, 'Personal Care', 42, 8, 50, 12),
(89,  'Head & Shoulders 340ml', 330.00, 'Personal Care', 36, 5, 30, 8),
(90,  'Gillette Guard Razor', 35.00, 'Personal Care', 43, 8, 90, 25),
(91,  'Whisper Choice (20 pads)', 60.00, 'Personal Care', 36, 5, 60, 15),
(92,  'Vaseline Body Lotion 400ml', 280.00, 'Personal Care', 34, 5, 30, 8),
(93,  'Pepsodent Toothbrush', 30.00, 'Personal Care', 34, 8, 100, 25),
-- Spices
(94,  'MDH Garam Masala 100g', 85.00, 'Spices', 44, 7, 60, 15),
(95,  'Everest Turmeric Powder 200g', 70.00, 'Spices', 45, 7, 70, 18),
(96,  'Everest Red Chilli Powder 200g', 90.00, 'Spices', 45, 7, 65, 18),
(97,  'Catch Cumin Seeds 100g', 65.00, 'Spices', 46, 7, 55, 15),
(98,  'Badshah Pav Bhaji Masala 100g', 70.00, 'Spices', 47, 7, 50, 12),
-- Packaged Food / Dry Fruits
(99,  'Kissan Tomato Ketchup 950g', 135.00, 'Packaged Food', 48, 5, 60, 15),
(100, 'Kissan Mixed Fruit Jam 500g', 160.00, 'Packaged Food', 48, 5, 40, 10),
(101, 'Sundrop Peanut Butter 340g', 180.00, 'Packaged Food', 49, 8, 35, 10),
(102, 'Tata Sampann Almonds 200g', 230.00, 'Dry Fruits', 10, 6, 30, 8),
(103, 'Quaker Oats 1kg', 190.00, 'Packaged Food', 18, 5, 45, 12),
(104, 'Kellogg''s Corn Flakes 475g', 195.00, 'Packaged Food', 50, 5, 40, 10),
(105, 'Veeba Mayonnaise 250g', 95.00, 'Packaged Food', 51, 8, 45, 12),
-- Eggs & Bakery
(106, 'Eggs (Pack of 12)', 90.00, 'Dairy & Eggs', 52, 4, 100, 30),
(107, 'Britannia Bread 400g', 45.00, 'Bakery', 5, 4, 70, 25),
(108, 'Harvest Gold Pav (6 pcs)', 30.00, 'Bakery', 53, 4, 60, 20)
ON DUPLICATE KEY UPDATE product_name = VALUES(product_name);

-- 4. Verify
SELECT COUNT(*) AS total_brands    FROM brand;      -- expect 53
SELECT COUNT(*) AS total_suppliers FROM supplier;   -- expect 8
SELECT COUNT(*) AS total_products  FROM product;    -- expect 108