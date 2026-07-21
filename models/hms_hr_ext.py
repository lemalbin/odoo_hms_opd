from odoo import fields, models


class HrEmployee(models.Model):
    """Extend hr.employee to flag clinical staff for nestHMS field domains."""
    _inherit = 'hr.employee'

    is_clinical_staff = fields.Boolean(
        'Clinical Staff',
        help='Tick for doctors, nurses, and clinical officers. '
             'This controls which employees appear in clinical fields (Attending Doctor, etc.).'
    )
