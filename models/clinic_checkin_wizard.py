# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ClinicCheckinWizard(models.TransientModel):
    _name = 'clinic.checkin.wizard'
    _description = 'Assistant de check-in (accueil)'

    appointment_id = fields.Many2one(
        'clinic.appointment',
        string="Rendez-vous",
        required=True,
        ondelete='cascade',
    )
    patient_id = fields.Many2one(
        related='appointment_id.patient_id',
        string="Patient",
        readonly=True,
    )
    identity_verified = fields.Boolean(
        related='appointment_id.patient_id.identity_verified',
        string="Identité vérifiée",
        readonly=True,
    )
    appointment_date = fields.Datetime(
        related='appointment_id.date_start',
        string="Heure prévue",
        readonly=True,
    )
    is_late = fields.Boolean(
        string="Patient en retard",
        compute='_compute_is_late',
    )
    late_minutes = fields.Integer(
        string="Retard (minutes)",
        compute='_compute_is_late',
    )
    delay_tolerance = fields.Integer(
        string="Tolérance (minutes)",
        compute='_compute_is_late',
    )

    late_action = fields.Selection([
    ('maintain', 'Maintenir le RDV'),
    ('shift', 'Décaler'),
    ('reschedule', 'Reprogrammer'),
    ], string="Action sur le retard",
    default=lambda self: self.env['ir.config_parameter'].sudo().get_param(
        'gestion_clinique.late_action', 'maintain'
    ),
    )

    notes = fields.Text(string="Notes")

    @api.depends('appointment_date')
    def _compute_is_late(self):
        from datetime import datetime
        tolerance = int(self.env['ir.config_parameter'].sudo().get_param(
            'gestion_clinique.delay_tolerance', 15
        ))
        now = fields.Datetime.now()
        for wiz in self:
            wiz.delay_tolerance = tolerance
            if wiz.appointment_date and now > wiz.appointment_date:
                delta = (now - wiz.appointment_date).total_seconds() / 60.0
                wiz.late_minutes = int(delta)
                wiz.is_late = delta > tolerance
            else:
                wiz.late_minutes = 0
                wiz.is_late = False

    def action_checkin(self):
        """Marque le patient arrivé (RG-ACU-01)."""
        self.ensure_one()

        if not self.appointment_id.patient_id.identity_verified:
            raise UserError(_(
                "L'identité du patient doit être vérifiée avant le check-in (RG-ACU-01). "
                "Veuillez d'abord vérifier l'identité dans le dossier patient."
            ))

        if self.appointment_id.status not in ('booked', 'confirmed'):
            raise UserError(_("Ce rendez-vous ne peut pas être check-in (statut : %s).") % self.appointment_id.status)

        # Créer la visite (V_VIS) si elle n'existe pas
        visit = self.env['clinic.visit'].create({
            'patient_id': self.appointment_id.patient_id.id,
            'appointment_id': self.appointment_id.id,
            'clinician_id': self.appointment_id.doctor_id.id,
            'status': 'open',
        })

        self.appointment_id.write({
            'status': 'arrived',
            'arrival_time': fields.Datetime.now(),
            'arrival_user_id': self.env.user.id,
            'visit_id': visit.id,
        })

        self.appointment_id.message_post(
            body=_("Check-in effectué par %s. Visite %s ouverte.") % (self.env.user.name, visit.name),
            subtype_xmlid='mail.mt_note',
        )

        return {'type': 'ir.actions.act_window_close'}