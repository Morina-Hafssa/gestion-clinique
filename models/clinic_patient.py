# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import re
import unicodedata


class ClinicPatient(models.Model):
    _name = 'clinic.patient'
    _description = 'Dossier Patient'
    _inherit = ['mail.thread.cc']  
    _order = 'patient_identifier desc'
    _rec_name = 'patient_identifier'
    _parent_store = False

    # ============================================================
    # IDENTIFICATION
    # ============================================================
    patient_identifier = fields.Char(
        string="Identifiant Patient",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau'),
        tracking=True,
        index=True,
        help="Identifiant unique auto-généré (ex: PAT-00001)"
    )

    medical_record_number = fields.Char(
        string="Numéro de dossier médical",
        copy=False,
        readonly=True,
        tracking=True,
        help="Numéro externe du dossier (optionnel, si la clinique en utilise un autre)"
    )

    partner_id = fields.Many2one(
        'res.partner',
        string="Contact associé",
        ondelete='restrict',
        tracking=True,
        index=True,
        copy=False,
    )

    # Champs dénormalisés pour recherche rapide
    name = fields.Char(
        related='partner_id.name',
        string="Nom complet",
        store=True,
        readonly=False,
        required=True,
        tracking=True,
    )
    phone = fields.Char(
        related='partner_id.phone',
        string="Téléphone",
        store=True,
        readonly=False,
        tracking=True,
    )
    mobile = fields.Char(
        related='partner_id.mobile',
        string="Mobile",
        store=True,
        readonly=False,
    )
    email = fields.Char(
        related='partner_id.email',
        string="Email",
        store=True,
        readonly=False,
    )
    street = fields.Char(
        related='partner_id.street',
        string="Adresse",
        readonly=False,
    )
    street2 = fields.Char(
        related='partner_id.street2',
        string="Complément d'adresse",
        readonly=False,
    )
    city = fields.Char(
        related='partner_id.city',
        string="Ville",
        readonly=False,
    )
    zip = fields.Char(
        related='partner_id.zip',
        string="Code postal",
        readonly=False,
    )
    country_id = fields.Many2one(
        related='partner_id.country_id',
        string="Pays",
        readonly=False,
    )

    name_normalized = fields.Char(
        string="Nom normalisé",
        compute='_compute_name_normalized',
        store=True,
        index=True,
        help="Nom sans accents ni casse pour recherche anti-doublon"
    )

    birthdate = fields.Date(
        string="Date de naissance",
        required=True,
        tracking=True,
        index=True,
    )
    birthdate_estimated = fields.Boolean(
        string="Date de naissance estimée",
        help="Cocher si la date exacte est inconnue",
    )
    age = fields.Integer(
        string="Âge",
        compute='_compute_age',
        store=True,
    )
    gender = fields.Selection([
        ('male', 'Masculin'),
        ('female', 'Féminin'),
        ('other', 'Autre'),
        ('undisclosed', 'Non précisé'),
    ], string="Genre", tracking=True, required=True, default='undisclosed')

    national_id = fields.Char(
        string="Numéro d'identité nationale",
        tracking=True,
        help="Optionnel selon la juridiction"
    )
    national_id_type = fields.Selection([
        ('cin', 'CIN'),
        ('passport', 'Passeport'),
        ('carte_sejour', 'Carte de séjour'),
        ('other', 'Autre'),
    ], string="Type de pièce d'identité")

    marital_status = fields.Selection([
        ('single', 'Célibataire'),
        ('married', 'Marié(e)'),
        ('divorced', 'Divorcé(e)'),
        ('widowed', 'Veuf/Veuve'),
        ('other', 'Autre'),
    ], string="Situation familiale")

    occupation = fields.Char(string="Profession")
    preferred_language = fields.Selection([
        ('fr', 'Français'),
        ('ar', 'Arabe'),
        ('en', 'Anglais'),
        ('es', 'Espagnol'),
        ('other', 'Autre'),
    ], string="Langue préférée", default='fr')

    # ============================================================
    # CONTACT D'URGENCE
    # ============================================================
    emergency_contact_name = fields.Char(string="Contact d'urgence - Nom")
    emergency_contact_phone = fields.Char(string="Contact d'urgence - Téléphone")
    emergency_contact_relation = fields.Char(
        string="Contact d'urgence - Relation",
        help="Ex: conjoint, parent, ami"
    )

    # ============================================================
    # ASSURANCE
    # ============================================================
    insurance_provider_id = fields.Many2one(
        'res.partner',
        string="Assureur",
        domain=[('is_company', '=', True)],
    )
    insurance_number = fields.Char(string="Numéro d'assurance")
    insurance_valid_until = fields.Date(string="Valide jusqu'au")
    insurance_coverage_percent = fields.Float(
        string="Taux de couverture (%)",
        help="Pourcentage pris en charge par l'assureur",
    )

    # ============================================================
    # CONSENTEMENT & CONFIDENTIALITÉ
    # ============================================================
    privacy_notice_acknowledged = fields.Boolean(
        string="Notice de confidentialité acceptée",
        tracking=True,
    )
    privacy_notice_date = fields.Datetime(
        string="Date d'acceptation",
        tracking=True,
    )
    consent_document_ids = fields.Many2many(
        'ir.attachment',
        'clinic_patient_consent_rel',
        'patient_id',
        'attachment_id',
        string="Documents de consentement",
    )
    consent_ids = fields.One2many(
        'clinic.patient.consent',
        'patient_id',
        string="Consentements",
    )

    # ============================================================
    # IDENTITOVIGILANCE
    # ============================================================
    identity_verified = fields.Boolean(
        string="Identité vérifiée",
        default=False,
        tracking=True,
        readonly=True,
        copy=False,
    )
    identity_verified_by_id = fields.Many2one(
        'res.users',
        string="Vérifiée par",
        readonly=True,
        tracking=True,
        copy=False,
    )
    identity_verified_at = fields.Datetime(
        string="Vérifiée le",
        readonly=True,
        tracking=True,
        copy=False,
    )

    # ============================================================
    # STATUT & MÉTADONNÉES
    # ============================================================
    is_new_patient = fields.Boolean(
        string="Nouveau patient",
        compute='_compute_is_new_patient',
        store=True,
    )
    active = fields.Boolean(string="Actif", default=True)
    notes = fields.Text(
        string="Notes administratives",
        help="Notes visibles par la réception (non cliniques)"
    )
    tags_ids = fields.Many2many(
        'res.partner.category',
        'clinic_patient_tag_rel',
        'patient_id',
        'tag_id',
        string="Étiquettes",
    )

    # ============================================================
    # CHAMPS CLINIQUES (ACCÈS RESTREINT)
    # ============================================================
    blood_group = fields.Selection([
        ('a+', 'A+'), ('a-', 'A-'),
        ('b+', 'B+'), ('b-', 'B-'),
        ('ab+', 'AB+'), ('ab-', 'AB-'),
        ('o+', 'O+'), ('o-', 'O-'),
    ], string="Groupe sanguin",
       groups='gestion_clinique.group_clinic_medecin,gestion_clinique.group_clinic_infermier')

    allergies = fields.Text(
        string="Allergies connues",
        groups='gestion_clinique.group_clinic_medecin,gestion_clinique.group_clinic_infermier',
    )
    clinical_notes = fields.Text(
        string="Notes cliniques",
        groups='gestion_clinique.group_clinic_medecin,gestion_clinique.group_clinic_infermier',
    )
    chronic_conditions = fields.Text(
        string="Maladies chroniques",
        groups='gestion_clinique.group_clinic_medecin,gestion_clinique.group_clinic_infermier',
    )
    current_medications = fields.Text(
        string="Médicaments en cours",
        groups='gestion_clinique.group_clinic_medecin,gestion_clinique.group_clinic_infermier',
    )

    # ============================================================
    # CHAMPS CALCULÉS / TECHNIQUES
    # ============================================================
    full_display_name = fields.Char(
        string="Nom complet affiché",
        compute='_compute_full_display_name',
        store=True,
    )

    # ============================================================
    # CONTRAINTES SQL
    # ============================================================
    _sql_constraints = [
        ('patient_identifier_uniq', 'unique(patient_identifier)',
         "L'identifiant patient doit être unique."),
        ('national_id_uniq_per_type', 'unique(national_id, national_id_type)',
         "Ce numéro de pièce d'identité existe déjà pour ce type."),
    ]

    # ============================================================
    # MÉTHODES COMPUTE
    # ============================================================
    @api.depends('partner_id.name')
    def _compute_name_normalized(self):
        for record in self:
            if record.partner_id.name:
                nfkd = unicodedata.normalize('NFKD', record.partner_id.name)
                normalized = ''.join(c for c in nfkd if not unicodedata.combining(c))
                record.name_normalized = re.sub(r'\s+', '', normalized.lower())
            else:
                record.name_normalized = False

    @api.depends('birthdate')
    def _compute_age(self):
        today = fields.Date.today()
        for record in self:
            if record.birthdate:
                record.age = today.year - record.birthdate.year - (
                    (today.month, today.day) < (record.birthdate.month, record.birthdate.day)
                )
            else:
                record.age = 0

    @api.depends('create_date')
    def _compute_is_new_patient(self):
        for record in self:
            if record.create_date:
                delta = fields.Datetime.now() - record.create_date
                record.is_new_patient = delta.days < 7
            else:
                record.is_new_patient = False

    @api.depends('patient_identifier', 'name')
    def _compute_full_display_name(self):
        for record in self:
            record.full_display_name = f"{record.patient_identifier} - {record.name or ''}"

    # ============================================================
    # CONTRAINTES PYTHON
    # ============================================================
    @api.constrains('birthdate')
    def _check_birthdate_in_past(self):
        today = fields.Date.today()
        for record in self:
            if record.birthdate and record.birthdate > today:
                raise ValidationError(_("La date de naissance ne peut pas être dans le futur."))

    @api.constrains('name_normalized', 'birthdate')
    def _check_duplicate_patient(self):
        """Bloque la création si un doublon exact existe."""
        for record in self:
            if not record.name_normalized or not record.birthdate:
                continue
            duplicates = self.with_context(active_test=False).search([
                ('id', '!=', record.id),
                ('name_normalized', '=', record.name_normalized),
                ('birthdate', '=', record.birthdate),
            ], limit=1)
            if duplicates:
                raise ValidationError(_(
                    "Un patient avec le même nom et la même date de naissance existe déjà : %s (%s).\n"
                    "Veuillez utiliser la recherche anti-doublon ou fusionner les dossiers."
                ) % (duplicates.patient_identifier, duplicates.name))

    # ============================================================
    # CRUD
    # ============================================================
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('patient_identifier', _('Nouveau')) == _('Nouveau'):
                vals['patient_identifier'] = self.env['ir.sequence'].next_by_code(
                    'clinic.patient'
                ) or _('PAT-ERREUR')

            if not vals.get('partner_id'):
                partner_vals = {
                    'name': vals.get('name', _('Patient inconnu')),
                    'phone': vals.get('phone'),
                    'mobile': vals.get('mobile'),
                    'email': vals.get('email'),
                    'street': vals.get('street'),
                    'street2': vals.get('street2'),
                    'city': vals.get('city'),
                    'zip': vals.get('zip'),
                    'country_id': vals.get('country_id'),
                    'is_company': False,
                    
                }
                partner = self.env['res.partner'].create(partner_vals)
                vals['partner_id'] = partner.id

        return super().create(vals_list)

    def write(self, vals):
        partner_fields = ['name', 'phone', 'mobile', 'email', 'street', 'street2',
                          'city', 'zip', 'country_id']
        if any(f in vals for f in partner_fields):
            for record in self:
                partner_vals = {f: vals[f] for f in partner_fields if f in vals}
                if partner_vals and record.partner_id:
                    record.partner_id.write(partner_vals)

        # Gestion identité vérifiée
        if vals.get('identity_verified') and not any(r.identity_verified for r in self):
            vals['identity_verified_by_id'] = self.env.user.id
            vals['identity_verified_at'] = fields.Datetime.now()

        return super().write(vals)

    # ============================================================
    # ACTIONS MÉTIER
    # ============================================================
    def action_verify_identity(self):
        for record in self:
            if record.identity_verified:
                raise UserError(_("L'identité de ce patient est déjà vérifiée."))
            record.write({
                'identity_verified': True,
                'identity_verified_by_id': self.env.user.id,
                'identity_verified_at': fields.Datetime.now(),
            })
            record.message_post(
                body=_("Identité vérifiée par %s.") % self.env.user.name,
                subtype_xmlid='mail.mt_note',
            )
        return True

    def action_acknowledge_privacy(self):
        for record in self:
            record.write({
                'privacy_notice_acknowledged': True,
                'privacy_notice_date': fields.Datetime.now(),
            })
            record.message_post(
                body=_("Notice de confidentialité acceptée par le patient."),
                subtype_xmlid='mail.mt_note',
            )
        return True

    def action_open_merge_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'clinic.patient.merge.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_source_patient_id': self.id},
        }

    # ============================================================
    # RECHERCHE ANTI-DOUBLON
    # ============================================================
    @api.model
    def search_duplicates(self, name, birthdate=None, phone=None, limit=10):
        domain = [('active', 'in', [True, False])]
        if name:
            nfkd = unicodedata.normalize('NFKD', name)
            normalized = ''.join(c for c in nfkd if not unicodedata.combining(c))
            normalized = re.sub(r'\s+', '', normalized.lower())
            domain.append(('name_normalized', 'ilike', normalized))
        if birthdate:
            domain.append(('birthdate', '=', birthdate))
        if phone:
            domain.append(('phone', 'ilike', phone))

        patients = self.with_context(active_test=False).search(domain, limit=limit)
        return [{
            'id': p.id,
            'patient_identifier': p.patient_identifier,
            'name': p.name,
            'birthdate': p.birthdate,
            'phone': p.phone,
            'identity_verified': p.identity_verified,
            'active': p.active,
        } for p in patients]