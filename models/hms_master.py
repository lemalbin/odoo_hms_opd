from odoo import fields, models


class HmsTzRegion(models.Model):
    """Tanzania's 31 administrative regions."""
    _name = 'hms.tz.region'
    _description = 'Tanzania Region'
    _order = 'name'

    name = fields.Char('Region Name', required=True)
    code = fields.Char('Region Code')
    active = fields.Boolean(default=True)


class HmsInsuranceScheme(models.Model):
    """Insurance schemes supported at Savanna Hospital."""
    _name = 'hms.insurance.scheme'
    _description = 'Insurance Scheme'
    _order = 'name'

    name = fields.Char('Scheme Name', required=True)
    scheme_type = fields.Selection([
        ('nhif', 'NHIF (National Health Insurance Fund)'),
        ('chf', 'CHF (Community Health Fund)'),
        ('private', 'Private Insurance'),
        ('corporate', 'Corporate / Self-insured'),
    ], 'Scheme Type', required=True, default='private')
    claims_method = fields.Char('Claims Submission Method', help='e.g. Portal, EDI, Email batch')
    avg_settlement_days = fields.Integer('Avg. Settlement Days')
    contact_email = fields.Char('Claims Contact Email')
    contact_phone = fields.Char('Claims Contact Phone')
    pre_auth_required = fields.Boolean(
        'Pre-auth Required',
        help='Tick if this scheme requires pre-authorisation for admissions and major procedures'
    )
    pre_auth_threshold = fields.Float(
        'Pre-auth Threshold (TZS)',
        help='Bill amount above which pre-auth is mandatory'
    )
    active = fields.Boolean(default=True)
    notes = fields.Text('Notes')


class HmsAllergyMaster(models.Model):
    """Reference list of known allergens for quick lookup during patient registration."""
    _name = 'hms.allergy.master'
    _description = 'Allergy Master List'
    _order = 'name'

    name = fields.Char('Allergen', required=True)
    category = fields.Selection([
        ('drug', 'Drug'),
        ('food', 'Food'),
        ('environmental', 'Environmental'),
        ('latex', 'Latex'),
        ('other', 'Other'),
    ], 'Category', default='drug')


class HmsConditionMaster(models.Model):
    """Reference list of chronic conditions for quick selection."""
    _name = 'hms.condition.master'
    _description = 'Chronic Condition Master List'
    _order = 'name'

    name = fields.Char('Condition', required=True)
    icd10_code = fields.Char('ICD-10 Code')
    is_sensitive = fields.Boolean(
        'Sensitive',
        help='Conditions like HIV/TB — access restricted to clinical roles'
    )
