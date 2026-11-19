# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ClinicAppointmentCancelWizard(models.TransientModel):
    _name = 'clinic.appointment.cancel.wizard'
    _description = 'Assistant d\'annulation de rendez-vous'

    appointment_id = fields.Many2one(
        'clinic.appointment',
        string="Rendez-vous",
        required=True,
        ondelete='cascade',
    )
    cancel_reason = fields.Text(
        string="Motif d'annulation",
        required=True,
    )
    confirm_cancel = fields.Boolean(
        string="Je confirme l'annulation",
        required=True,
    )

    def action_confirm_cancel(self):
        self.ensure_one()
        if not self.confirm_cancel:
            raise UserError(_("Veuillez confirmer l'annulation."))
        appt = self.appointment_id
        if appt.status in ('cancelled', 'done'):
            raise UserError(_("Ce rendez-vous ne peut plus être annulé."))

        appt.write({
            'status': 'cancelled',
            'cancel_reason': self.cancel_reason,
            'cancel_date': fields.Datetime.now(),
            'cancel_user_id': self.env.user.id,
        })
        appt.message_post(
            body=_("RDV annulé par %s. Motif : %s") % (self.env.user.name, self.cancel_reason),
            subtype_xmlid='mail.mt_note',
        )
        return {'type': 'ir.actions.act_window_close'}