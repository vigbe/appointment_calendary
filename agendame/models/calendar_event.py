# pyright: reportMissingImports=false
# (odoo framework imports resolve only inside the Odoo runtime/container)
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
    @api.constrains("user_id", "partner_ids", "attendee_ids", "agendame_type_id")
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

    # ------------------------------------------------------------------
    # Odoo 19 redirige las escrituras de asistentes al modelo
    # calendar.attendee (no revalida los campos del evento), por lo que un
    # @api.constrains sobre partner_ids nunca se dispara en esa serie.
    # Este guard a nivel de vals (PRE-super) es la fuente de verdad
    # portable 16-19; el constrains queda como defensa adicional.
    # ------------------------------------------------------------------
    def _resolve_partner_commands(self, base, commands):
        """Resolve the partner set that ``commands`` would produce."""
        Partner = self.env["res.partner"]
        result = base
        for cmd in commands or []:
            if isinstance(cmd, int):
                result |= Partner.browse([cmd])
            elif cmd and cmd[0] == 6:  # replace
                result = Partner.browse(cmd[2] or [])
            elif cmd and cmd[0] in (4, 1):  # link / update
                result |= Partner.browse([cmd[1]])
            elif cmd and cmd[0] in (3, 2):  # unlink / delete one
                rid = cmd[1]
                result = result.filtered(lambda p, _rid=rid: p.id != _rid)
            elif cmd and cmd[0] == 5:  # clear all
                result = Partner.browse([])
        return result

    def _guard_module_vals(self, vals, current_partner_ids=None):
        """Raise when a non-admin module-appointment write involves others."""
        if self.env.su or self.env.user.has_group("base.group_system"):
            return
        if not vals.get("agendame_type_id") and not any(
            r.agendame_type_id for r in self
        ):
            return
        user = self.env.user
        own_partner = user.partner_id
        new_uid = vals.get("user_id")
        if new_uid:
            uid = new_uid.id if hasattr(new_uid, "id") else int(new_uid)
            if uid != user.id:
                raise ValidationError(
                    _(
                        "Solo podes crear o editar citas en las que seas el "
                        "organizador; no agendes a nombre de otro usuario."
                    )
                )
        if "partner_ids" in vals:
            base = (
                current_partner_ids
                if current_partner_ids is not None
                else self.env["res.partner"]
            )
            target = self._resolve_partner_commands(base, vals["partner_ids"])
            foreign = target.filtered(lambda p: p != own_partner)
            if foreign:
                raise ValidationError(
                    _(
                        "Las citas solo pueden involucrarte a ti mismo; no podes "
                        "agregar a otras personas como asistentes."
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._guard_module_vals(vals)
        return super().create(vals_list)

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
        # mismo como organizador. El guard de vals cubre el caso Odoo 19
        # donde las escrituras de asistentes no revalidan el evento.
        self._check_appointment_ownership()
        for event in self:
            if event.agendame_type_id:
                event._guard_module_vals(vals, current_partner_ids=event.partner_ids)
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_check_appointment_ownership(self):
        self._check_appointment_ownership()
