from odoo import api, fields, models


class HmsIcd10(models.Model):
    """ICD-10 diagnosis catalogue for OPD.

    Populate it three ways:
      1. The seeded common Tanzania OPD codes (data/hms_icd10_data.xml).
      2. Manually via Configuration > ICD-10 Codes.
      3. Bulk-import the full WHO ICD-10 list as CSV (Favorites > Import on
         the list view; map columns to Code / Description)."""
    _name = 'hms.icd10'
    _description = 'ICD-10 Diagnosis Code'
    _order = 'code'
    _rec_name = 'display_name'
    _rec_names_search = ['code', 'name', 'display_name']

    code = fields.Char('ICD-10 Code', required=True, index=True)
    name = fields.Char('Description', required=True)
    category = fields.Char('Chapter / Category')
    parent_id = fields.Many2one('hms.icd10', 'Parent Code', ondelete='set null')
    active = fields.Boolean(default=True)
    display_name = fields.Char(compute='_compute_display_name', store=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'This ICD-10 code already exists.'),
    ]

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = ('%s - %s' % (rec.code, rec.name)) if rec.code else (rec.name or '')
