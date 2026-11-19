# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ============================================================
    # PARAMÈTRES GÉNÉRAUX (RG-GEN-10, RG-ACC-04)
    # ============================================================

    clinic_delay_tolerance = fields.Integer(
        string="Délai de tolérance de retard (min)",
        config_parameter='gestion_clinique.delay_tolerance',
        default=15,
        help="Minutes après lesquelles un patient est considéré en retard (RG-ACU-03)."
    )

    clinic_appointment_margin = fields.Integer(
        string="Marge entre rendez-vous (min)",
        config_parameter='gestion_clinique.appointment_margin',
        default=10,
        help="Temps tampon entre deux rendez-vous (RG-RDV-06)."
    )

    clinic_followup_delay = fields.Integer(
        string="Délai de relance des suivis (jours)",
        config_parameter='gestion_clinique.followup_delay',
        default=7,
        help="Nombre de jours avant qu'une tâche de suivi soit relancée (RG-SUI-03)."
    )

    # ============================================================
    # [HYPOTHÈSE PV-27] Politique de retard paramétrable
    # ============================================================
    clinic_late_action = fields.Selection([
        ('maintain', 'Maintenir le RDV'),
        ('shift', 'Décaler'),
        ('reschedule', 'Reprogrammer'),
    ], string="Action par défaut (patient en retard)",
        config_parameter='gestion_clinique.late_action',
        default='maintain',
        help="Comportement par défaut proposé par le wizard de check-in (RG-ACU-03)."
    )

    # ============================================================
    # MODULE CONDITIONNEL (RG-PHA-01)
    # ============================================================
    clinic_pharmacy_enabled = fields.Boolean(
        string="Activer le module Pharmacie",
        config_parameter='gestion_clinique.pharmacy_enabled',
        default=False,
        help="Activer uniquement si la clinique exploite une pharmacie interne."
    )