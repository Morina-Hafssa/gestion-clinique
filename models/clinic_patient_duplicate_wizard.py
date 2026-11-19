# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ClinicPatientDuplicateWizard(models.TransientModel):
    _name = 'clinic.patient.duplicate.wizard'
    _description = 'Assistant de détection de doublons'

    name = fields.Char(string="Nom recherché", required=True)
    birthdate = fields.Date(string="Date de naissance")
    phone = fields.Char(string="Téléphone")
    results = fields.Text(string="Doublons potentiels", compute='_compute_results')
    matched_patient_ids = fields.Many2many(
        'clinic.patient', string="Patients correspondants",
        compute='_compute_results',
    )

    @api.depends('name', 'birthdate', 'phone')
    def _compute_results(self):
        for wizard in self:
            if not wizard.name:
                wizard.matched_patient_ids = False
                wizard.results = _("Saisissez un nom pour lancer la recherche.")
                continue
            matches = self.env['clinic.patient'].search_duplicates(
                name=wizard.name,
                birthdate=wizard.birthdate,
                phone=wizard.phone,
                limit=20,
            )
            wizard.matched_patient_ids = [(6, 0, [m['id'] for m in matches])]
            if matches:
                wizard.results = "\n".join([
                    f"• {m['patient_identifier']} — {m['name']} ({m['birthdate'] or 'N/A'}) "
                    f"{'[ARCHIVÉ]' if not m['active'] else ''}"
                    for m in matches
                ])
            else:
                wizard.results = _("Aucun doublon trouvé. Vous pouvez créer le patient.")

    def action_open_existing(self):
        self.ensure_one()
        if not self.matched_patient_ids:
            raise UserError(_("Aucun patient sélectionné."))
        if len(self.matched_patient_ids) > 1:
            raise UserError(_("Sélectionnez un seul patient."))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'clinic.patient',
            'res_id': self.matched_patient_ids.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_create_new(self):
        """Ouvre une nouvelle fiche patient avec les données pré-remplies."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'clinic.patient',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_name': self.name,
                'default_birthdate': self.birthdate,
                'default_phone': self.phone,
            },
        }