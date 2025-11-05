# Immer Miau — Player Roster System

This project provides two linked Streamlit apps backed by a Supabase database.

1. **Public Form** — anyone can submit their player data.
2. **Private Dashboard** — trusted editors can view, edit, and export all entries.

---

## 🧩 Fields Collected
- Player Name  
- Current Alliance (free text)  
- Total Hero Power  
- Combat Power 1st Squad  
- Expected Transfer Seat Color (White, Blue, Pink)

---

## 🌐 Setup Overview

### 1. Supabase
Create a Supabase project and run this SQL in the SQL Editor:

```sql
create table if not exists players (
  player_name text primary key,
  current_alliance text,
  total_hero_power numeric,
  combat_power_1st_squad numeric,
  expected_transfer_seat_color text,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  submitted_ip text
);

alter table players enable row level security;

create policy "public_can_insert"
on players for insert
to anon
with check (true);

create policy "anon_cannot_select"
on players for select
to anon
using (false);

create policy "anon_cannot_update"
on players for update
to anon
using (false)
with check (false);

create policy "anon_cannot_delete"
on players for delete
to anon
using (false);
