from odoo import fields, models
from odoo.exceptions import UserError


class HmsVisitLauncher(models.TransientModel):
    """Pick a visit type and open that department's visit form for the patient."""
    _name = 'hms.visit.launcher'
    _description = 'Register Visit'

    patient_id = fields.Many2one('hms.patient', 'Patient', required=True)
    visit_type_id = fields.Many2one(
        'hms.visit.type', 'Visit Type', required=True,
        domain="[('is_available', '=', True)]")

    def action_launch(self):
        self.ensure_one()
        model = self.visit_type_id.res_model
        if not model or model not in self.env.registry.models:
            raise UserError(
                "The module providing '%s' is not installed on this system."
                % self.visit_type_id.name)
        return {
            'type': 'ir.actions.act_window',
            'name': self.visit_type_id.name,
            'res_model': model,
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_patient_id': self.patient_id.id},
        }
