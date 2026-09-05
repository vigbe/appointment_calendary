import datetime

import pytz
from odoo import http
from odoo.http import request


class AppointmentController(http.Controller):
    @http.route("/agendame", type="http", auth="public", website=True)
    def appointment_index(self, **kwargs):
        domain = [("active", "=", True)]
        # Authenticated internal users see only their own agendas
        # (Odoo record rules enforce this). Public visitors see all.
        if request.env.user.has_group("base.group_user"):
            appointment_types = request.env["agendame.type"].search(domain)
        else:
            appointment_types = request.env["agendame.type"].sudo().search(domain)
        return request.render(
            "agendame.appointments_list",
            {
                "appointment_types": appointment_types,
            },
        )

    @http.route(
        "/agendame/<int:agendame_type_id>",
        type="http",
        auth="public",
        website=True,
    )
    def appointment_page(self, agendame_type_id, **kwargs):
        if request.env.user.has_group("base.group_user"):
            appointment_type = request.env["agendame.type"].browse(agendame_type_id)
        else:
            appointment_type = (
                request.env["agendame.type"].sudo().browse(agendame_type_id)
            )
        if not appointment_type.exists():
            return request.not_found()

        slots = appointment_type._get_appointment_slots()
        # Group by date for the template
        grouped_slots = {}
        appt_tz = pytz.timezone(appointment_type.appointment_tz or "UTC")

        for slot in slots:
            # Localize UTC slot back to appointment timezone for display
            slot_localized = pytz.utc.localize(slot).astimezone(appt_tz)
            date_key = slot_localized.strftime("%Y-%m-%d")
            if date_key not in grouped_slots:
                grouped_slots[date_key] = []
            grouped_slots[date_key].append(slot_localized)

        # Paises activos en Odoo, priorizando el pais de la compania
        default_country = (
            request.env.company.country_id
            or request.env["res.country"].sudo().search([], limit=1)
        )
        countries = request.env["res.country"].sudo().search([])
        countries = sorted(
            countries,
            key=lambda c: (0 if c.id == default_country.id else 1, c.name),
        )

        return request.render(
            "agendame.appointment_details",
            {
                "appointment_type": appointment_type,
                "grouped_slots": grouped_slots,
                "countries": countries,
                "default_country": default_country,
                "days_es": {
                    "Mon": "Lun",
                    "Tue": "Mar",
                    "Wed": "Mié",
                    "Thu": "Jue",
                    "Fri": "Vie",
                    "Sat": "Sáb",
                    "Sun": "Dom",
                },
                "months_es": {
                    "January": "Enero",
                    "February": "Febrero",
                    "March": "Marzo",
                    "April": "Abril",
                    "May": "Mayo",
                    "June": "Junio",
                    "July": "Julio",
                    "August": "Agosto",
                    "September": "Septiembre",
                    "October": "Octubre",
                    "November": "Noviembre",
                    "December": "Diciembre",
                },
            },
        )

    @http.route(
        "/agendame/submit",
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def appointment_submit(self, **post):
        agendame_type_id = int(post.get("agendame_type_id"))
        name = post.get("name")
        email = post.get("email")
        phone = post.get("phone")
        rut = post.get("rut")
        country_id = int(post.get("country_id")) if post.get("country_id") else False
        date_str = post.get("date")  # Expected: '2023-10-27 10:00:00' (in appt_tz)

        if not date_str:
            return request.redirect(f"/agendame/{agendame_type_id}?error=no_date")

        appointment_type = request.env["agendame.type"].sudo().browse(agendame_type_id)

        # Convert submitted date back to UTC
        appt_tz = pytz.timezone(appointment_type.appointment_tz or "UTC")
        local_start = appt_tz.localize(
            datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        )
        utc_start = local_start.astimezone(pytz.UTC).replace(tzinfo=None)

        # --- RACE CONDITION PROTECTION ---
        # Re-verify availability before creating the event
        duration = appointment_type.appointment_duration
        utc_end = utc_start + datetime.timedelta(hours=duration)

        if not appointment_type._is_slot_available(utc_start, utc_end):
            return request.redirect(
                f"/agendame/{agendame_type_id}?error=already_booked"
            )

        # Create partner if doesn't exist
        partner = (
            request.env["res.partner"].sudo().search([("email", "=", email)], limit=1)
        )
        if not partner:
            partner = (
                request.env["res.partner"]
                .sudo()
                .create(
                    {
                        "name": name,
                        "email": email,
                        "phone": phone,
                        "vat": rut,  # Guardamos el RUT en el campo VAT estándar de Odoo
                        "country_id": country_id,
                    }
                )
            )
        else:
            # Si el partner existe, actualizamos datos si faltan
            vals = {}
            if not partner.vat:
                vals["vat"] = rut
            if not partner.phone:
                vals["phone"] = phone
            if not partner.country_id:
                vals["country_id"] = country_id
            if vals:
                partner.write(vals)

        # Create calendar event
        partner_ids = [(4, partner.id)]
        for user in appointment_type.staff_user_ids:
            if user.partner_id:
                partner_ids.append((4, user.partner_id.id))

        event = (
            request.env["calendar.event"]
            .sudo()
            .create(
                {
                    "name": f"{appointment_type.name}: {name}",
                    "start": utc_start,
                    "stop": utc_end,
                    "partner_ids": partner_ids,
                    "agendame_type_id": appointment_type.id,
                    "agendame_status": "booked",
                    "videocall_source": appointment_type.event_videocall_source,
                    "client_rut": rut,
                    "client_country_id": country_id,
                }
            )
        )

        return request.render(
            "agendame.appointment_thanks",
            {
                "event": event,
            },
        )
