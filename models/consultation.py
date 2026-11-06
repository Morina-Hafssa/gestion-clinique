from odoo import models, fields

class GestionCliniqueConsultation(models.Model):
    _name = 'gestion.clinique.consultation'
    _description = 'Consultation'
    _rec_name = 'name'

    name = fields.Char(string='Reference', required=True, copy=False, default='New')
    appointment_id = fields.Many2one('gestion.clinique.appointment', string='Appointment')
    patient_id = fields.Many2one('gestion.clinique.patient', string='Patient', required=True)
    doctor_id = fields.Many2one('gestion.clinique.doctor', string='Doctor', required=True)
    diagnosis = fields.Text(string='Diagnosis')
    prescription = fields.Text(string='Prescription')
    date = fields.Datetime(string='Date', default=fields.Datetime.now)