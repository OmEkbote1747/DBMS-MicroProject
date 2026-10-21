# Amazon Style Store DBMS Micro Project

This classroom project has two demonstrations:

- **Local SQLite app:** ready to run without cloud credentials. Its role checks are in the Python application server. SQLite does not provide per-user RLS.
- **Supabase app:** connects to your hosted PostgreSQL project. PostgreSQL RLS policies and database functions enforce access. This is the version to use when demonstrating database-enforced roles.

The data is fictional. The project is not Amazon software and does not process real payments.

## Requirements

- Python 3.10 or newer
- A modern browser
- Internet access and your own Supabase project for the cloud demonstration
- No third-party Python packages for the local server

## Start the project

1. Extract the ZIP.
2. Open a terminal in the `Amazon_DBMS_Project` folder.
3. Double-click `Start_Amazon_DBMS_Project.bat` (or run `python app.py` in PowerShell).
4. The launcher opens `http://127.0.0.1:8000` in your browser and leaves a server window open. Keep that window open while using the app. If the port cannot be opened, the server window will show the reason.

The local database file `amazon_store.db` is created and seeded on first run. Delete it while the server is stopped to reset the local demo.

## Local demo accounts

| Role | Email | Password |
|---|---|---|
| Customer | `maya@example.test` | `customer123` |
| Inventory staff | `ivan@example.test` | `stock123` |
| Analyst | `sam@example.test` | `analytics123` |
| Administrator | `admin@example.test` | `admin123` |

These accounts apply only to the local SQLite version. They are not Supabase Auth accounts.

## Demonstrate the local SQLite app

1. As customer, browse/search, add a product to cart, place an order, and show order history and reduced stock.
2. As inventory staff, change a stock quantity.
3. As analyst, view orders and run read-only queries with `python run_sql.py`; use queries from `sql/queries.sql`.
4. As administrator, add a product.

Here the Python server performs role checks before database operations. This is a useful local prototype, but not database-enforced per-user authorization.

## Set up and use the Supabase version

1. Create a Supabase project. Keep **Enable Data API** on; leave **Automatically expose new tables** and **Enable automatic RLS** off for this project. The supplied schema configures grants and RLS itself.
2. In the Supabase Dashboard, open **SQL Editor → New query**. Copy all of `supabase/schema.sql` into the editor and run it once in the new project.
3. Under **Authentication → Users**, create a user for each role you will demonstrate. Copy each user’s UID.
4. For every Auth user, add the matching profile and role in SQL Editor. Example (replace the UUID):

   ```sql
   insert into public.profiles (id, full_name, role)
   values ('AUTH-USER-UUID', 'Maya Customer', 'customer');
   ```

   Valid roles are `customer`, `inventory`, `analyst`, and `admin`. The Auth user must exist first.
5. Run `supabase/demo_data.sql` in SQL Editor to add 47 more products and eight historical sample orders for the first customer profile. This seed is safe to rerun. If you run it before creating a customer profile, it adds the products; run it again after creating the profile to add orders.
6. In the local app, open **Supabase version (database-enforced roles)** or go directly to `http://127.0.0.1:8000/static/cloud.html`.
7. Enter the **Project URL** and **publishable key** from the Supabase Dashboard. The page saves these browser-side values in local storage. Sign in with one of the Supabase Auth accounts.
8. Demonstrate customer checkout, inventory stock adjustment, analyst order reading, and admin product creation. For the customer, inventory, or analyst account, click **Attempt an action outside my role** and show the rejection returned by PostgreSQL. The page calls Supabase Auth/Data API and the database functions `place_order`, `update_stock`, and `admin_add_product`. PostgreSQL RLS and function checks determine which rows/actions the signed-in user can access.

The Supabase SQL Editor runs with administrator privileges, so it is for schema/data inspection and setup—not for proving what a customer can access. To demonstrate roles, sign into the Supabase page as each Auth user. Supabase explains that database grants and RLS policies work together to control access: https://supabase.com/docs/guides/database/postgres/row-level-security.

**Never enter the database password, a secret key, or a service-role key into the browser page.** The publishable key is intended for client use when RLS is configured. Do not share credentials in screenshots or chat.

## Technologies

- Local version: Python standard library HTTP server, SQLite, HTML, CSS, JavaScript.
- Supabase version: Supabase Auth, PostgreSQL, Data API, Row Level Security, and database functions. Its frontend uses the Supabase JavaScript client from a CDN. The local Python process only serves the static page; it does not authorize Supabase operations.

## Project contents

- `app.py` — local server, SQLite initialization, local API and Python role checks
- `static/index.html`, `static/app.js`, `static/styles.css` — local storefront
- `static/cloud.html`, `static/cloud.js` — Supabase-connected frontend with database-enforced access
- `sql/schema.sql` — SQLite schema
- `sql/queries.sql` — sample SQL queries
- `supabase/schema.sql` — PostgreSQL schema, RLS policies, and role-checked functions
- `supabase/demo_data.sql` — additional categories, products, and sample order history
- `run_sql.py` — read-only SQL prompt for the local SQLite database
- `report.docx` — project report
- `images/supabase_schema_overview.png`, `images/amazon_dbms_er_diagram.png` — report figures generated from the deployed Supabase schema

