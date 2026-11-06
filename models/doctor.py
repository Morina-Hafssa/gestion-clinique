from odoo import models, fields

class GestionCliniqueDoctor(models.Model):
    _name = 'gestion.clinique.doctor'
    _description = 'Doctor'
    _rec_name = 'name'

    name = fields.Char(string='Full Name', required=True)
    specialty = fields.Char(string='Specialty')
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')