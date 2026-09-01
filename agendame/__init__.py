import logging

from . import controllers, models

__all__ = ["controllers", "models"]

_logger = logging.getLogger(__name__)


def _create_default_appointment_types(env):
    """post_init_hook: create a default appointment agenda for every internal user.

    Only users belonging to the internal group (base.group_user) get a default
    agenda. Existing agendas are not duplicated.
    """
    AppointmentType = env["agendame.type"]
    group_user = env.ref("base.group_user", raise_if_not_found=False)
    if not group_user:
        return
    # Raw SQL: group membership is reliable here even if relational fields
    # are not fully loaded during module install.
    env.cr.execute(
        "SELECT uid FROM res_groups_users_rel WHERE gid = %s",
        (group_user.id,),
    )
    user_ids = [row[0] for row in env.cr.fetchall()]
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
