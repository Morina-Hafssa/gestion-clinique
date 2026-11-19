# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ClinicPatientConsent(models.Model):
    _name = 'clinic.patient.consent'
    _description = 'Consentement Patient'
    _inherit = ['mail.thread']
    _order = 'consent_date desc'

    patient_id = fields.Many2one(
        'clinic.patient',
        string="Patient",
        required=True,
        ondelete='cascade',
        index=True,
    )
    consent_type = fields.Selection([
        ('general_care', 'Soins généraux'),
        ('data_processing', 'Traitement des données personnelles'),
        ('data_sharing', 'Partage des données'),
        ('surgery', 'Intervention chirurgicale'),
        ('anesthesia', 'Anesthésie'),
        ('transfusion', 'Transfusion sanguine'),
        ('research', 'Recherche'),
        ('photography', 'Photographie / Enregistrement'),
        ('other', 'Autre'),
    ], string="Type de consentement", required=True, tracking=True)

    consent_date = fields.Datetime(
        string="Date du consentement",
        required=True,
        default=fields.Datetime.now,
        tracking=True,
    )
    consent_given = fields.Boolean(
        string="Consentement donné",
        required=True,
        default=True,
        tracking=True,
    )
    consent_withdrawn = fields.Boolean(
        string="Consentement retiré",
        default=False,
        tracking=True,
    )
    withdrawal_date = fields.Datetime(
        string="Date de retrait",
        tracking=True,
    )
    withdrawal_reason = fields.Text(
        string="Motif du retrait",
        tracking=True,
    )

    document = fields.Binary(string="Document signé", attachment=True)
    document_filename = fields.Char(string="Nom du document")
    witness_name = fields.Char(string="Nom du témoin")
    notes = fields.Text(string="Notes")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record.patient_id.message_post(
                body=_("Consentement '%s' %s le %s.") % (
                    dict(self._fields['consent_type'].selection).get(record.consent_type),
                    _('donné') if record.consent_given else _('refusé'),
                    record.consent_date,
                ),
                subtype_xmlid='mail.mt_note',
            )
        return records

    def action_withdraw(self):
        for record in self:
            record.write({
                'consent_withdrawn': True,
                'withdrawal_date': fields.Datetime.now(),
                'consent_given': False,
            })
        return True