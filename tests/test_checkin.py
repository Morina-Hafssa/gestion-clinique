# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError
import datetime


@tagged('post_install', '-at_install')
class TestClinicCheckin(TransactionCase):
    """Tests du check-in (TF-ACU-01, TF-ACU-02)"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Appointment = cls.env['clinic.appointment']
        cls.Visit = cls.env['clinic.visit']

        cls.doctor = cls.env['res.users'].create({
            'name': 'Dr Checkin',
            'login': 'dr_checkin',
            'email': 'dr.checkin@test.com',
            'groups_id': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('gestion_clinique.group_clinic_medecin').id,
            ])],
        })

        cls.patient_verified = cls.env['clinic.patient'].create({
            'name': 'Patient Vérifié',
            'birthdate': datetime.date(1985, 5, 5),
            'gender': 'male',
            'identity_verified': True,
        })

        cls.patient_unverified = cls.env['clinic.patient'].create({
            'name': 'Patient Non Vérifié',
            'birthdate': datetime.date(1990, 1, 1),
            'gender': 'female',
            'identity_verified': False,
        })

    def _make_appointment(self, patient, **vals):
        start = vals.pop('date_start', datetime.datetime(2026, 12, 1, 9, 0))
        stop = vals.pop('date_stop', start + datetime.timedelta(hours=1))
        defaults = {
            'patient_id': patient.id,
            'doctor_id': self.doctor.id,
            'service': 'Consultation',
            'date_start': start,
            'date_stop': stop,
            'booking_channel': 'phone',
            'status': 'confirmed',
        }
        defaults.update(vals)
        return self.Appointment.create(defaults)

    # ----------------------------------------------------------
    # TF-ACU-01 — Check-in requires identity verified (RG-ACU-01)
    # ----------------------------------------------------------
    def test_checkin_refused_if_identity_not_verified(self):
        appt = self._make_appointment(self.patient_unverified)
        wizard = self.env['clinic.checkin.wizard'].create({
            'appointment_id': appt.id,
        })
        with self.assertRaises(UserError):
            wizard.action_checkin()

    def test_checkin_succeeds_if_identity_verified(self):
        appt = self._make_appointment(self.patient_verified)
        wizard = self.env['clinic.checkin.wizard'].create({
            'appointment_id': appt.id,
        })
        wizard.action_checkin()

        self.assertEqual(appt.status, 'arrived')
        self.assertIsNotNone(appt.arrival_time)
        self.assertEqual(appt.arrival_user_id, self.env.user)
        self.assertTrue(appt.visit_id, "A visit should be created at check-in")

    # ----------------------------------------------------------
    # Visit auto-creation
    # ----------------------------------------------------------
    def test_checkin_creates_visit(self):
        appt = self._make_appointment(self.patient_verified)
        wizard = self.env['clinic.checkin.wizard'].create({
            'appointment_id': appt.id,
        })
        wizard.action_checkin()

        visit = appt.visit_id
        self.assertTrue(visit)
        self.assertEqual(visit.patient_id, self.patient_verified)
        self.assertEqual(visit.appointment_id, appt)
        self.assertEqual(visit.clinician_id, self.doctor)
        self.assertEqual(visit.status, 'open')
        self.assertRegex(visit.name, r'^VIS-\d{5}$')

    # ----------------------------------------------------------
    # Check-in status guard
    # ----------------------------------------------------------
    def test_checkin_refused_if_already_arrived(self):
        appt = self._make_appointment(self.patient_verified)
        wizard = self.env['clinic.checkin.wizard'].create({'appointment_id': appt.id})
        wizard.action_checkin()

        # Second attempt
        wizard2 = self.env['clinic.checkin.wizard'].create({'appointment_id': appt.id})
        with self.assertRaises(UserError):
            wizard2.action_checkin()

    def test_checkin_refused_if_cancelled(self):
        appt = self._make_appointment(self.patient_verified, status='cancelled')
        wizard = self.env['clinic.checkin.wizard'].create({'appointment_id': appt.id})
        with self.assertRaises(UserError):
            wizard.action_checkin()

    # ----------------------------------------------------------
    # TF-ACU-02 — Queue view has no clinical data
    # ----------------------------------------------------------
    def test_queue_view_has_no_clinical_fields(self):
        """RG-ACU-02 / RG-ACU-04: queue view must NOT display clinical fields."""
        view = self.env.ref('gestion_clinique.view_clinic_appointment_queue_list')
        arch = view.arch_db or ''
        forbidden = ['clinical_notes', 'allergies', 'blood_group',
                     'chronic_conditions', 'current_medications']
        for field in forbidden:
            self.assertNotIn(
                field, arch,
                f"Queue view must not display '{field}' (RG-ACU-02/04)"
            )

    # ----------------------------------------------------------
    # Late detection (RG-ACU-03 param-driven)
    # ----------------------------------------------------------
    def test_late_detection_uses_config_tolerance(self):
        # Set tolerance to 5 min via config parameter
        self.env['ir.config_parameter'].sudo().set_param(
            'gestion_clinique.delay_tolerance', '5'
        )
        # Appointment scheduled 20 minutes ago (should be late)
        past_start = datetime.datetime.now() - datetime.timedelta(minutes=20)
        past_stop = past_start + datetime.timedelta(hours=1)
        appt = self._make_appointment(
            self.patient_verified,
            date_start=past_start,
            date_stop=past_stop,
        )
        wizard = self.env['clinic.checkin.wizard'].create({'appointment_id': appt.id})
        self.assertTrue(wizard.is_late)
        self.assertGreater(wizard.late_minutes, 5)
        self.assertEqual(wizard.delay_tolerance, 5)