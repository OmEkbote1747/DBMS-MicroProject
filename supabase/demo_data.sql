-- Extra fictional catalogue and order history for a fuller classroom demo.
-- Safe to run more than once: products are matched by name, and demo orders
-- use fixed timestamps to avoid duplicate inserts. Create a customer Auth user
-- and matching public.profiles row before running this file if you want orders.

insert into public.categories (name, description) values
  ('Computers', 'Laptops, storage, and computer accessories'),
  ('Kitchen & Dining', 'Cookware and everyday kitchen equipment'),
  ('Sports & Outdoors', 'Fitness, travel, and outdoor equipment'),
  ('Beauty & Personal Care', 'Personal care and grooming products'),
  ('Toys & Games', 'Toys, games, and creative activities'),
  ('Office Supplies', 'Study and office essentials'),
  ('Fashion', 'Clothing, bags, and accessories'),
  ('Grocery', 'Packaged pantry and beverage items')
on conflict (name) do nothing;

insert into public.products (category_id, name, description, price_paise, stock_quantity)
select c.id, x.name, x.description, x.price_paise, x.stock_quantity
from (values
  ('Electronics', 'Bluetooth Speaker', 'Portable speaker with wireless audio', 179900, 21),
  ('Electronics', 'Wireless Mouse', 'Ergonomic wireless mouse with USB receiver', 79900, 37),
  ('Electronics', 'Mechanical Keyboard', 'Compact keyboard with tactile switches', 329900, 14),
  ('Electronics', '1080p Webcam', 'USB webcam for calls and classes', 219900, 11),
  ('Electronics', 'Noise Cancelling Earbuds', 'True wireless earbuds with charging case', 399900, 16),
  ('Computers', 'Everyday Laptop 14', '14 inch laptop for study and office work', 5499900, 7),
  ('Computers', 'Portable SSD 1TB', 'External solid state drive with USB-C', 699900, 13),
  ('Computers', 'USB-C Hub 7-in-1', 'Multiport hub with HDMI and card reader', 249900, 19),
  ('Computers', 'Laptop Stand', 'Foldable aluminium stand for laptops', 159900, 23),
  ('Computers', '27-inch Monitor', 'Full HD IPS monitor for desk setups', 1199900, 6),
  ('Home', 'Cotton Bedsheet Set', 'Double bed sheet with two pillow covers', 139900, 20),
  ('Home', 'Memory Foam Pillow', 'Supportive pillow with washable cover', 99900, 17),
  ('Home', 'Storage Basket Set', 'Set of three woven household baskets', 84900, 29),
  ('Home', 'LED Bulb 9W Pack', 'Pack of four energy-saving LED bulbs', 49900, 56),
  ('Home', 'Wall Clock', 'Silent sweep clock for home or office', 74900, 15),
  ('Kitchen & Dining', 'Nonstick Frying Pan', '26 cm everyday frying pan', 119900, 18),
  ('Kitchen & Dining', 'Electric Kettle 1.5L', 'Stainless steel kettle with auto shut-off', 169900, 12),
  ('Kitchen & Dining', 'Glass Food Container Set', 'Set of five stackable storage containers', 109900, 24),
  ('Kitchen & Dining', 'Digital Kitchen Scale', 'Compact scale for cooking and baking', 89900, 9),
  ('Kitchen & Dining', 'Ceramic Dinner Set', 'Six-piece dinner set for everyday meals', 199900, 8),
  ('Books', 'The Art of Clear Thinking', 'Practical guide to reasoning and decisions', 39900, 31),
  ('Books', 'Python for Beginners', 'Introductory programming workbook', 54900, 22),
  ('Books', 'The World Atlas', 'Illustrated reference atlas for students', 79900, 10),
  ('Books', 'Classic Short Stories', 'Collection of public-domain short fiction', 29900, 28),
  ('Books', 'Project Planning Handbook', 'A practical guide to planning small projects', 45900, 14),
  ('Sports & Outdoors', 'Yoga Mat 6mm', 'Non-slip exercise mat with carry strap', 89900, 26),
  ('Sports & Outdoors', 'Resistance Band Set', 'Five bands for home strength training', 69900, 32),
  ('Sports & Outdoors', 'Trekking Backpack 30L', 'Day pack with padded straps and rain cover', 189900, 11),
  ('Sports & Outdoors', 'Stainless Steel Shaker', 'Leak-resistant bottle for fitness drinks', 59900, 18),
  ('Sports & Outdoors', 'LED Camping Lantern', 'Rechargeable lantern with adjustable brightness', 129900, 7),
  ('Beauty & Personal Care', 'Ceramic Hair Dryer', 'Compact hair dryer with two heat settings', 149900, 13),
  ('Beauty & Personal Care', 'Electric Toothbrush', 'Rechargeable brush with two cleaning modes', 179900, 10),
  ('Beauty & Personal Care', 'Daily Moisturiser 200ml', 'Lightweight, fragrance-free skin moisturiser', 34900, 34),
  ('Beauty & Personal Care', 'Beard Grooming Kit', 'Trimmer and comb set for home grooming', 99900, 8),
  ('Toys & Games', 'Wooden Building Blocks', 'Colourful block set for creative play', 79900, 16),
  ('Toys & Games', 'Family Puzzle 1000 Pieces', 'Landscape jigsaw puzzle for family game time', 49900, 20),
  ('Toys & Games', 'Strategy Board Game', 'Turn-based strategy game for two to four players', 129900, 5),
  ('Office Supplies', 'A5 Notebook 3-Pack', 'Ruled notebooks for class and daily notes', 24900, 60),
  ('Office Supplies', 'Gel Pen Set', 'Pack of ten black ink gel pens', 19900, 72),
  ('Office Supplies', 'Desk Organiser', 'Multi-compartment organiser for stationery', 69900, 17),
  ('Office Supplies', 'Whiteboard 60x90cm', 'Wall-mounted board with marker and eraser', 159900, 4),
  ('Fashion', 'Canvas Backpack', 'Lightweight backpack with laptop sleeve', 119900, 15),
  ('Fashion', 'Everyday Cotton T-Shirt', 'Regular fit cotton T-shirt in navy', 49900, 33),
  ('Fashion', 'Travel Wallet', 'Compact wallet with passport and card slots', 79900, 12),
  ('Grocery', 'Arabica Coffee 250g', 'Medium roast ground coffee for filter brewing', 32900, 25),
  ('Grocery', 'Green Tea 100 Bags', 'Everyday green tea bags in a resealable pack', 27900, 40),
  ('Grocery', 'Mixed Nuts 500g', 'Roasted mixed nuts in a resealable pouch', 49900, 18)
) as x(category, name, description, price_paise, stock_quantity)
join public.categories c on c.name = x.category
where not exists (select 1 from public.products p where p.name = x.name);

-- Add eight historical orders for the first customer profile, if one exists.
-- Historical sample orders do not change current stock balances.
do $$
declare
  v_customer uuid;
  v_i integer;
  v_created timestamptz;
  v_name1 text;
  v_name2 text;
  v_id1 bigint;
  v_id2 bigint;
  v_price1 integer;
  v_price2 integer;
  v_qty1 integer;
  v_order_id bigint;
begin
  select id into v_customer from public.profiles
    where role = 'customer' order by created_at, id limit 1;
  if v_customer is null then
    raise notice 'Catalogue seeded. Create a customer Auth user and profile, then rerun this file to add sample orders.';
    return;
  end if;

  for v_i in 1..8 loop
    v_created := timestamptz '2026-09-02 12:00:00+05:30' + ((v_i - 1) * interval '3 days');
    if exists (select 1 from public.orders where customer_id = v_customer and created_at = v_created) then
      continue;
    end if;

    v_name1 := case v_i
      when 1 then 'Wireless Headphones' when 2 then 'Portable SSD 1TB'
      when 3 then 'Electric Kettle 1.5L' when 4 then 'A5 Notebook 3-Pack'
      when 5 then 'Yoga Mat 6mm' when 6 then 'Canvas Backpack'
      when 7 then 'Database Systems Basics' else 'Bluetooth Speaker' end;
    v_name2 := case v_i
      when 1 then 'USB-C Charger' when 2 then 'USB-C Hub 7-in-1'
      when 3 then 'Glass Food Container Set' when 4 then 'Gel Pen Set'
      when 5 then 'Resistance Band Set' when 6 then 'Everyday Cotton T-Shirt'
      when 7 then 'Python for Beginners' else 'Noise Cancelling Earbuds' end;
    v_qty1 := case when v_i in (3, 6) then 2 else 1 end;
    select id, price_paise into v_id1, v_price1 from public.products where name = v_name1 limit 1;
    select id, price_paise into v_id2, v_price2 from public.products where name = v_name2 limit 1;
    if v_id1 is null or v_id2 is null then continue; end if;

    insert into public.orders(customer_id, status, total_paise, created_at)
    values (v_customer,
      case v_i % 4 when 0 then 'delivered'::public.order_status
                   when 1 then 'delivered'::public.order_status
                   when 2 then 'shipped'::public.order_status
                   else 'packed'::public.order_status end,
      (v_price1::bigint * v_qty1) + v_price2, v_created)
    returning id into v_order_id;
    insert into public.order_items(order_id, product_id, quantity, unit_price_paise)
      values (v_order_id, v_id1, v_qty1, v_price1), (v_order_id, v_id2, 1, v_price2);
  end loop;
end;
$$;
