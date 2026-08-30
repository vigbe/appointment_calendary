import logging

from odoo.api import Environment

_logger = logging.getLogger(__name__)

__all__ = ["migrate"]


def migrate(cr, version):
    """Post-migrate: provision a default appointment agenda for existing internal users.

    Uses raw SQL to resolve group membership because, during migration, the ORM
    may not have all relational fields (e.g. res.users.groups_id) fully loaded.
    """
    env = Environment(cr, 1, {})
    group_user = env.ref("base.group_user", raise_if_not_found=False)
    if not group_user:
        return

    cr.execute(
        "SELECT uid FROM res_groups_users_rel WHERE gid = %s",
        (group_user.id,),
    )
    user_ids = [row[0] for row in cr.fetchall()]

    AppointmentType = env["appointment_calendar.type"]
    for uid in user_ids:
        user = env["res.users"].browse(uid)
        if not user.active:
            continue
        try:
            AppointmentType._create_default_for_user(user)
        except Exception:
            _logger.exception(
                "Could not create default appointment type for user %s", user.login
            )
