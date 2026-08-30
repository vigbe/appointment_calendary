
from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    appointment_type_id = fields.Many2one('appointment_calendar.type', string='Tipo de Cita para Reserva')
    booking_link = fields.Char(string='Enlace de Reserva', compute='_compute_booking_link')

    @api.depends('appointment_type_id')
    def _compute_booking_link(self):
        for lead in self:
            if lead.appointment_type_id:
                lead.booking_link = lead.appointment_type_id.booking_url
            else:
                lead.booking_link = False

    def action_send_appointment_link(self):
        self.ensure_one()
        if not self.booking_link:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': 'Por favor seleccione un Tipo de Cita primero.',
                    'sticky': False,
                }
            }

        # In a more advanced implementation, this could open an email composer.
        # For now, we'll just ensure it's visible to copy.
        return True
