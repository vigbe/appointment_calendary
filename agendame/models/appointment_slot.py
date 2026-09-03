from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AppointmentSlot(models.Model):
    _name = "agendame.slot"
    _description = "Horario de Cita"

    agendame_type_id = fields.Many2one(
        "agendame.type",
        string="Tipo de Cita",
        ondelete="cascade",
        required=True,
    )
    weekday = fields.Selection(
        [
            ("1", "Lunes"),
            ("2", "Martes"),
            ("3", "Miércoles"),
            ("4", "Jueves"),
            ("5", "Viernes"),
            ("6", "Sábado"),
            ("7", "Domingo"),
        ],
        string="Día de la Semana",
        required=True,
    )
    start_hour = fields.Float(string="Hora Inicio", required=True)
    end_hour = fields.Float(string="Hora Fin", required=True)

    @api.constrains("start_hour", "end_hour")
    def _check_hours_range(self):
        """Keep hour ranges sane so slot generation cannot crash.

        Out-of-range hours (e.g. 24.5) would make datetime.time() raise and
        break the public booking page of the whole agenda, while inverted
        ranges silently produce zero slots.
        """
        for slot in self:
            if not (0 <= slot.start_hour < slot.end_hour <= 24):
                raise ValidationError(
                    _(
                        "El horario debe cumplir 0 <= hora inicio < hora fin <= 24 "
                        "(actual: inicio %s, fin %s)."
                    )
                    % (slot.start_hour, slot.end_hour)
                )
