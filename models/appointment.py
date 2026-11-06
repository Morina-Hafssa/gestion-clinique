from odoo import models, fields

class GestionCliniqueAppointment(models.Model):
    _name = 'gestion.clinique.appointment'
    _description = 'Appointment'
    _rec_name = 'name'

    name = fields.Char(string='Reference', required=True, copy=False, default='New')
    patient_id = fields.Many2one('gestion.clinique.patient', string='Patient', required=True)
    doctor_id = fields.Many2one('gestion.clinique.doctor', string='Doctor', required=True)
    appointment_date = fields.Datetime(string='Date', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft')
    notes = fields.Text(string='Notes')