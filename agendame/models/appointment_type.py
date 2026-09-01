import datetime
from collections import Counter

import pytz
from odoo import _, api, fields, models
from odoo.addons.base.models.res_partner import _tz_get
from odoo.exceptions import ValidationError
from odoo.fields import Command


class AppointmentType(models.Model):
    _name = "agendame.type"
    _description = "Tipo de Cita"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Nombre", required=True, tracking=True)
    appointment_duration = fields.Float(
        string="Duración (Horas)", default=1.0, tracking=True
    )
    staff_user_ids = fields.Many2many(
        "res.users",
        string="Usuarios Asignados",
        default=lambda self: [Command.set(self.env.user.ids)],
    )
    slot_ids = fields.One2many(
        "agendame.slot",
        "appointment_type_id",
        string="Horarios Disponibles",
    )
    appointment_tz = fields.Selection(
        _tz_get,
        string="Zona Horaria",
        required=True,
        default=lambda self: self.env.user.tz or "UTC",
        tracking=True,
    )
    event_videocall_source = fields.Selection(
        [
            ("discuss", "Odoo Discuss"),
            ("google_meet", "Google Meet"),
            ("zoom", "Zoom"),
        ],
        string="Fuente de Videollamada",
        help="Fuente del enlace de videollamada para la reunión.",
    )

    image_1920 = fields.Image(string="Imagen", max_width=1920, max_height=1920)

    color_primary = fields.Char(
        string="Color Primario",
        default="#714B67",
        help="Color de botones y acentos en la página pública de reservas.",
    )
    color_secondary = fields.Char(
        string="Color Secundario",
        default="#212529",
        help="Color de fondo del panel lateral en la página pública de reservas.",
    )

    active = fields.Boolean(string="Activo", default=True, tracking=True)
    max_schedule_days = fields.Integer(
        string="Días a Mostrar",
        default=7,
        help="Número de días disponibles para agendar desde hoy.",
    )

    @api.constrains("staff_user_ids")
    def _check_staff_user_ids(self):
        for record in self:
            if not record.staff_user_ids:
                raise ValidationError(
                    _("Debe asignar al menos un usuario a este tipo de cita.")
                )

    @api.constrains("staff_user_ids")
    def _check_staff_user_self_only(self):
        """Non-admin internal users can only manage their own agendas.

        Admins (base.group_system) can assign any user. Superuser context
        (install hooks, automated agenda provisioning) is always allowed.
        """
        if self.env.su or self.env.user.has_group("base.group_system"):
            return
        for record in self:
            if record.staff_user_ids != self.env.user:
                raise ValidationError(
                    _(
                        "Solo un administrador puede asignar otros usuarios. "
                        "Como usuario interno solo puede crear citas para sí mismo."
                    )
                )

    # ------------------------------------------------------------------
    # Default agenda provisioning
    # ------------------------------------------------------------------
    _DEFAULT_SLOT_WEEKDAYS = ("1", "2", "3", "4", "5", "6")  # Monday..Saturday
    _DEFAULT_SLOT_START = 10.0
    _DEFAULT_SLOT_END = 18.0

    @api.model
    def _create_default_for_user(self, user):
        """Create a default, editable appointment agenda for the given user.

        The agenda is created with Mon-Sat availability from 10:00 to 18:00,
        the user's own timezone and the user as the only staff member.
        It is skipped if the user already has an assigned agenda.
        """
        if not user:
            return self.env["agendame.type"]
        existing = self.search([("staff_user_ids", "in", user.id)], limit=1)
        if existing:
            return existing
        slots = [
            Command.create(
                {
                    "weekday": wd,
                    "start_hour": self._DEFAULT_SLOT_START,
                    "end_hour": self._DEFAULT_SLOT_END,
                }
            )
            for wd in self._DEFAULT_SLOT_WEEKDAYS
        ]
        return self.create(
            {
                "name": _("Agenda de %s") % (user.name or user.login),
                "appointment_duration": 1.0,
                "appointment_tz": user.tz or "UTC",
                "staff_user_ids": [Command.set(user.ids)],
                "slot_ids": slots,
            }
        )

    @api.onchange("staff_user_ids")
    def _onchange_staff_user_ids(self):
        if not self.staff_user_ids:
            self.appointment_tz = self.env.user.tz or "UTC"
            return

        timezones = self.staff_user_ids.mapped("tz")
        # Filter out False/None
        timezones = [tz for tz in timezones if tz]

        if not timezones:
            self.appointment_tz = self.env.user.tz or "UTC"
            return

        tz_counts = Counter(timezones)
        most_common = tz_counts.most_common(1)

        if most_common:
            # If multiple have same count,Counter returns them in order of first encounter
            self.appointment_tz = most_common[0][0]
        else:
            # Fallback to first user's timezone if any
            self.appointment_tz = timezones[0]

    booking_url = fields.Char(string="URL de Reserva", compute="_compute_booking_url")

    def _compute_booking_url(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        for app_type in self:
            app_type.booking_url = f"{base_url}/appointment/{app_type.id}"

    def _get_appointment_slots(self, reference_date=None):
        """
        Generate available slots localized in the appointment's timezone.
        Returns a list of UTC datetimes.

        OPTIMIZED: Single query for all events instead of N+1 queries.
        """
        self.ensure_one()
        if not reference_date:
            reference_date = fields.Date.today()

        appt_tz = pytz.timezone(self.appointment_tz or "UTC")
        duration = self.appointment_duration
        max_days = self.max_schedule_days or 7

        # Pre-calculate date range for the query
        end_date = reference_date + datetime.timedelta(days=max_days)

        # Convert to UTC bounds for the query
        range_start_local = appt_tz.localize(
            datetime.datetime.combine(reference_date, datetime.time.min)
        )
        range_end_local = appt_tz.localize(
            datetime.datetime.combine(end_date, datetime.time.max)
        )
        range_start_utc = range_start_local.astimezone(pytz.UTC).replace(tzinfo=None)
        range_end_utc = range_end_local.astimezone(pytz.UTC).replace(tzinfo=None)

        # Pre-fetch ALL events for ALL staff users in the date range (SINGLE QUERY)
        partner_ids = self.staff_user_ids.mapped("partner_id").ids
        busy_events = []
        if partner_ids:
            busy_events = (
                self.env["calendar.event"]
                .sudo()
                .search_read(
                    [
                        ("partner_ids", "in", partner_ids),
                        ("start", "<", fields.Datetime.to_string(range_end_utc)),
                        ("stop", ">", fields.Datetime.to_string(range_start_utc)),
                    ],
                    ["start", "stop", "partner_ids"],
                )
            )

        # Build a dict of busy periods per partner for fast lookup
        busy_by_partner = {pid: [] for pid in partner_ids}
        for event in busy_events:
            event_start = (
                fields.Datetime.from_string(event["start"])
                if isinstance(event["start"], str)
                else event["start"]
            )
            event_stop = (
                fields.Datetime.from_string(event["stop"])
                if isinstance(event["stop"], str)
                else event["stop"]
            )
            for pid in event["partner_ids"]:
                if pid in busy_by_partner:
                    busy_by_partner[pid].append((event_start, event_stop))

        # Pre-index slots by weekday for faster lookup
        slots_by_weekday = {}
        for slot in self.slot_ids:
            slots_by_weekday.setdefault(slot.weekday, []).append(
                (slot.start_hour, slot.end_hour)
            )

        available_slots = []

        for i in range(max_days):
            check_date = reference_date + datetime.timedelta(days=i)
            weekday = str(check_date.isoweekday())

            day_slots = slots_by_weekday.get(weekday, [])
            for start_hour, end_hour in day_slots:
                current_hour = start_hour
                while current_hour + duration <= end_hour:
                    h = int(current_hour)
                    m = int(round((current_hour - h) * 60))

                    local_dt = appt_tz.localize(
                        datetime.datetime.combine(check_date, datetime.time(h, m))
                    )
                    utc_dt = local_dt.astimezone(pytz.UTC).replace(tzinfo=None)
                    slot_end_utc = utc_dt + datetime.timedelta(hours=duration)

                    # Check availability using pre-fetched data
                    if self._is_slot_available_fast(
                        utc_dt, slot_end_utc, partner_ids, busy_by_partner
                    ):
                        available_slots.append(utc_dt)

                    current_hour += duration

        return sorted(set(available_slots))

    def _is_slot_available_fast(self, start_dt, end_dt, partner_ids, busy_by_partner):
        """
        Check slot availability using pre-fetched busy periods.
        Returns True if at least one staff member is free.
        """
        if not partner_ids:
            return True

        for pid in partner_ids:
            is_busy = False
            for event_start, event_stop in busy_by_partner.get(pid, []):
                # Check overlap: event_start < slot_end AND event_stop > slot_start
                if event_start < end_dt and event_stop > start_dt:
                    is_busy = True
                    break
            if not is_busy:
                return True  # At least one user is free

        return False

    def _is_slot_available(self, start_dt, end_dt):
        """
        Check if any of the staff users are free in this time range.
        DEPRECATED: Use _get_appointment_slots which uses optimized batch checking.
        Kept for backward compatibility.
        """
        self.ensure_one()
        if not self.staff_user_ids:
            return True

        partner_ids = self.staff_user_ids.mapped("partner_id").ids
        overlapping_event = (
            self.env["calendar.event"]
            .sudo()
            .search(
                [
                    ("partner_ids", "in", partner_ids),
                    ("start", "<", fields.Datetime.to_string(end_dt)),
                    ("stop", ">", fields.Datetime.to_string(start_dt)),
                ],
                limit=1,
            )
        )

        return not overlapping_event
