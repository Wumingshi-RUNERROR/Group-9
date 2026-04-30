# Group-9 Last Resort Admin

Flask + Jinja implementation based on `Group9_milestone2_create.sql` and `Group9_LastResort_PageSpec.md`.

## Stack

- Backend: Python Flask
- Frontend: Jinja templates + CSS
- Database: SQLite (`last_resort.db`)

## Pages Implemented (P0)

- Dashboard (`/dashboard`)
- Inventory (`/inventory`)
- Party Management (`/parties`)
- Reservation Management (`/reservations`)
- Assignment & Stay (`/assignments`)
- Event Management (`/events`)
- Billing & Charges (`/billing`)
- Maintenance Tickets (`/maintenance`)

## Quick Start

1. Install dependencies:
   - `python3 -m venv .venv`
   - `source .venv/bin/activate`
   - `pip install -r requirements.txt`
2. Run app:
   - `python app.py`
3. Open:
   - `http://127.0.0.1:5000`

On first run, the app creates `last_resort.db` from:
- `Group9_milestone2_create.sql`
- `Group9_milestone2_insert.sql`
