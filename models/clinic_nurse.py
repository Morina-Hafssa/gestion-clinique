from odoo import fields, models


class ClinicNurse(models.Model):
    _name = 'clinic.nurse'
    _description = 'Infirmier de la clinique'
    _order = 'name'

    name = fields.Char(string='Nom complet', required=True)
    user_id = fields.Many2one('res.users', string='Utilisateur Odoo', ondelete='restrict')
    service = fields.Char(string='Service')
    license_number = fields.Char(string="N° professionnel")
    phone = fields.Char(string='Téléphone')
    email = fields.Char(string='Email')
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('user_unique', 'unique(user_id)',
         'Cet utilisateur est déjà lié à un infirmier.'),
    ]