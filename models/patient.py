from odoo import models, fields

class GestionCliniquePatient(models.Model):
    _name = 'gestion.clinique.patient'
    _description = 'Patient'
    _rec_name = 'name'

    name = fields.Char(string='Full Name', required=True)
    birth_date = fields.Date(string='Birth Date')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string='Gender')
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    notes = fields.Text(string='Notes')