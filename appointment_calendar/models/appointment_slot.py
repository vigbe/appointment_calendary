from odoo import fields, models


class AppointmentSlot(models.Model):
    _name = "appointment_calendar.slot"
    _description = "Horario de Cita"

    appointment_type_id = fields.Many2one(
        "appointment_calendar.type",
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
