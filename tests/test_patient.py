# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError, UserError
import datetime


@tagged('post_install', '-at_install')
class TestClinicPatient(TransactionCase):
    """Tests unitaires pour clinic.patient (TF-PAT-01, TF-PAT-02)"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Patient = cls.env['clinic.patient']
        cls.Consent = cls.env['clinic.patient.consent']

    def _create_patient(self, **vals):
        defaults = {
            'name': 'Ahmed Benali',
            'birthdate': datetime.date(1985, 3, 15),
            'gender': 'male',
            'phone': '+212600000001',
        }
        defaults.update(vals)
        return self.Patient.create(defaults)

    # ----------------------------------------------------------
    # TF-PAT-01 — Créer un patient avec identifiant unique
    # ----------------------------------------------------------
    def test_patient_created_with_unique_identifier(self):
        p = self._create_patient()
        self.assertTrue(p.patient_identifier)
        self.assertNotEqual(p.patient_identifier, 'Nouveau')
        self.assertRegex(p.patient_identifier, r'^PAT-\d{5}$')

    def test_identifiers_are_sequential(self):
        p1 = self._create_patient(name='Patient A', birthdate=datetime.date(1990, 1, 1))
        p2 = self._create_patient(name='Patient B', birthdate=datetime.date(1991, 1, 1))
        self.assertNotEqual(p1.patient_identifier, p2.patient_identifier)

    def test_partner_auto_created(self):
        p = self._create_patient()
        self.assertTrue(p.partner_id)
        self.assertEqual(p.partner_id.name, 'Ahmed Benali')
        self.assertEqual(p.partner_id.phone, '+212600000001')

    # ----------------------------------------------------------
    # RG-PAT-02 / TF-PAT-02 — Doublon bloqué
    # ----------------------------------------------------------
    def test_duplicate_patient_blocked(self):
        self._create_patient(name='Fatima Zahra', birthdate=datetime.date(1985, 3, 15))
        with self.assertRaises(UserError):
            self._create_patient(name='Fatima Zahra', birthdate=datetime.date(1985, 3, 15))

    def test_duplicate_with_accents_normalized(self):
        self._create_patient(name='Fatima Zahra', birthdate=datetime.date(1985, 3, 15))
        with self.assertRaises(UserError):
            self._create_patient(name='Fátima  Zahra', birthdate=datetime.date(1985, 3, 15))

    def test_different_birthdate_not_duplicate(self):
        self._create_patient(name='Fatima Zahra', birthdate=datetime.date(1985, 3, 15))
        p2 = self._create_patient(name='Fatima Zahra', birthdate=datetime.date(1986, 3, 15))
        self.assertTrue(p2.id)

    # ----------------------------------------------------------
    # Birthdate validation
    # ----------------------------------------------------------
    def test_future_birthdate_refused(self):
        future = datetime.date.today() + datetime.timedelta(days=1)
        with self.assertRaises(UserError):
            self._create_patient(name='Future Patient', birthdate=future)

    # ----------------------------------------------------------
    # RG-PAT-03 — Identifiant non réutilisable
    # ----------------------------------------------------------
    def test_identifier_sql_unique(self):
        p = self._create_patient()
        with self.assertRaises(Exception):
            self._create_patient(
                name='Autre Patient',
                birthdate=datetime.date(2000, 1, 1),
                patient_identifier=p.patient_identifier,
            )

    # ----------------------------------------------------------
    # RG-PAT-01 — Identity verification
    # ----------------------------------------------------------
    def test_action_verify_identity(self):
        p = self._create_patient()
        self.assertFalse(p.identity_verified)
        p.action_verify_identity()
        self.assertTrue(p.identity_verified)
        self.assertEqual(p.identity_verified_by_id, self.env.user)
        self.assertIsNotNone(p.identity_verified_at)

    def test_verify_identity_twice_raises(self):
        p = self._create_patient()
        p.action_verify_identity()
        with self.assertRaises(UserError):
            p.action_verify_identity()

    # ----------------------------------------------------------
    # Privacy acknowledgement
    # ----------------------------------------------------------
    def test_action_acknowledge_privacy(self):
        p = self._create_patient()
        self.assertFalse(p.privacy_notice_acknowledged)
        p.action_acknowledge_privacy()
        self.assertTrue(p.privacy_notice_acknowledged)
        self.assertIsNotNone(p.privacy_notice_date)

    # ----------------------------------------------------------
    # Consent model
    # ----------------------------------------------------------
    def test_consent_creates_chatter_message(self):
        p = self._create_patient()
        before = len(p.message_ids)
        self.Consent.create({
            'patient_id': p.id,
            'consent_type': 'general_care',
            'consent_given': True,
        })
        p.invalidate_recordset(['message_ids'])
        self.assertGreater(len(p.message_ids), before)

    def test_consent_withdraw(self):
        p = self._create_patient()
        consent = self.Consent.create({
            'patient_id': p.id,
            'consent_type': 'surgery',
            'consent_given': True,
        })
        consent.action_withdraw()
        self.assertTrue(consent.consent_withdrawn)
        self.assertFalse(consent.consent_given)
        self.assertIsNotNone(consent.withdrawal_date)

    def test_consent_requires_patient(self):
        with self.assertRaises(Exception):
            self.Consent.create({
                'consent_type': 'general_care',
                'consent_given': True,
            })

    # ----------------------------------------------------------
    # RG-PAT-04 — Merge wizard
    # ----------------------------------------------------------
    def test_merge_wizard_archives_source(self):
        source = self._create_patient(name='Source P', birthdate=datetime.date(1990, 1, 1))
        target = self._create_patient(name='Target P', birthdate=datetime.date(1990, 2, 2))
        wizard = self.env['clinic.patient.merge.wizard'].create({
            'source_patient_id': source.id,
            'target_patient_id': target.id,
            'merge_reason': 'Doublon détecté',
            'confirm_merge': True,
        })
        wizard.action_merge()
        self.assertFalse(source.active)
        self.assertTrue(target.active)
        self.assertIn('FUSIONNÉ', source.notes)

    def test_merge_wizard_same_patient_refused(self):
        p = self._create_patient()
        with self.assertRaises(UserError):
            self.env['clinic.patient.merge.wizard'].create({
                'source_patient_id': p.id,
                'target_patient_id': p.id,
                'merge_reason': 'Erreur',
                'confirm_merge': True,
            })

    def test_merge_wizard_requires_confirmation(self):
        source = self._create_patient(name='A', birthdate=datetime.date(1990, 1, 1))
        target = self._create_patient(name='B', birthdate=datetime.date(1990, 2, 2))
        wizard = self.env['clinic.patient.merge.wizard'].create({
            'source_patient_id': source.id,
            'target_patient_id': target.id,
            'merge_reason': 'Doublon',
            'confirm_merge': False,
        })
        with self.assertRaises(UserError):
            wizard.action_merge()

    # ----------------------------------------------------------
    # RG-PAT-02 — search_duplicates helper
    # ----------------------------------------------------------
    def test_search_duplicates_finds_match(self):
        self._create_patient(name='Hassan Alami', birthdate=datetime.date(1975, 5, 5))
        results = self.Patient.search_duplicates(
            name='Hassan Alami',
            birthdate=datetime.date(1975, 5, 5),
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], 'Hassan Alami')

    def test_search_duplicates_empty(self):
        results = self.Patient.search_duplicates(name='Nobody Has This Name')
        self.assertEqual(len(results), 0)

    # ----------------------------------------------------------
    # Computed fields
    # ----------------------------------------------------------
    def test_name_normalized_strips_accents(self):
        p = self._create_patient(name='Éléonore Dubois', birthdate=datetime.date(1990, 1, 1))
        self.assertEqual(p.name_normalized, 'eleonoredubois')

    def test_age_computation(self):
        p = self._create_patient(birthdate=datetime.date(2000, 1, 1))
        expected = datetime.date.today().year - 2000
        today = datetime.date.today()
        if (today.month, today.day) < (1, 1):
            expected -= 1
        self.assertEqual(p.age, expected)

    def test_is_new_patient(self):
        p = self._create_patient()
        self.assertTrue(p.is_new_patient)