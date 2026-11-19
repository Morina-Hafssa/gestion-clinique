# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ClinicVisit(models.Model):
    _name = 'clinic.visit'
    _description = 'Visite (épisode de soins)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'
    _rec_name = 'name'

    name = fields.Char(
        string="Référence visite",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouvelle'),
        tracking=True,
    )

    patient_id = fields.Many2one(
        'clinic.patient',
        string="Patient",
        required=True,
        ondelete='restrict',
        tracking=True,
        index=True,
    )

    appointment_id = fields.Many2one(
        'clinic.appointment',
        string="Rendez-vous d'origine",
        ondelete='set null',
        tracking=True,
        index=True,
    )

    clinician_id = fields.Many2one(
        'res.users',
        string="Clinicien responsable",
        ondelete='restrict',
        tracking=True,
        domain=[('share', '=', False)],
        help="[HYPOTHÈSE PV-22] Utilisateur avec groupe Médecin ou Infirmier."
    )

    date_start = fields.Datetime(
        string="Début",
        required=True,
        default=fields.Datetime.now,
        tracking=True,
    )
    date_stop = fields.Datetime(
        string="Fin",
        tracking=True,
        copy=False,
    )

    status = fields.Selection([
        ('open', 'Ouverte'),
        ('in_progress', 'En cours'),
        ('closed', 'Clôturée'),
        ('cancelled', 'Annulée'),
    ], string="Statut",
       default='open',
       required=True,
       tracking=True,
       index=True,
    )

    notes = fields.Text(
        string="Notes administratives",
        help="Notes non cliniques (visibles réception)"
    )

    _sql_constraints = [
        ('name_uniq', 'unique(name)', "La référence de visite doit être unique."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouvelle')) == _('Nouvelle'):
                vals['name'] = self.env['ir.sequence'].next_by_code('clinic.visit') or _('VIS-ERREUR')
        return super().create(vals_list)

    def action_close(self):
        for visit in self:
            if visit.status not in ('open', 'in_progress'):
                raise UserError(_("Seule une visite ouverte ou en cours peut être clôturée."))
            visit.write({
                'status': 'closed',
                'date_stop': fields.Datetime.now(),
            })
        return True

    def action_cancel(self):
        for visit in self:
            if visit.status == 'closed':
                raise UserError(_("Impossible d'annuler une visite clôturée."))
            visit.status = 'cancelled'
        return True