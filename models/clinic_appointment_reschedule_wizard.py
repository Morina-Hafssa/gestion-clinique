# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ClinicAppointmentRescheduleWizard(models.TransientModel):
    _name = 'clinic.appointment.reschedule.wizard'
    _description = 'Assistant de reprogrammation de rendez-vous'

    appointment_id = fields.Many2one(
        'clinic.appointment',
        string="Rendez-vous à reprogrammer",
        required=True,
        ondelete='cascade',
    )
    patient_id = fields.Many2one(
        related='appointment_id.patient_id',
        string="Patient",
        readonly=True,
    )
    doctor_id = fields.Many2one(
        related='appointment_id.doctor_id',
        string="Médecin",
        readonly=True,
    )
    old_date_start = fields.Datetime(
        related='appointment_id.date_start',
        string="Ancienne date",
        readonly=True,
    )

    new_date_start = fields.Datetime(
        string="Nouvelle date de début",
        required=True,
    )
    new_date_stop = fields.Datetime(
        string="Nouvelle date de fin",
        required=True,
    )
    reason = fields.Text(
        string="Motif de reprogrammation",
        required=True,
    )

    @api.constrains('new_date_start', 'new_date_stop')
    def _check_dates(self):
        for wiz in self:
            if wiz.new_date_start and wiz.new_date_stop and wiz.new_date_stop <= wiz.new_date_start:
                raise ValidationError(_("La nouvelle date de fin doit être après la date de début."))

    def action_reschedule(self):
        """RG-RDV-02: vérifie le nouveau créneau AVANT de libérer l'ancien."""
        self.ensure_one()
        appt = self.appointment_id

        # 1. Vérifier que le nouveau créneau est libre (sans toucher l'ancien)
        conflicts = self.env['clinic.appointment'].search([
            ('id', '!=', appt.id),
            ('doctor_id', '=', appt.doctor_id.id),
            ('status', 'not in', ['cancelled', 'no_show', 'rescheduled']),
            ('date_start', '<', self.new_date_stop),
            ('date_stop', '>', self.new_date_start),
        ], limit=1)

        if conflicts:
            raise UserError(_(
                "Le nouveau créneau est occupé (RDV %s de %s à %s). "
                "L'ancien rendez-vous est conservé."
            ) % (conflicts.name, conflicts.date_start, conflicts.date_stop))

        # 2. Créer le nouveau RDV (avant de marquer l'ancien comme reprogrammé)
        new_appt = self.env['clinic.appointment'].create({
            'patient_id': appt.patient_id.id,
            'doctor_id': appt.doctor_id.id,
            'service': appt.service,
            'date_start': self.new_date_start,
            'date_stop': self.new_date_stop,
            'room': appt.room,
            'booking_channel': appt.booking_channel,
            'status': 'booked',
            'reschedule_origin_id': appt.id,
        })

        # 3. Marquer l'ancien comme reprogrammé
        appt.write({
            'status': 'rescheduled',
            'reschedule_new_id': new_appt.id,
        })
        appt.message_post(
            body=_("RDV reprogrammé vers %s. Motif : %s") % (new_appt.name, self.reason),
            subtype_xmlid='mail.mt_note',
        )

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'clinic.appointment',
            'res_id': new_appt.id,
            'view_mode': 'form',
            'target': 'current',
        }