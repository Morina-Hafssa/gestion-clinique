# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import AccessError
import datetime


@tagged('post_install', '-at_install')
class TestClinicPatientPermissions(TransactionCase):
    """Tests des permissions par groupe (TP-01, TP-02, TP-03, TP-08)"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        def _make_user(name, group_xmlid):
            return cls.env['res.users'].create({
                'name': name,
                'login': name.lower().replace(' ', '_'),
                'email': f'{name.lower().replace(" ", ".")}@test.com',
                'groups_id': [(6, 0, [
                    cls.env.ref('base.group_user').id,
                    cls.env.ref(group_xmlid).id,
                ])],
            })

        cls.user_reception = _make_user('Reception', 'gestion_clinique.group_clinic_reception')
        cls.user_medecin = _make_user('Medecin', 'gestion_clinique.group_clinic_medecin')
        cls.user_caissier = _make_user('Caissier', 'gestion_clinique.group_clinic_caisse')
        cls.user_manager = _make_user('Manager', 'gestion_clinique.group_clinic_manager')

        cls.patient = cls.env['clinic.patient'].create({
            'name': 'Test Patient',
            'birthdate': datetime.date(1980, 1, 1),
            'gender': 'male',
            'clinical_notes': 'Secret clinical info',
        })

    # ----------------------------------------------------------
    # TP-01 — Réception ne peut pas lire les notes cliniques
    # ----------------------------------------------------------
    def test_reception_cannot_read_clinical_notes(self):
        patient = self.patient.with_user(self.user_reception)
        with self.assertRaises(AccessError):
            patient.read(['clinical_notes'])

    # ----------------------------------------------------------
    # TP-02 — Réception peut lire l'identité
    # ----------------------------------------------------------
    def test_reception_can_read_identity(self):
        patient = self.patient.with_user(self.user_reception)
        data = patient.read(['name', 'phone', 'birthdate', 'patient_identifier'])
        self.assertEqual(data[0]['name'], 'Test Patient')

    # ----------------------------------------------------------
    # TP-03 — Réception ne peut pas modifier les notes cliniques
    # ----------------------------------------------------------
    def test_reception_cannot_write_clinical_notes(self):
        patient = self.patient.with_user(self.user_reception)
        with self.assertRaises(AccessError):
            patient.write({'clinical_notes': 'Hacked'})

    # ----------------------------------------------------------
    # TP-08 — Manager ne peut pas modifier une note clinique
    # ----------------------------------------------------------
    def test_manager_cannot_write_clinical_notes(self):
        patient = self.patient.with_user(self.user_manager)
        with self.assertRaises(AccessError):
            patient.write({'clinical_notes': 'Manager hack'})

    # ----------------------------------------------------------
    # Médecin peut écrire les notes cliniques
    # ----------------------------------------------------------
    def test_medecin_can_write_clinical_notes(self):
        patient = self.patient.with_user(self.user_medecin)
        patient.write({'clinical_notes': 'Updated by doctor'})
        self.assertEqual(patient.clinical_notes, 'Updated by doctor')

    # ----------------------------------------------------------
    # Caissier : lecture seule
    # ----------------------------------------------------------
    def test_caissier_can_read_not_write(self):
        patient = self.patient.with_user(self.user_caissier)
        patient.read(['name'])
        with self.assertRaises(AccessError):
            patient.write({'name': 'Hacked'})

    # ----------------------------------------------------------
    # Réception peut créer
    # ----------------------------------------------------------
    def test_reception_can_create_patient(self):
        p = self.env['clinic.patient'].with_user(self.user_reception).create({
            'name': 'Nouveau Patient',
            'birthdate': datetime.date(1995, 5, 5),
            'gender': 'female',
        })
        self.assertTrue(p.id)