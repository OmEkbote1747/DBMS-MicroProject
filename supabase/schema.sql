-- Educational Amazon-style storefront schema for Supabase PostgreSQL.
-- Run in the Supabase SQL Editor. All prices are integer paise.
-- Create Auth users separately; profile role defaults to customer.

create type public.app_role as enum ('customer', 'inventory', 'analyst', 'admin');
create type public.order_status as enum ('placed', 'packed', 'shipped', 'delivered', 'cancelled');

create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text not null default '',
  role public.app_role not null default 'customer',
  created_at timestamptz not null default now()
);

create table public.categories (
  id bigint generated always as identity primary key,
  name text not null unique,
  description text
);

create table public.products (
  id bigint generated always as identity primary key,
  category_id bigint not null references public.categories(id),
  name text not null,
  description text not null default '',
  price_paise integer not null check (price_paise >= 0),
  stock_quantity integer not null default 0 check (stock_quantity >= 0),
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create table public.orders (
  id bigint generated always as identity primary key,
  customer_id uuid not null references public.profiles(id),
  status public.order_status not null default 'placed',
  total_paise bigint not null check (total_paise >= 0),
  created_at timestamptz not null default now()
);

create table public.order_items (
  id bigint generated always as identity primary key,
  order_id bigint not null references public.orders(id) on delete cascade,
  product_id bigint not null references public.products(id),
  quantity integer not null check (quantity > 0),
  unit_price_paise integer not null check (unit_price_paise >= 0),
  unique (order_id, product_id)
);

create index products_category_idx on public.products(category_id);
create index orders_customer_created_idx on public.orders(customer_id, created_at desc);
create index order_items_order_idx on public.order_items(order_id);

create or replace function public.has_staff_role()
returns boolean language sql stable security definer
set search_path = '' as $$
  select exists (
    select 1 from public.profiles p
    where p.id = (select auth.uid()) and p.role in ('inventory', 'admin')
  );
$$;

create or replace function public.is_admin()
returns boolean language sql stable security definer
set search_path = '' as $$
  select exists (
    select 1 from public.profiles p
    where p.id = (select auth.uid()) and p.role = 'admin'
  );
$$;

create or replace function public.is_analyst()
returns boolean language sql stable security definer
set search_path = '' as $$
  select exists (
    select 1 from public.profiles p
    where p.id = (select auth.uid()) and p.role = 'analyst'
  );
$$;

alter table public.profiles enable row level security;
alter table public.categories enable row level security;
alter table public.products enable row level security;
alter table public.orders enable row level security;
alter table public.order_items enable row level security;

-- Public catalogue reads. Writes require inventory or admin role.
create policy "active catalogue is readable" on public.products
for select to anon, authenticated using (is_active or public.has_staff_role() or public.is_analyst());
create policy "categories readable" on public.categories
for select to anon, authenticated using (true);

-- Users may read their own profile. Only an administrator may assign roles.
create policy "users read own profile" on public.profiles
for select to authenticated using (id = (select auth.uid()) or public.is_admin());
create policy "admin manages profiles" on public.profiles
for all to authenticated using (public.is_admin()) with check (public.is_admin());

-- Customers can only read their own orders. Staff can read all orders.
create policy "customer or staff reads orders" on public.orders
for select to authenticated using (customer_id = (select auth.uid()) or public.has_staff_role() or public.is_analyst());
create policy "customer creates own order" on public.orders
for insert to authenticated with check (customer_id = (select auth.uid()));
create policy "staff updates orders" on public.orders
for update to authenticated using (public.has_staff_role()) with check (public.has_staff_role());

create policy "customer or staff reads order items" on public.order_items
for select to authenticated using (
  public.has_staff_role() or public.is_analyst() or exists (
    select 1 from public.orders o where o.id = order_id and o.customer_id = (select auth.uid())
  )
);
create policy "customer inserts own order items" on public.order_items
for insert to authenticated with check (
  exists (select 1 from public.orders o where o.id = order_id and o.customer_id = (select auth.uid()))
);
create policy "staff manages order items" on public.order_items
for all to authenticated using (public.has_staff_role()) with check (public.has_staff_role());

grant select on public.products, public.categories to anon, authenticated;
grant select, insert, update on public.profiles to authenticated;
grant select, update on public.orders to authenticated;
grant select on public.order_items to authenticated;

revoke insert, update, delete on public.products, public.categories from anon, authenticated;
revoke insert, update, delete on public.order_items from anon, authenticated;
revoke insert on public.orders from anon, authenticated;

-- Inventory staff can change stock only. Product creation is administrator-only.
create or replace function public.update_stock(p_product_id bigint, p_stock_quantity integer)
returns void language plpgsql security definer
set search_path = '' as $$
begin
  if not public.has_staff_role() then raise exception 'Staff permission required'; end if;
  if p_stock_quantity < 0 then raise exception 'Stock cannot be negative'; end if;
  update public.products set stock_quantity = p_stock_quantity where id = p_product_id;
  if not found then raise exception 'Product not found'; end if;
end;
$$;

create or replace function public.admin_add_product(
  p_name text, p_category text, p_description text,
  p_price_paise integer, p_stock_quantity integer
)
returns bigint language plpgsql security definer
set search_path = '' as $$
declare v_category_id bigint; v_product_id bigint;
begin
  if not public.is_admin() then raise exception 'Administrator permission required'; end if;
  if length(trim(p_name)) = 0 or length(trim(p_category)) = 0
     or p_price_paise < 0 or p_stock_quantity < 0 then
    raise exception 'Invalid product details';
  end if;
  insert into public.categories(name) values (trim(p_category))
    on conflict (name) do nothing;
  select id into v_category_id from public.categories where name = trim(p_category);
  insert into public.products(category_id, name, description, price_paise, stock_quantity)
    values (v_category_id, trim(p_name), coalesce(p_description,''), p_price_paise, p_stock_quantity)
    returning id into v_product_id;
  return v_product_id;
end;
$$;

revoke all on function public.update_stock(bigint, integer) from public, anon;
revoke all on function public.admin_add_product(text, text, text, integer, integer) from public, anon;
grant execute on function public.update_stock(bigint, integer) to authenticated;
grant execute on function public.admin_add_product(text, text, text, integer, integer) to authenticated;

-- Customers create orders only through this transaction, so the database
-- derives prices from products and checks stock rather than trusting the browser.
create or replace function public.place_order(p_items jsonb)
returns bigint language plpgsql security definer
set search_path = '' as $$
declare
  v_order_id bigint;
  v_total bigint := 0;
  v_item record;
  v_product public.products%rowtype;
begin
  if (select auth.uid()) is null then
    raise exception 'Sign in before placing an order';
  end if;
  if not exists (select 1 from public.profiles p
      where p.id = (select auth.uid()) and p.role = 'customer') then
    raise exception 'Customer account required';
  end if;
  if p_items is null or jsonb_typeof(p_items) is distinct from 'array'
     or jsonb_array_length(p_items) = 0 then
    raise exception 'An order must contain at least one item';
  end if;

  for v_item in
    select (value->>'product_id')::bigint as product_id,
           sum((value->>'quantity')::integer)::integer as quantity
    from jsonb_array_elements(p_items) group by (value->>'product_id')::bigint
  loop
    if v_item.quantity < 1 then raise exception 'Quantity must be positive'; end if;
    select * into v_product from public.products p
      where p.id = v_item.product_id and p.is_active for update;
    if not found then raise exception 'Product is unavailable'; end if;
    if v_product.stock_quantity < v_item.quantity then
      raise exception 'Insufficient stock for product %', v_product.id;
    end if;
    update public.products set stock_quantity = stock_quantity - v_item.quantity
      where id = v_product.id;
    v_total := v_total + (v_product.price_paise::bigint * v_item.quantity);
  end loop;

  insert into public.orders(customer_id, status, total_paise)
    values ((select auth.uid()), 'placed', v_total) returning id into v_order_id;

  for v_item in
    select (value->>'product_id')::bigint as product_id,
           sum((value->>'quantity')::integer)::integer as quantity
    from jsonb_array_elements(p_items) group by (value->>'product_id')::bigint
  loop
    select * into v_product from public.products p where p.id = v_item.product_id;
    insert into public.order_items(order_id, product_id, quantity, unit_price_paise)
      values (v_order_id, v_product.id, v_item.quantity, v_product.price_paise);
  end loop;
  return v_order_id;
end;
$$;

revoke all on function public.place_order(jsonb) from public, anon;
grant execute on function public.place_order(jsonb) to authenticated;

-- Seed catalogue entries after creating these categories in the SQL Editor.
insert into public.categories (name, description) values
  ('Electronics', 'Everyday electronic devices'),
  ('Home', 'Useful products for the home'),
  ('Books', 'Reading and learning')
on conflict (name) do nothing;

insert into public.products (category_id, name, description, price_paise, stock_quantity)
select c.id, x.name, x.description, x.price_paise, x.stock_quantity
from (values
  ('Electronics', 'Wireless Headphones', 'Bluetooth over-ear headphones', 249900, 18),
  ('Electronics', 'USB-C Charger', 'Fast charging wall adapter', 89900, 42),
  ('Home', 'Insulated Bottle', '750 ml stainless steel bottle', 69900, 25),
  ('Books', 'Database Systems Basics', 'Introductory textbook for database learners', 59900, 12),
  ('Home', 'Desk Lamp', 'Adjustable LED study lamp', 129900, 8)
) as x(category, name, description, price_paise, stock_quantity)
join public.categories c on c.name = x.category
where not exists (select 1 from public.products p where p.name = x.name);
