from odoo import api, fields, models
from dateutil.relativedelta import relativedelta


class HmsPatient(models.Model):
    """Full patient master record for nestHMS."""
    _name = 'hms.patient'
    _description = 'HMS Patient'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'patient_id desc'

    # ── Identity ──────────────────────────────────────────────────────────────
    patient_id = fields.Char('Patient No.', readonly=True, copy=False, default='New')
    name = fields.Char('Full Name', required=True, tracking=True)
    date_of_birth = fields.Date('Date of Birth')
    age = fields.Integer('Age (years)', compute='_compute_age', store=True)
    age_display = fields.Char('Age', compute='_compute_age', store=True,
                              help='Human-friendly age: years, or months/days for infants.')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], required=True, default='male', tracking=True)
    blood_group = fields.Char('Blood Group')
    state = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('deceased', 'Deceased'),
    ], default='active', tracking=True)

    # ── Identification ────────────────────────────────────────────────────────
    id_type = fields.Selection([
        ('national_id', 'National ID (NIDA)'),
        ('passport', 'Passport'),
        ('voter_id', 'Voter Registration Card'),
        ('birth_cert', 'Birth Certificate'),
        ('driving_license', 'Driving Licence'),
    ], 'ID Type', default='national_id')
    id_number = fields.Char('ID / NIDA Number')
    photo = fields.Image('Photo', max_width=256, max_height=256)

    # ── Contact ───────────────────────────────────────────────────────────────
    phone = fields.Char('Phone', required=True)
    email = fields.Char('Email')

    # ── Tanzania Administrative Units ─────────────────────────────────────────
    region_id = fields.Many2one('hms.tz.region', 'Region')
    district = fields.Char('District')
    ward = fields.Char('Ward / Kata')
    street_village = fields.Char('Street / Village (Mtaa / Kijiji)')

    # ── Next of Kin ───────────────────────────────────────────────────────────
    kin_name = fields.Char('Next of Kin Name')
    kin_relationship = fields.Selection([
        ('spouse', 'Spouse / Mwenzi'),
        ('parent', 'Parent / Mzazi'),
        ('child', 'Child / Mtoto'),
        ('sibling', 'Sibling / Ndugu'),
        ('guardian', 'Guardian / Mlezi'),
        ('friend', 'Friend / Rafiki'),
        ('other', 'Other / Nyingine'),
    ], 'Relationship to NOK')
    kin_phone = fields.Char('NOK Phone Number')

    # ── Emergency Contact ─────────────────────────────────────────────────────
    emergency_contact = fields.Char('Emergency Contact Name')
    emergency_phone = fields.Char('Emergency Contact Phone')
    emergency_relationship = fields.Char('Relationship')

    # ── Insurance & Payment ───────────────────────────────────────────────────
    nhif_number = fields.Char('NHIF Membership No.')
    chf_number = fields.Char('CHF Card No.', help='Community Health Fund')
    insurance_scheme_id = fields.Many2one('hms.insurance.scheme', 'Insurance Scheme')
    insurance_policy_number = fields.Char('Policy Number')
    insurance_plan_tier = fields.Char('Plan Tier', help='e.g. Gold, Silver, Standard')
    corporate_employer_id = fields.Many2one(
        'res.partner', 'Corporate Employer',
        domain=[('is_company', '=', True)],
        help='For employees on corporate credit accounts'
    )
    payer_type = fields.Selection([
        ('cash', 'Cash / Self-pay'),
        ('insurance', 'Insurance / Scheme'),
        ('corporate', 'Corporate / Employer'),
        ('nhif', 'NHIF'),
        ('waiver', 'Waiver / Free'),
    ], 'Payer Type')

    # ── Clinical ──────────────────────────────────────────────────────────────
    allergy_ids = fields.One2many('hms.patient.allergy', 'patient_id', 'Known Allergies')
    chronic_condition_ids = fields.One2many('hms.patient.condition', 'patient_id', 'Chronic Conditions')
    has_allergies = fields.Boolean('Has Allergies', compute='_compute_has_allergies', store=True)
    clinical_notes = fields.Text('Internal Clinical Notes')

    # ── OPD Visits ────────────────────────────────────────────────────────────
    opd_visit_ids = fields.One2many('hms.opd.visit', 'patient_id', 'Visit History')
    opd_visit_count = fields.Integer('OPD Visits', compute='_compute_opd_visit_count')
    has_active_visit = fields.Boolean('Has Active Visit', compute='_compute_opd_visit_count')

    # ── Auto Flags ────────────────────────────────────────────────────────────
    is_paediatric = fields.Boolean('Paediatric', compute='_compute_age_flags', store=True)
    is_geriatric = fields.Boolean('Geriatric', compute='_compute_age_flags', store=True)

    # ─────────────────────────────── Computes ────────────────────────────────

    @api.depends('date_of_birth')
    def _compute_age(self):
        today = fields.Date.today()
        for rec in self:
            if rec.date_of_birth:
                d = relativedelta(today, rec.date_of_birth)
                rec.age = d.years
                if d.years >= 1:
                    rec.age_display = ('%d yr %d mo' % (d.years, d.months)
                                       if d.months else '%d yr' % d.years)
                elif d.months >= 1:
                    rec.age_display = ('%d mo %d d' % (d.months, d.days)
                                       if d.days else '%d mo' % d.months)
                else:
                    rec.age_display = '%d d' % d.days
            else:
                rec.age = 0
                rec.age_display = ''

    @api.depends('age')
    def _compute_age_flags(self):
        for rec in self:
            rec.is_paediatric = rec.age < 18
            rec.is_geriatric = rec.age >= 65

    @api.depends('allergy_ids')
    def _compute_has_allergies(self):
        for rec in self:
            rec.has_allergies = bool(rec.allergy_ids)

    def _compute_opd_visit_count(self):
        for rec in self:
            rec.opd_visit_count = len(rec.opd_visit_ids)
            # Check if patient has any active visits (not completed, cancelled, or discharge)
            active_visits = rec.opd_visit_ids.filtered(
                lambda v: v.state not in ['completed', 'cancelled', 'discharge']
            )
            rec.has_active_visit = bool(active_visits)

    # ─────────────────────────────── ORM ─────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('patient_id', 'New') == 'New':
                vals['patient_id'] = self.env['ir.sequence'].next_by_code('hms.patient') or 'New'
        return super().create(vals_list)

    # ─────────────────────────────── Actions ─────────────────────────────────

    def action_register_opd_visit(self):
        self.ensure_one()
        visit_type = 'return' if self.opd_visit_count > 0 else 'new'
        return {
            'type': 'ir.actions.act_window',
            'name': 'New OPD Visit',
            'res_model': 'hms.opd.visit',
            'view_mode': 'form',
            'context': {
                'default_patient_id': self.id,
                'default_visit_type': visit_type,
            },
        }

    def action_view_opd_visits(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'OPD Visits',
            'res_model': 'hms.opd.visit',
            'view_mode': 'list,form',
            'domain': [('patient_id', '=', self.id)],
            'context': {'default_patient_id': self.id},
        }


class HmsPatientAllergy(models.Model):
    """Per-patient allergy records with severity tracking."""
    _name = 'hms.patient.allergy'
    _description = 'Patient Allergy'
    _order = 'severity desc, allergen'

    patient_id = fields.Many2one('hms.patient', required=True, ondelete='cascade')
    allergen = fields.Char('Allergen / Drug / Food', required=True)
    category = fields.Selection([
        ('drug', 'Drug'),
        ('food', 'Food'),
        ('environmental', 'Environmental'),
        ('latex', 'Latex / Rubber'),
        ('other', 'Other'),
    ], 'Category', default='drug', required=True)
    reaction = fields.Char('Reaction / Symptoms')
    severity = fields.Selection([
        ('mild', 'Mild'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe — Anaphylaxis Risk'),
    ], 'Severity', default='mild', required=True)
    notes = fields.Text('Additional Notes')


class HmsPatientCondition(models.Model):
    """Chronic conditions per patient."""
    _name = 'hms.patient.condition'
    _description = 'Patient Chronic Condition'
    _order = 'condition'

    patient_id = fields.Many2one('hms.patient', required=True, ondelete='cascade')
    condition = fields.Char('Condition / Diagnosis', required=True)
    icd10_code = fields.Char('ICD-10 Code')
    since = fields.Date('Diagnosed Since')
    is_sensitive = fields.Boolean(
        'Sensitive Record',
        help='Mark HIV, TB, and other sensitive conditions — visible only to clinical staff'
    )
    status = fields.Selection([
        ('active', 'Active / Ongoing'),
        ('controlled', 'Controlled / Stable'),
        ('resolved', 'Resolved'),
    ], 'Status', default='active')
    notes = fields.Text('Notes')
