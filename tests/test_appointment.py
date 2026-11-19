# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError, UserError
import datetime


@tagged('post_install', '-at_install')
class TestClinicAppointment(TransactionCase):
    """Tests unitaires pour clinic.appointment (TF-RDV-01 → TF-RDV-04, TF-PER-01)"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Appointment = cls.env['clinic.appointment']

        cls.patient = cls.env['clinic.patient'].create({
            'name': 'Patient RDV Test',
            'birthdate': datetime.date(1985, 5, 5),
            'gender': 'male',
            'identity_verified': True,
        })

        cls.doctor = cls.env['res.users'].create({
            'name': 'Dr Test',
            'login': 'dr_test',
            'email': 'dr@test.com',
            'groups_id': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('gestion_clinique.group_clinic_medecin').id,
            ])],
        })

    def _make_appointment(self, **vals):
        start = vals.pop('date_start', datetime.datetime(2026, 12, 1, 9, 0))
        stop = vals.pop('date_stop', start + datetime.timedelta(hours=1))
        defaults = {
            'patient_id': self.patient.id,
            'doctor_id': self.doctor.id,
            'service': 'Consultation générale',
            'date_start': start,
            'date_stop': stop,
            'booking_channel': 'phone',
            'status': 'booked',
        }
        defaults.update(vals)
        return self.Appointment.create(defaults)

    # ----------------------------------------------------------
    # TF-RDV-01 — Double-booking refused (RG-RDV-01)
    # ----------------------------------------------------------
    def test_double_booking_refused(self):
        self._make_appointment()
        with self.assertRaises(ValidationError):
            self._make_appointment()

    def test_overlapping_slot_refused(self):
        self._make_appointment(
            date_start=datetime.datetime(2026, 12, 1, 9, 0),
            date_stop=datetime.datetime(2026, 12, 1, 10, 0),
        )
        with self.assertRaises(ValidationError):
            self._make_appointment(
                date_start=datetime.datetime(2026, 12, 1, 9, 30),
                date_stop=datetime.datetime(2026, 12, 1, 10, 30),
            )

    def test_adjacent_slot_ok(self):
        self._make_appointment(
            date_start=datetime.datetime(2026, 12, 1, 9, 0),
            date_stop=datetime.datetime(2026, 12, 1, 10, 0),
        )
        # 10:00 – 11:00 is adjacent, not overlapping → should succeed
        appt2 = self._make_appointment(
            date_start=datetime.datetime(2026, 12, 1, 10, 0),
            date_stop=datetime.datetime(2026, 12, 1, 11, 0),
        )
        self.assertTrue(appt2.id)

    def test_same_slot_different_doctor_ok(self):
        self._make_appointment()
        doctor2 = self.env['res.users'].create({
            'name': 'Dr Other', 'login': 'dr_other', 'email': 'dr2@test.com',
            'groups_id': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref('gestion_clinique.group_clinic_medecin').id,
            ])],
        })
        appt2 = self._make_appointment(doctor_id=doctor2.id)
        self.assertTrue(appt2.id)

    def test_cancelled_slot_does_not_block(self):
        appt1 = self._make_appointment()
        appt1.write({'status': 'cancelled'})
        # Now the slot is free
        appt2 = self._make_appointment()
        self.assertTrue(appt2.id)

    # ----------------------------------------------------------
    # TF-RDV-03 — Cancellation trace (RG-RDV-03)
    # ----------------------------------------------------------
    def test_cancel_requires_reason_and_confirmation(self):
        appt = self._make_appointment()
        wizard = self.env['clinic.appointment.cancel.wizard'].create({
            'appointment_id': appt.id,
            'cancel_reason': 'Patient empêché',
            'confirm_cancel': True,
        })
        wizard.action_confirm_cancel()

        self.assertEqual(appt.status, 'cancelled')
        self.assertEqual(appt.cancel_reason, 'Patient empêché')
        self.assertEqual(appt.cancel_user_id, self.env.user)
        self.assertIsNotNone(appt.cancel_date)

    def test_cancel_without_confirm_raises(self):
        appt = self._make_appointment()
        wizard = self.env['clinic.appointment.cancel.wizard'].create({
            'appointment_id': appt.id,
            'cancel_reason': 'Test',
            'confirm_cancel': False,
        })
        with self.assertRaises(UserError):
            wizard.action_confirm_cancel()

    # ----------------------------------------------------------
    # TF-RDV-04 — Confirmation trace (RG-RDV-04)
    # ----------------------------------------------------------
    def test_confirm_appointment_traced(self):
        appt = self._make_appointment(status='booked')
        appt.action_confirm()
        self.assertEqual(appt.status, 'confirmed')
        self.assertTrue(appt.confirmation_sent)
        self.assertIsNotNone(appt.confirmation_date)
        self.assertEqual(appt.confirmation_user_id, self.env.user)

    def test_confirm_only_from_draft_or_booked(self):
        appt = self._make_appointment(status='confirmed')
        with self.assertRaises(UserError):
            appt.action_confirm()

    # ----------------------------------------------------------
    # TF-RDV-02 — Reschedule: verify new slot BEFORE releasing old (RG-RDV-02)
    # ----------------------------------------------------------
    def test_reschedule_to_free_slot(self):
        appt = self._make_appointment(
            date_start=datetime.datetime(2026, 12, 1, 9, 0),
            date_stop=datetime.datetime(2026, 12, 1, 10, 0),
        )
        wizard = self.env['clinic.appointment.reschedule.wizard'].create({
            'appointment_id': appt.id,
            'new_date_start': datetime.datetime(2026, 12, 2, 14, 0),
            'new_date_stop': datetime.datetime(2026, 12, 2, 15, 0),
            'reason': 'Patient indisponible le 1er',
        })
        wizard.action_reschedule()

        self.assertEqual(appt.status, 'rescheduled')
        self.assertTrue(appt.reschedule_new_id)
        self.assertEqual(
            appt.reschedule_new_id.date_start,
            datetime.datetime(2026, 12, 2, 14, 0),
        )
        self.assertEqual(appt.reschedule_new_id.reschedule_origin_id, appt)

    def test_reschedule_to_occupied_slot_keeps_old(self):
        """RG-RDV-02: old slot is NOT released if new slot is occupied."""
        appt1 = self._make_appointment(
            date_start=datetime.datetime(2026, 12, 1, 9, 0),
            date_stop=datetime.datetime(2026, 12, 1, 10, 0),
        )
        # Occupy the target slot
        self._make_appointment(
            date_start=datetime.datetime(2026, 12, 2, 14, 0),
            date_stop=datetime.datetime(2026, 12, 2, 15, 0),
        )

        wizard = self.env['clinic.appointment.reschedule.wizard'].create({
            'appointment_id': appt1.id,
            'new_date_start': datetime.datetime(2026, 12, 2, 14, 0),
            'new_date_stop': datetime.datetime(2026, 12, 2, 15, 0),
            'reason': 'Test conflit',
        })

        with self.assertRaises(UserError):
            wizard.action_reschedule()

        # Old appointment untouched
        self.assertEqual(appt1.status, 'booked')
        self.assertFalse(appt1.reschedule_new_id)

    # ----------------------------------------------------------
    # TF-PER-01 — Doctor on leave: no slot offered (RG-PER-01)
    # ----------------------------------------------------------
    def test_doctor_on_leave_blocks_appointment(self):
        # Create hr.employee linked to doctor with a resource calendar
        calendar = self.env['resource.calendar'].create({
            'name': 'Calendrier Test',
        })
        employee = self.env['hr.employee'].create({
            'name': 'Dr Test Employee',
            'user_id': self.doctor.id,
            'resource_calendar_id': calendar.id,
        })
        # Create a leave covering 2026-12-15
        self.env['resource.calendar.leaves'].create({
            'name': 'Congé test',
            'calendar_id': calendar.id,
            'date_from': datetime.datetime(2026, 12, 15, 0, 0),
            'date_to': datetime.datetime(2026, 12, 16, 0, 0),
            'resource_id': employee.resource_id.id,
        })
        with self.assertRaises(ValidationError):
            self._make_appointment(
                date_start=datetime.datetime(2026, 12, 15, 9, 0),
                date_stop=datetime.datetime(2026, 12, 15, 10, 0),
            )

    # ----------------------------------------------------------
    # Status flow
    # ----------------------------------------------------------
    def test_full_status_flow(self):
        appt = self._make_appointment(status='booked')
        appt.action_confirm()
        self.assertEqual(appt.status, 'confirmed')
        appt.action_mark_arrived()
        self.assertEqual(appt.status, 'arrived')
        self.assertIsNotNone(appt.arrival_time)
        appt.action_start()
        self.assertEqual(appt.status, 'in_progress')
        appt.action_done()
        self.assertEqual(appt.status, 'done')

    def test_mark_arrived_requires_identity_verified(self):
        """RG-ACU-01: cannot mark arrived without identity verified."""
        patient_unverified = self.env['clinic.patient'].create({
            'name': 'Patient Non Vérifié',
            'birthdate': datetime.date(1990, 1, 1),
            'gender': 'female',
            'identity_verified': False,
        })
        appt = self._make_appointment(patient_id=patient_unverified.id)
        with self.assertRaises(UserError):
            appt.action_mark_arrived()

    # ----------------------------------------------------------
    # Sequence
    # ----------------------------------------------------------
    def test_appointment_identifier_sequential(self):
        appt1 = self._make_appointment()
        appt2 = self._make_appointment(
            date_start=datetime.datetime(2026, 12, 2, 9, 0),
            date_stop=datetime.datetime(2026, 12, 2, 10, 0),
        )
        self.assertRegex(appt1.name, r'^RDV-\d{5}$')
        self.assertNotEqual(appt1.name, appt2.name)