# Agendame - Appointment Booking

Addon para Odoo que agrega una página pública de reservas a tu sitio web: los visitantes eligen un tipo de cita y un horario disponible, y Odoo crea el evento de calendario por vos.

## Qué hace

- Agrega la ruta pública `/appointment` a tu sitio web con la lista de tipos de cita activos.
- Cada tipo de cita tiene su propia página con los horarios disponibles calculados en tiempo real.
- La disponibilidad se calcula a partir de franjas horarias por día de la semana y de los calendarios reales de los usuarios asignados (detección de conflictos con una única consulta optimizada).
- Al reservar, se crea o actualiza automáticamente el contacto (nombre, email, teléfono, RUT/VAT y país).
- Se crea el evento de calendario con los asistentes correctos (cliente + personal asignado) y la fuente de videollamada configurada.
- Integración con CRM: cada oportunidad puede tener su tipo de cita y un enlace de reserva listo para compartir.
- Cada usuario interno recibe una agenda por defecto (lunes a sábado, 10:00 a 18:00, su zona horaria) al crearse.
- Funciona en Odoo Community Edition y no depende del módulo Enterprise `appointment`.

## Características principales

- Tipos de cita configurables: duración, zona horaria, personal asignado, franjas horarias por día, imagen, colores primario/secundario y días a mostrar.
- Validación de carrera al confirmar la reserva: se re-verifica la disponibilidad antes de crear el evento.
- Seguridad a nivel de registros: los usuarios internos solo gestionan sus propias agendas; los administradores tienen acceso total.
- Restricciones de propiedad: un usuario interno no puede agendar ni modificar citas de este módulo a nombre de otro.
- Menú integrado en la app nativa Calendario (`Citas → Tipos de Cita`).
- Campos adicionales en la cita: tipo, estado (solicitud/reservada/asistió/no asistió/cancelada), RUT del cliente y país.

## Dependencias

- `base`
- `crm`
- `calendar`
- `website`
- `mail`

## Instalación

1. Copia el addon `appointment_calendar` a tu carpeta de addons de Odoo.
2. Asegúrate de que Odoo pueda encontrar la ruta: agrega el directorio al `addons_path` si es necesario.
3. Reinicia el servidor de Odoo.
4. Actualiza la lista de aplicaciones y encuentra el addon **Agendame - Appointment Booking**.
5. Instálalo. Cada usuario interno recibirá automáticamente su agenda por defecto.

## Uso

1. Ve a **Calendario → Citas → Tipos de Cita** y ajusta horarios, duración y personal asignado.
2. Comparte la URL de reserva (`/appointment`) o el enlace específico de cada tipo de cita.
3. El visitante elige el tipo de cita, completa sus datos (nombre, email, teléfono, RUT y país) y selecciona un horario disponible.
4. La cita queda creada en el calendario de Odoo con el estado *Reservada*.

## Estructura del addon

- `__manifest__.py` — definición del addon.
- `__init__.py` — post_init_hook que provisiona agendas por defecto.
- `models/appointment_type.py` — modelo principal: tipos de cita y generación de horarios disponibles.
- `models/appointment_slot.py` — franjas horarias de disponibilidad por día de la semana.
- `models/calendar_event.py` — extensión del evento de calendario y restricciones de propiedad.
- `models/crm_lead.py` — integración con oportunidades CRM (enlace de reserva).
- `models/res_users.py` — agenda por defecto para usuarios internos nuevos.
- `controllers/main.py` — controlador del sitio público de reservas.
- `views/appointment_type_views.xml` — vistas backend (formulario/lista) y menú.
- `views/appointment_templates.xml` — plantillas QWeb del portal público.
- `views/calendar_event_views.xml` — herencia de la vista de calendario.
- `views/crm_lead_views_inherit.xml` — herencia de la vista de oportunidad.
- `security/` — reglas de registro y permisos de acceso.
- `tests/test_appointment_booking.py` — tests de reservas, seguridad y restricciones.

## Licencia

- `LGPL-3`

## Autor

- Victor Bastías Escobar
- Sitio: <https://vicbas.com/addons_odoo.html>
- Soporte: <contacto@vicbas.com>
