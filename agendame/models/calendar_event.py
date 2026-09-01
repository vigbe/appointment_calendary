from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    agendame_type_id = fields.Many2one("agendame.type", string="Tipo de Cita")
    agendame_status = fields.Selection(
        [
            ("request", "Solicitud"),
            ("booked", "Reservada"),
            ("attended", "Asistió"),
            ("no_show", "No Asistió"),
            ("cancelled", "Cancelada"),
        ],
        string="Estado de la Cita",
        default="booked",
    )

    # Almacenamos datos extra del agendamiento
    client_rut = fields.Char(string="RUT Cliente")
    client_country_id = fields.Many2one("res.country", string="País Cliente")

    # ------------------------------------------------------------------
    # Restriccion: un usuario interno (no administrador) solo puede crear
    # o editar citas de este modulo que lo involucren a EL MISMO. No puede
    # agendar a nombre de otro usuario ni agregar a otras personas (clientes
    # o companeros) como asistentes.
    #
    # El flujo publico de reserva usa sudo() (env.su = True) y los
    # administradores (base.group_system) estan exentos, por lo que el
    # booking web no se ve afectado.
    # ------------------------------------------------------------------
    @api.constrains("user_id", "partner_ids", "agendame_type_id")
    def _check_appointment_self_only(self):
        if self.env.su or self.env.user.has_group("base.group_system"):
            return
        user = self.env.user
        own_partner = user.partner_id
        for event in self:
            # Solo aplica a las citas de este modulo
            if not event.agendame_type_id:
                continue
            # El organizador debe ser el propio usuario (o quedar vacio)
            if event.user_id and event.user_id != user:
                raise ValidationError(
                    _(
                        "Solo podes crear o editar citas en las que seas el "
                        "organizador; no agendes a nombre de otro usuario."
                    )
                )
            # Los asistentes solo pueden ser el propio usuario (o ninguno)
            foreign_attendees = event.partner_ids.filtered(lambda p: p != own_partner)
            if foreign_attendees:
                raise ValidationError(
                    _(
                        "Las citas solo pueden involucrarte a ti mismo; no podes "
                        "agregar a otras personas como asistentes."
                    )
                )

    def _check_appointment_ownership(self):
        """Un usuario no administrador no debe escribir ni eliminar citas de
        este modulo cuyo organizador sea otro usuario (defense in depth sobre
        las reglas nativas de calendar)."""
        if self.env.su or self.env.user.has_group("base.group_system"):
            return
        user = self.env.user
        for event in self:
            if not event.agendame_type_id:
                continue
            if event.user_id and event.user_id != user:
                raise UserError(
                    _("No podes modificar citas de las que no sos el organizador.")
                )

    def write(self, vals):
        # Validamos la propiedad ANTES de escribir usando el estado actual,
        # asi un usuario no puede "robar" una cita ajena seteandose a si
        # mismo como organizador.
        self._check_appointment_ownership()
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_check_appointment_ownership(self):
        self._check_appointment_ownership()
