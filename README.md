# Agendame - Appointment Booking

Free appointment booking module for Odoo 16, 17, 18 and 19. Adds a public
booking page to your website where visitors pick an appointment type and an
available time slot; Odoo creates the calendar event for you.

Works with **Odoo Community Edition** — no Enterprise Appointments module
required.

## Branches

| Branch | Odoo series | Notes |
|--------|-------------|-------|
| `main` | 19.0 | Default branch, identical to `19.0` |
| `19.0` | 19.0 | Version continuity with internal history (19.0.2.3.0) |
| `18.0` | 18.0 | First public port (18.0.1.0.0) |
| `17.0` | 17.0 | First public port (17.0.1.0.0) |
| `16.0` | 16.0 | First public port (16.0.1.0.0) |

Version branches live in parallel and are **never merged into each other** —
each one carries the view syntax of its Odoo series.

## Installation

1. Clone this repository (or download the branch matching your Odoo version)
   into a directory listed in your `addons_path`:

   ```bash
   git clone -b 19.0 https://github.com/vigbe/agendame_calendary.git
   ```

2. Restart Odoo and update the Apps list.
3. Install **Agendame - Appointment Booking** (technical name:
   `agendame`).

Dependencies: `crm`, `calendar`, `website`, `mail`.

## Usage

1. Go to **Calendar → Appointments → Appointment Types** and configure
   duration, timezone, staff users and weekday availability.
2. Share the public booking URL (`/agendame`) with your customers.
3. Visitors fill in their details and pick a free slot; availability adapts
   to each staff member's real calendar.

Full (Spanish) module documentation: [`agendame/README.md`](agendame/README.md).

## License

LGPL-3. Author: Victor Bastías Escobar —
[vicbas.com](https://vicbas.com) — <contacto@vicbas.com>
