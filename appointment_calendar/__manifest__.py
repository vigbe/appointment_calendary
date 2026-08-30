{
    "name": "Agendame - Appointment Booking",
    "summary": "Public appointment booking website integrated with Calendar and CRM.",
    "description": (
        "Adds a public booking page to your website where visitors pick an "
        "appointment type and an available time slot, and Odoo creates the "
        "calendar event for you. Availability is computed from per-weekday "
        "time slots and staff users' real calendars, with conflict detection. "
        "Includes CRM integration (booking link per lead), automatic default "
        "agendas for internal users, and record-level security. Works with "
        "Odoo Community Edition; does not require the Enterprise Appointments "
        "module."
    ),
    "author": "Victor Bastías Escobar",
    "website": "https://vicbas.com/addons_odoo.html",
    "support": "contacto@vicbas.com",
    "maintainer": "Victor Bastías Escobar",
    "category": "Sales/CRM",
    "version": "18.0.1.0.0",
    "depends": ["base", "crm", "calendar", "website", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "security/appointment_security.xml",
        "views/appointment_type_views.xml",
        "views/calendar_event_views.xml",
        "views/appointment_templates.xml",
        "views/crm_lead_views_inherit.xml",
    ],
    "images": [
        "static/description/thumbnail.png",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "post_init_hook": "_create_default_appointment_types",
    "license": "LGPL-3",
}
