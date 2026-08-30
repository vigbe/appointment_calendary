"""Pre-migration for 19.0.2.2.0.

The appointment menus were re-parented under the native Calendar app
(``calendar.mail_menu_calendar``) and flattened to ``Citas -> Tipos de Cita``.
The legacy ``menu_appointment_type`` ("Configuracion") menu is dropped from the
data file. Reparent its only child *before* Odoo drops the parent so the menu
tree never references a non-existing parent (which on ``ON DELETE SET NULL``
would surface as a stray root app).
"""

import logging

_logger = logging.getLogger(__name__)


def _reparent_type_action_under_root(cr):
    cr.execute(
        """
        UPDATE ir_ui_menu
        SET parent_id = (
            SELECT mir.res_id
            FROM ir_model_data mir
            WHERE mir.module = 'appointment_calendar'
              AND mir.name = 'menu_appointment_root'
        )
        WHERE id IN (
            SELECT mir.res_id
            FROM ir_model_data mir
            WHERE mir.module = 'appointment_calendar'
              AND mir.name = 'menu_appointment_type_action'
        )
        """
    )


def migrate(cr, version):
    _logger.info(
        "appointment_calendar 19.0.2.2.0: reparenting appointment menus under Calendar"
    )
    _reparent_type_action_under_root(cr)
