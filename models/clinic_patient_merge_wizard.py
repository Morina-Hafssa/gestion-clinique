# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ClinicPatientMergeWizard(models.TransientModel):
    _name = 'clinic.patient.merge.wizard'
    _description = 'Assistant de fusion de patients'

    source_patient_id = fields.Many2one(
        'clinic.patient', string="Patient à fusionner (source)",
        required=True, ondelete='cascade',
    )
    target_patient_id = fields.Many2one(
        'clinic.patient', string="Patient cible (conservé)",
        required=True, ondelete='cascade',
    )
    merge_reason = fields.Text(string="Motif de la fusion", required=True)
    confirm_merge = fields.Boolean(string="Je confirme la fusion", required=True)

    @api.constrains('source_patient_id', 'target_patient_id')
    def _check_different_patients(self):
        for wizard in self:
            if wizard.source_patient_id == wizard.target_patient_id:
                raise UserError(_("Les patients source et cible doivent être différents."))
            if not wizard.target_patient_id.active:
                raise UserError(_("Le patient cible doit être actif."))

    def action_merge(self):
        self.ensure_one()
        if not self.confirm_merge:
            raise UserError(_("Veuillez confirmer la fusion."))

        source = self.source_patient_id
        target = self.target_patient_id

        # 1. Audit AVANT fusion
        target.message_post(
            body=_(
                "Fusion de dossiers : le patient <b>%s</b> (%s) a été fusionné dans ce dossier.\n"
                "Motif : %s\nEffectuée par : %s"
            ) % (source.patient_identifier, source.name, self.merge_reason, self.env.user.name),
            subtype_xmlid='mail.mt_note',
        )
        source.message_post(
            body=_(
                "Ce dossier a été fusionné dans <b>%s</b> (%s).\nMotif : %s\nEffectuée par : %s"
            ) % (target.patient_identifier, target.name, self.merge_reason, self.env.user.name),
            subtype_xmlid='mail.mt_note',
        )

        # 2. Transférer consentements
        source.consent_ids.write({'patient_id': target.id})
        if source.consent_document_ids:
            target.write({'consent_document_ids': [(4, doc.id) for doc in source.consent_document_ids]})

        # 3. Rediriger les relations (à étendre quand les modèles existent)
        related_models = [
            ('clinic.appointment', 'patient_id'),
            ('clinic.consultation', 'patient_id'),
            ('clinic.test.order', 'patient_id'),
            ('clinic.prescription', 'patient_id'),
            ('clinic.referral', 'patient_id'),
            ('clinic.followup', 'patient_id'),
            ('clinic.incident', 'patient_id'),
            ('account.move', 'clinic_patient_id'),
        ]
        for model_name, field_name in related_models:
            if model_name in self.env and field_name in self.env[model_name]._fields:
                try:
                    recs = self.env[model_name].search([(field_name, '=', source.id)])
                    if recs:
                        recs.write({field_name: target.id})
                except Exception:
                    pass  # modèle pas encore prêt, ignorer

        # 4. Archiver source (jamais supprimer)
        source.write({
            'active': False,
            'notes': (source.notes or '') + _(
                "\n\n[FUSIONNÉ dans %s le %s par %s]"
            ) % (target.patient_identifier, fields.Datetime.now(), self.env.user.name),
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'clinic.patient',
            'res_id': target.id,
            'view_mode': 'form',
            'target': 'current',
        }