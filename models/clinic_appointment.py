# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta


class ClinicAppointment(models.Model):
    _name = 'clinic.appointment'
    _description = 'Rendez-vous Clinique'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'
    _rec_name = 'display_name'

    # ============================================================
    # IDENTIFICATION
    # ============================================================
    name = fields.Char(
        string="Référence RDV",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau'),
        tracking=True,
        index=True,
    )

    patient_id = fields.Many2one(
        'clinic.patient',
        string="Patient",
        required=True,
        ondelete='restrict',
        tracking=True,
        index=True,
    )

    # [HYPOTHÈSE PV-22] Médecin = res.users avec groupe medecin
    # Sera lié à clinic.doctor quand feature/medecin sera mergée
    doctor_id = fields.Many2one(
        'res.users',
        string="Médecin",
        required=True,
        ondelete='restrict',
        tracking=True,
        index=True,
        domain=[('share', '=', False)],
        help="[HYPOTHÈSE PV-22] Utilisateur avec groupe Médecin. "
             "Sera lié à clinic.doctor quand disponible."
    )

    service = fields.Char(
        string="Service",
        required=True,
        tracking=True,
        help="Motif du rendez-vous (ex: consultation générale, suivi, urgence)"
    )

    # ============================================================
    # PLANIFICATION
    # ============================================================
    date_start = fields.Datetime(
        string="Date et heure de début",
        required=True,
        tracking=True,
        index=True,
    )
    date_stop = fields.Datetime(
        string="Date et heure de fin",
        required=True,
        tracking=True,
    )
    duration = fields.Float(
        string="Durée (heures)",
        compute='_compute_duration',
        inverse='_inverse_duration',
        store=True,
        help="Calculée depuis date_start et date_stop"
    )

    room = fields.Char(
        string="Salle",
        tracking=True,
        help="Numéro ou nom de la salle (optionnel)"
    )

    # ============================================================
    # STATUTS (RG-RDV-05 — 9 états)
    # ============================================================
    status = fields.Selection([
        ('draft', 'Brouillon/Demandé'),
        ('booked', 'Réservé'),
        ('confirmed', 'Confirmé'),
        ('arrived', 'Arrivé'),
        ('in_progress', 'En cours'),
        ('done', 'Terminé'),
        ('cancelled', 'Annulé'),
        ('no_show', 'Absent'),
        ('rescheduled', 'Reprogrammé'),
    ], string="Statut",
       default='draft',
       required=True,
       tracking=True,
       index=True,
       copy=False,
    )

    # ============================================================
    # CANAL DE RÉSERVATION (PV-04 — générique)
    # ============================================================
    booking_channel = fields.Selection([
        ('phone', 'Téléphone'),
        ('in_person', 'En personne'),
        ('web', 'Site Web'),
        ('email', 'Courriel'),
        ('other', 'Autre'),
    ], string="Canal de réservation",
       default='in_person',
       required=True,
       tracking=True,
    )

    # ============================================================
    # CONFIRMATION (RG-RDV-04)
    # ============================================================
    confirmation_sent = fields.Boolean(
        string="Confirmation envoyée",
        default=False,
        tracking=True,
        copy=False,
    )
    confirmation_channel = fields.Selection([
        ('phone', 'Téléphone'),
        ('email', 'Courriel'),
        ('sms', 'SMS'),
        ('in_person', 'En personne'),
    ], string="Canal de confirmation", tracking=True, copy=False)

    confirmation_date = fields.Datetime(
        string="Date de confirmation",
        tracking=True,
        copy=False,
    )
    confirmation_user_id = fields.Many2one(
        'res.users',
        string="Confirmé par",
        tracking=True,
        copy=False,
    )

    # ============================================================
    # ANNULATION (RG-RDV-03)
    # ============================================================
    cancel_reason = fields.Text(
        string="Motif d'annulation",
        tracking=True,
        copy=False,
    )
    cancel_date = fields.Datetime(
        string="Date d'annulation",
        tracking=True,
        copy=False,
    )
    cancel_user_id = fields.Many2one(
        'res.users',
        string="Annulé par",
        tracking=True,
        copy=False,
    )

    # ============================================================
    # REPROGRAMMATION (RG-RDV-07)
    # ============================================================
    reschedule_origin_id = fields.Many2one(
        'clinic.appointment',
        string="RDV d'origine",
        ondelete='set null',
        tracking=True,
        copy=False,
        help="Si ce RDV est le résultat d'une reprogrammation"
    )
    reschedule_new_id = fields.Many2one(
        'clinic.appointment',
        string="Nouveau RDV",
        ondelete='set null',
        tracking=True,
        copy=False,
        help="Si ce RDV a été reprogrammé"
    )

    # ============================================================
    # ARRIVÉE (Accueil / Check-in)
    # ============================================================
    arrival_time = fields.Datetime(
        string="Heure d'arrivée",
        tracking=True,
        copy=False,
    )
    arrival_user_id = fields.Many2one(
        'res.users',
        string="Enregistré par",
        tracking=True,
        copy=False,
    )

    # ============================================================
    # VISITE (V_VIS)
    # ============================================================
    visit_id = fields.Many2one(
        'clinic.visit',
        string="Visite",
        ondelete='set null',
        tracking=True,
        copy=False,
        help="Visite ouverte au check-in"
    )

    # ============================================================
    # COMPUTED
    # ============================================================
    display_name = fields.Char(
        compute='_compute_display_name',
        store=True,
    )
    is_past = fields.Boolean(
        compute='_compute_is_past',
        store=True,
    )
    is_today = fields.Boolean(
        compute='_compute_is_today',
        store=True,
    )

    # ============================================================
    # SQL CONSTRAINTS
    # ============================================================
    _sql_constraints = [
        ('name_uniq', 'unique(name)', "La référence du RDV doit être unique."),
        ('dates_ordered', 'CHECK(date_stop > date_start)',
         "La date de fin doit être après la date de début."),
    ]

    # ============================================================
    # COMPUTE
    # ============================================================
    @api.depends('patient_id', 'date_start', 'doctor_id')
    def _compute_display_name(self):
        for appt in self:
            if appt.patient_id and appt.date_start:
                appt.display_name = f"{appt.name} — {appt.patient_id.name} ({appt.date_start:%Y-%m-%d %H:%M})"
            else:
                appt.display_name = appt.name or _('Nouveau')

    @api.depends('date_start', 'date_stop')
    def _compute_duration(self):
        for appt in self:
            if appt.date_start and appt.date_stop:
                delta = appt.date_stop - appt.date_start
                appt.duration = delta.total_seconds() / 3600.0
            else:
                appt.duration = 0.0

    def _inverse_duration(self):
        for appt in self:
            if appt.date_start and appt.duration:
                appt.date_stop = appt.date_start + timedelta(hours=appt.duration)

    @api.depends('date_start')
    def _compute_is_past(self):
        now = fields.Datetime.now()
        for appt in self:
            appt.is_past = bool(appt.date_start and appt.date_start < now)

    @api.depends('date_start')
    def _compute_is_today(self):
        today = fields.Date.today()
        for appt in self:
            appt.is_today = bool(appt.date_start and appt.date_start.date() == today)

    # ============================================================
    # CONSTRAINTS
    # ============================================================
    @api.constrains('date_start', 'date_stop', 'doctor_id', 'status')
    def _check_no_overlap(self):
        """RG-RDV-01: aucun créneau déjà occupé ne peut être réservé."""
        for appt in self:
            if appt.status in ('cancelled', 'no_show', 'rescheduled'):
                continue  # les annulés/absents/reprogrammés ne bloquent pas
            if not (appt.date_start and appt.date_stop and appt.doctor_id):
                continue
            overlapping = self.search([
                ('id', '!=', appt.id),
                ('doctor_id', '=', appt.doctor_id.id),
                ('status', 'not in', ['cancelled', 'no_show', 'rescheduled']),
                ('date_start', '<', appt.date_stop),
                ('date_stop', '>', appt.date_start),
            ], limit=1)
            if overlapping:
                raise ValidationError(_(
                    "Créneau déjà occupé : le médecin %s a un autre rendez-vous de %s à %s.\n"
                    "Veuillez choisir un autre créneau."
                ) % (
                    appt.doctor_id.name,
                    overlapping.date_start,
                    overlapping.date_stop,
                ))

    @api.constrains('date_start', 'date_stop', 'doctor_id')
    def _check_doctor_availability(self):
        """RG-PER-01: pas de RDV pendant un congé / absence (via resource.calendar)."""
        for appt in self:
            if not (appt.date_start and appt.date_stop and appt.doctor_id):
                continue
            # Si l'utilisateur a un employé lié avec resource_calendar, on vérifie les leaves
            employee = self.env['hr.employee'].search([('user_id', '=', appt.doctor_id.id)], limit=1)
            if employee and employee.resource_calendar_id:
                leaves = self.env['resource.calendar.leaves'].search([
                    ('calendar_id', '=', employee.resource_calendar_id.id),
                    ('date_from', '<', appt.date_stop),
                    ('date_to', '>', appt.date_start),
                ])
                if leaves:
                    raise ValidationError(_(
                        "Le médecin %s est indisponible sur ce créneau (congé/absence)."
                    ) % appt.doctor_id.name)

    # ============================================================
    # CRUD
    # ============================================================
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('clinic.appointment') or _('RDV-ERREUR')
        return super().create(vals_list)

    # ============================================================
    # ACTIONS MÉTIER
    # ============================================================
    def action_confirm(self):
        """RG-RDV-04: confirmation tracée."""
        for appt in self:
            if appt.status not in ('draft', 'booked'):
                raise UserError(_("Seul un RDV brouillon ou réservé peut être confirmé."))
            appt.write({
                'status': 'confirmed',
                'confirmation_sent': True,
                'confirmation_channel': appt.booking_channel if appt.booking_channel in ('phone', 'email') else 'in_person',
                'confirmation_date': fields.Datetime.now(),
                'confirmation_user_id': self.env.user.id,
            })
        return True

    def action_cancel(self):
        """Ouvre le wizard d'annulation."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'clinic.appointment.cancel.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_appointment_id': self.id},
        }

    def action_reschedule(self):
        """Ouvre le wizard de reprogrammation (RG-RDV-02)."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'clinic.appointment.reschedule.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_appointment_id': self.id},
        }

    def action_mark_arrived(self):
        """Marque le RDV comme arrivé (utilisé par check-in)."""
        for appt in self:
            if appt.status not in ('booked', 'confirmed'):
                raise UserError(_("Seul un RDV réservé ou confirmé peut être marqué arrivé."))
            if not appt.patient_id.identity_verified:
                raise UserError(_(
                    "L'identité du patient n'est pas vérifiée (RG-ACU-01). "
                    "Veuillez d'abord vérifier l'identité dans le dossier patient."
                ))
            appt.write({
                'status': 'arrived',
                'arrival_time': fields.Datetime.now(),
                'arrival_user_id': self.env.user.id,
            })
        return True

    def action_start(self):
        """Démarre la consultation."""
        for appt in self:
            if appt.status != 'arrived':
                raise UserError(_("Seul un RDV arrivé peut être démarré."))
            appt.status = 'in_progress'
        return True

    def action_done(self):
        for appt in self:
            if appt.status != 'in_progress':
                raise UserError(_("Seul un RDV en cours peut être terminé."))
            appt.status = 'done'
        return True

    def action_no_show(self):
        for appt in self:
            if appt.status not in ('booked', 'confirmed'):
                raise UserError(_("Seul un RDV réservé ou confirmé peut être marqué absent."))
            appt.status = 'no_show'
        return True