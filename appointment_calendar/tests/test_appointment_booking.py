import datetime

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, new_test_user


class TestAppointmentBooking(TransactionCase):
    def setUp(self):
        super().setUp()
        self.user = self.env.user
        self.user2 = self.env["res.users"].create(
            {
                "name": "Test User 2",
                "login": "testuser2@test.com",
                "email": "testuser2@test.com",
            }
        )
        self.appointment_type = self.env["appointment_calendar.type"].create(
            {
                "name": "Test Consultation",
                "appointment_duration": 1.0,
                "staff_user_ids": [(4, self.user.id)],
            }
        )
        self.slot = self.env["appointment_calendar.slot"].create(
            {
                "appointment_type_id": self.appointment_type.id,
                "weekday": "1",  # Monday
                "start_hour": 9.0,
                "end_hour": 17.0,
            }
        )

    def test_availability_calculation(self):
        """Test that slots are correctly generated for available time ranges."""
        ref_date = datetime.date(2023, 10, 23)  # Monday
        slots = self.appointment_type._get_appointment_slots(reference_date=ref_date)

        # Should have slots for Monday (9:00, 10:00, ..., 16:00) = 8 slots
        monday_slots = [s for s in slots if s.date() == ref_date]
        self.assertEqual(len(monday_slots), 8)

    def test_booking_conflict(self):
        """Test that conflicting events block slot availability."""
        start_dt = datetime.datetime(2023, 10, 23, 10, 0, 0)
        end_dt = start_dt + datetime.timedelta(hours=1)

        self.env["calendar.event"].create(
            {
                "name": "Existing Meeting",
                "start": start_dt,
                "stop": end_dt,
                "partner_ids": [(4, self.user.partner_id.id)],
            }
        )

        is_available = self.appointment_type._is_slot_available(start_dt, end_dt)
        self.assertFalse(is_available, "Slot should NOT be available due to conflict")

        is_available_other = self.appointment_type._is_slot_available(
            start_dt + datetime.timedelta(hours=2), end_dt + datetime.timedelta(hours=2)
        )
        self.assertTrue(is_available_other, "Other slot should be available")

    def test_is_slot_available_fast_no_conflicts(self):
        """Test _is_slot_available_fast returns True when no conflicts exist."""
        partner_ids = [self.user.partner_id.id]
        busy_by_partner = {self.user.partner_id.id: []}

        start_dt = datetime.datetime(2023, 10, 23, 10, 0, 0)
        end_dt = start_dt + datetime.timedelta(hours=1)

        result = self.appointment_type._is_slot_available_fast(
            start_dt, end_dt, partner_ids, busy_by_partner
        )
        self.assertTrue(result, "Slot should be available with no conflicts")

    def test_is_slot_available_fast_with_conflict(self):
        """Test _is_slot_available_fast returns False when slot overlaps with busy period."""
        partner_ids = [self.user.partner_id.id]

        # Busy from 10:00 to 11:00
        busy_by_partner = {
            self.user.partner_id.id: [
                (
                    datetime.datetime(2023, 10, 23, 10, 0, 0),
                    datetime.datetime(2023, 10, 23, 11, 0, 0),
                )
            ]
        }

        # Try to book 10:00-11:00 (exact overlap)
        start_dt = datetime.datetime(2023, 10, 23, 10, 0, 0)
        end_dt = start_dt + datetime.timedelta(hours=1)

        result = self.appointment_type._is_slot_available_fast(
            start_dt, end_dt, partner_ids, busy_by_partner
        )
        self.assertFalse(result, "Slot should NOT be available due to exact overlap")

    def test_is_slot_available_fast_partial_overlap(self):
        """Test _is_slot_available_fast detects partial overlaps."""
        partner_ids = [self.user.partner_id.id]

        # Busy from 10:30 to 11:30
        busy_by_partner = {
            self.user.partner_id.id: [
                (
                    datetime.datetime(2023, 10, 23, 10, 30, 0),
                    datetime.datetime(2023, 10, 23, 11, 30, 0),
                )
            ]
        }

        # Try to book 10:00-11:00 (partial overlap)
        start_dt = datetime.datetime(2023, 10, 23, 10, 0, 0)
        end_dt = start_dt + datetime.timedelta(hours=1)

        result = self.appointment_type._is_slot_available_fast(
            start_dt, end_dt, partner_ids, busy_by_partner
        )
        self.assertFalse(result, "Slot should NOT be available due to partial overlap")

    def test_is_slot_available_fast_multiple_users_one_free(self):
        """Test that slot is available if at least one staff member is free."""
        self.appointment_type.write({"staff_user_ids": [(4, self.user2.id)]})

        partner_ids = [self.user.partner_id.id, self.user2.partner_id.id]

        # User 1 is busy, User 2 is free
        busy_by_partner = {
            self.user.partner_id.id: [
                (
                    datetime.datetime(2023, 10, 23, 10, 0, 0),
                    datetime.datetime(2023, 10, 23, 11, 0, 0),
                )
            ],
            self.user2.partner_id.id: [],
        }

        start_dt = datetime.datetime(2023, 10, 23, 10, 0, 0)
        end_dt = start_dt + datetime.timedelta(hours=1)

        result = self.appointment_type._is_slot_available_fast(
            start_dt, end_dt, partner_ids, busy_by_partner
        )
        self.assertTrue(result, "Slot should be available because user2 is free")

    def test_is_slot_available_fast_all_users_busy(self):
        """Test that slot is unavailable when all staff members are busy."""
        self.appointment_type.write({"staff_user_ids": [(4, self.user2.id)]})

        partner_ids = [self.user.partner_id.id, self.user2.partner_id.id]

        # Both users are busy
        busy_by_partner = {
            self.user.partner_id.id: [
                (
                    datetime.datetime(2023, 10, 23, 10, 0, 0),
                    datetime.datetime(2023, 10, 23, 11, 0, 0),
                )
            ],
            self.user2.partner_id.id: [
                (
                    datetime.datetime(2023, 10, 23, 9, 30, 0),
                    datetime.datetime(2023, 10, 23, 10, 30, 0),
                )
            ],
        }

        start_dt = datetime.datetime(2023, 10, 23, 10, 0, 0)
        end_dt = start_dt + datetime.timedelta(hours=1)

        result = self.appointment_type._is_slot_available_fast(
            start_dt, end_dt, partner_ids, busy_by_partner
        )
        self.assertFalse(
            result, "Slot should NOT be available because all users are busy"
        )

    def test_is_slot_available_fast_no_partners(self):
        """Test that slot is available when no staff is assigned."""
        result = self.appointment_type._is_slot_available_fast(
            datetime.datetime(2023, 10, 23, 10, 0, 0),
            datetime.datetime(2023, 10, 23, 11, 0, 0),
            [],  # No partners
            {},
        )
        self.assertTrue(result, "Slot should be available when no staff assigned")

    def test_get_appointment_slots_excludes_conflicts(self):
        """Test that _get_appointment_slots correctly excludes conflicting times."""
        ref_date = datetime.date(2023, 10, 23)  # Monday

        # Create event blocking 10:00-11:00
        self.env["calendar.event"].create(
            {
                "name": "Blocking Meeting",
                "start": datetime.datetime(2023, 10, 23, 10, 0, 0),
                "stop": datetime.datetime(2023, 10, 23, 11, 0, 0),
                "partner_ids": [(4, self.user.partner_id.id)],
            }
        )

        slots = self.appointment_type._get_appointment_slots(reference_date=ref_date)
        monday_slots = [s for s in slots if s.date() == ref_date]

        # Should have 7 slots instead of 8 (10:00 is blocked)
        self.assertEqual(len(monday_slots), 7)

        # Verify 10:00 is not in the list
        slot_hours = [s.hour for s in monday_slots]
        self.assertNotIn(10, slot_hours, "10:00 slot should be excluded")


class TestAppointmentSecurity(TransactionCase):
    """Verify record rules and the staff-self-only constraint."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Internal user without admin rights
        cls.user_a = new_test_user(cls.env, login="staff_a", groups="base.group_user")
        cls.user_b = new_test_user(cls.env, login="staff_b", groups="base.group_user")

        # Admin user
        cls.user_admin = new_test_user(
            cls.env, login="staff_admin", groups="base.group_system"
        )

    def test_constraint_user_cannot_assign_other_staff(self):
        """A non-admin user cannot create an agenda with someone else on staff."""
        with self.env.with_user(self.user_a), self.assertRaises(ValidationError):
            self.env["appointment_calendar.type"].create(
                {
                    "name": "Agenda de otro",
                    "appointment_duration": 1.0,
                    "staff_user_ids": [(4, self.user_b.id)],
                }
            )

    def test_constraint_user_can_assign_self(self):
        """A non-admin user CAN create an agenda with themselves as staff."""
        with self.env.with_user(self.user_a):
            agenda = self.env["appointment_calendar.type"].create(
                {
                    "name": "Mi Agenda",
                    "appointment_duration": 1.0,
                }
            )
            self.assertEqual(agenda.staff_user_ids, self.user_a)

    def test_record_rule_user_sees_only_own(self):
        """User A creates an agenda → only visible to A, not B."""
        with self.env.with_user(self.user_a):
            agenda_a = self.env["appointment_calendar.type"].create(
                {
                    "name": "Agenda A",
                    "appointment_duration": 1.0,
                }
            )

        # User B: search should NOT return A's agenda
        with self.env.with_user(self.user_b):
            visible = self.env["appointment_calendar.type"].search(
                [
                    ("id", "=", agenda_a.id),
                ]
            )
            self.assertFalse(visible, "User B should NOT see User A's agenda")

        # User A: search SHOULD return their own agenda
        with self.env.with_user(self.user_a):
            visible = self.env["appointment_calendar.type"].search(
                [
                    ("id", "=", agenda_a.id),
                ]
            )
            self.assertTrue(visible, "User A should see their own agenda")

    def test_admin_sees_all_agendas(self):
        """Admin can see agendas from any user."""
        with self.env.with_user(self.user_a):
            agenda_a = self.env["appointment_calendar.type"].create(
                {
                    "name": "Agenda A",
                    "appointment_duration": 1.0,
                }
            )
        with self.env.with_user(self.user_b):
            agenda_b = self.env["appointment_calendar.type"].create(
                {
                    "name": "Agenda B",
                    "appointment_duration": 1.0,
                }
            )

        with self.env.with_user(self.user_admin):
            all_visible = self.env["appointment_calendar.type"].search([])
            self.assertIn(agenda_a, all_visible)
            self.assertIn(agenda_b, all_visible)

    def test_admin_can_create_for_others(self):
        """Admin can create an agenda with any staff."""
        with self.env.with_user(self.user_admin):
            agenda = self.env["appointment_calendar.type"].create(
                {
                    "name": "Agenda Admin",
                    "appointment_duration": 1.0,
                    "staff_user_ids": [
                        (4, self.user_a.id),
                        (4, self.user_b.id),
                    ],
                }
            )
            self.assertEqual(len(agenda.staff_user_ids), 2)

    def test_user_cannot_delete_own_agenda(self):
        """Non-admin users cannot unlink their own agenda (ACL restriction)."""
        with self.env.with_user(self.user_a):
            agenda = self.env["appointment_calendar.type"].create(
                {
                    "name": "Agenda a borrar",
                    "appointment_duration": 1.0,
                }
            )
        with self.env.with_user(self.user_a), self.assertRaises(AccessError):
            agenda.unlink()

    def test_admin_can_delete_any_agenda(self):
        """Admin can unlink any agenda."""
        with self.env.with_user(self.user_a):
            agenda = self.env["appointment_calendar.type"].create(
                {
                    "name": "Agenda a borrar por admin",
                    "appointment_duration": 1.0,
                }
            )
            with self.env.with_user(self.user_admin):
                agenda.unlink()
                self.assertFalse(agenda.exists())


class TestAppointmentEventRestriction(TransactionCase):
    """A non-admin user can only create/edit module appointments (calendar.event
    with appointment_type_id) that involve themselves, and cannot modify an
    appointment owned by another user even if they are an attendee."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_a = new_test_user(cls.env, login="evt_a", groups="base.group_user")
        cls.user_b = new_test_user(cls.env, login="evt_b", groups="base.group_user")
        cls.admin = new_test_user(
            cls.env, login="evt_admin", groups="base.group_system"
        )

        # Appointment types created by admin, each with its own staff user.
        with cls.env.with_user(cls.admin):
            cls.appointment_type_a = cls.env["appointment_calendar.type"].create(
                {
                    "name": "Agenda A",
                    "appointment_duration": 1.0,
                    "staff_user_ids": [(4, cls.user_a.id)],
                }
            )
            cls.appointment_type_b = cls.env["appointment_calendar.type"].create(
                {
                    "name": "Agenda B",
                    "appointment_duration": 1.0,
                    "staff_user_ids": [(4, cls.user_b.id)],
                }
            )

    def _event_vals(self, appt_type):
        return {
            "name": "Cita",
            "start": datetime.datetime(2023, 10, 23, 10, 0, 0),
            "stop": datetime.datetime(2023, 10, 23, 11, 0, 0),
            "appointment_type_id": appt_type.id,
        }

    def test_user_can_create_own_appointment(self):
        """A user can create a module appointment with only themselves."""
        with self.env.with_user(self.user_a):
            event = self.env["calendar.event"].create(
                self._event_vals(self.appointment_type_a)
            )
            self.assertTrue(event.exists())

    def test_user_can_add_self_as_attendee(self):
        """Adding oneself as attendee is allowed."""
        vals = self._event_vals(self.appointment_type_a)
        vals["partner_ids"] = [(4, self.user_a.partner_id.id)]
        with self.env.with_user(self.user_a):
            event = self.env["calendar.event"].create(vals)
            self.assertIn(self.user_a.partner_id, event.partner_ids)

    def test_user_cannot_add_other_attendee(self):
        """Adding another person (client or peer) as attendee is blocked."""
        vals = self._event_vals(self.appointment_type_a)
        vals["partner_ids"] = [(4, self.user_b.partner_id.id)]
        with self.env.with_user(self.user_a), self.assertRaises(ValidationError):
            self.env["calendar.event"].create(vals)

    def test_user_cannot_set_other_organizer(self):
        """Setting another user as organizer is blocked."""
        vals = self._event_vals(self.appointment_type_a)
        vals["user_id"] = self.user_b.id
        with self.env.with_user(self.user_a), self.assertRaises(ValidationError):
            self.env["calendar.event"].create(vals)

    def test_user_cannot_add_other_attendee_via_write(self):
        """The constraint also applies when editing an existing appointment."""
        with self.env.with_user(self.user_a):
            event = self.env["calendar.event"].create(
                self._event_vals(self.appointment_type_a)
            )
        with self.env.with_user(self.user_a), self.assertRaises(ValidationError):
            event.write({"partner_ids": [(4, self.user_b.partner_id.id)]})

    def test_admin_can_add_others(self):
        """Admins are exempt and can add anyone."""
        vals = self._event_vals(self.appointment_type_a)
        vals["partner_ids"] = [(4, self.user_b.partner_id.id)]
        with self.env.with_user(self.admin):
            event = self.env["calendar.event"].create(vals)
            self.assertIn(self.user_b.partner_id, event.partner_ids)

    def test_attendee_cannot_edit_other_organizer_appointment(self):
        """An attendee (not organizer) cannot edit the appointment; Odoo's native
        calendar rule allows the write, so the ownership override must block it."""
        with self.env.with_user(self.admin):
            event = self.env["calendar.event"].create(
                {
                    "name": "Cita de B",
                    "start": datetime.datetime(2023, 10, 23, 10, 0, 0),
                    "stop": datetime.datetime(2023, 10, 23, 11, 0, 0),
                    "appointment_type_id": self.appointment_type_b.id,
                    "user_id": self.user_b.id,
                    "partner_ids": [(4, self.user_a.partner_id.id)],  # a is attendee
                }
            )
        with self.env.with_user(self.user_a), self.assertRaises(UserError):
            event.write({"name": "Hackeada"})
