-- Run with: python run_sql.py, then paste a query at the SQL> prompt.
-- Currency is stored as integer paise to avoid floating point rounding.

-- 1. Browse available products and categories
SELECT id, name, category, price_paise / 100.0 AS price_rupees, stock_quantity
FROM product_catalogue ORDER BY category, name;

-- 2. Search for a product by name
SELECT id, name, price_paise / 100.0 AS price_rupees, stock_quantity
FROM product_catalogue WHERE name LIKE '%headphone%';

-- 3. Show each order with its customer
SELECT o.id AS order_id, p.full_name AS customer, o.status,
       o.total_paise / 100.0 AS total_rupees, o.created_at
FROM orders o JOIN profiles p ON p.id = o.customer_id
ORDER BY o.created_at DESC;

-- 4. Show order line items (multi-table join)
SELECT o.id AS order_id, pr.name AS product, oi.quantity,
       oi.unit_price_paise / 100.0 AS unit_price_rupees,
       oi.quantity * oi.unit_price_paise / 100.0 AS line_total_rupees
FROM orders o JOIN order_items oi ON oi.order_id = o.id
JOIN products pr ON pr.id = oi.product_id ORDER BY o.id;

-- 5. Calculate sales by category
SELECT c.name AS category, SUM(oi.quantity * oi.unit_price_paise) / 100.0 AS sales_rupees
FROM order_items oi JOIN products pr ON pr.id = oi.product_id
JOIN categories c ON c.id = pr.category_id
JOIN orders o ON o.id = oi.order_id WHERE o.status <> 'cancelled'
GROUP BY c.name ORDER BY sales_rupees DESC;

-- 6. Low-stock report
SELECT name, stock_quantity FROM products WHERE is_active = 1 AND stock_quantity < 10
ORDER BY stock_quantity;

-- 7. Demonstrate update (inventory staff should use the UI for access checks)
-- UPDATE products SET stock_quantity = stock_quantity + 5 WHERE id = 1;

-- 8. Demonstrate delete on a disposable category only
-- DELETE FROM categories WHERE id = 999;
