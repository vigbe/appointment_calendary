from odoo import api, models

__all__ = ["ResUsers"]


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        AppointmentType = self.env["agendame.type"]
        for user in users:
            # Only internal users (base.group_user) get a default agenda.
            if not user.active:
                continue
            try:
                if user.has_group("base.group_user"):
                    AppointmentType._create_default_for_user(user)
            except Exception:
                # Never block user creation because of the default agenda.
                pass
        return users
