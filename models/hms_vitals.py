from odoo import api, fields, models


class HmsVitals(models.Model):
    """
    Vital signs recorded during an OPD visit.
    Multiple readings can be captured (e.g. on arrival and after treatment).
    """
    _name = 'hms.vitals'
    _description = 'Patient Vital Signs'
    _order = 'recorded_at desc'

    visit_id = fields.Many2one('hms.opd.visit', 'OPD Visit', required=True, ondelete='cascade')
    patient_id = fields.Many2one(related='visit_id.patient_id', string='Patient',
                                 store=True, readonly=True)

    recorded_at = fields.Datetime('Recorded At', default=fields.Datetime.now, required=True)
    recorded_by = fields.Many2one('res.users', 'Recorded By', default=lambda self: self.env.user)

    # ── Blood Pressure ────────────────────────────────────────────────────────
    bp_systolic = fields.Integer('BP Systolic (mmHg)')
    bp_diastolic = fields.Integer('BP Diastolic (mmHg)')
    bp_display = fields.Char('Blood Pressure', compute='_compute_bp_display')
    bp_status = fields.Char('BP Status', compute='_compute_bp_status',
                             help='Normal / Elevated / High / Low')

    # ── Temperature ───────────────────────────────────────────────────────────
    temperature = fields.Float('Temperature (°C)')
    temp_route = fields.Selection([
        ('oral', 'Oral'),
        ('axillary', 'Axillary'),
        ('rectal', 'Rectal'),
        ('tympanic', 'Tympanic / Ear'),
    ], 'Temp Route', default='axillary')

    # ── Pulse & Respiration ───────────────────────────────────────────────────
    pulse = fields.Integer('Pulse Rate (bpm)')
    respiratory_rate = fields.Integer('Respiratory Rate (/min)')

    # ── Oxygen Saturation ─────────────────────────────────────────────────────
    spo2 = fields.Float('SpO2 (%)')

    # ── Weight / Height / BMI ─────────────────────────────────────────────────
    weight = fields.Float('Weight (kg)')
    height = fields.Float('Height (cm)')
    bmi = fields.Float('BMI', compute='_compute_bmi', store=True)
    bmi_category = fields.Char('BMI Category', compute='_compute_bmi')

    # ── Blood Sugar ───────────────────────────────────────────────────────────
    rbs = fields.Float('RBS (mmol/L)', help='Random Blood Sugar')
    rbs_status = fields.Char('RBS Status', compute='_compute_rbs_status')

    # ── GCS ───────────────────────────────────────────────────────────────────
    gcs_eye = fields.Integer('GCS Eye (E)', default=4)
    gcs_verbal = fields.Integer('GCS Verbal (V)', default=5)
    gcs_motor = fields.Integer('GCS Motor (M)', default=6)
    gcs_total = fields.Integer('GCS Total', compute='_compute_gcs', store=True)

    notes = fields.Text('Vitals Notes')

    # ─────────────────────────────────── Computes ─────────────────────────────

    @api.depends('bp_systolic', 'bp_diastolic')
    def _compute_bp_display(self):
        for rec in self:
            if rec.bp_systolic and rec.bp_diastolic:
                rec.bp_display = f"{rec.bp_systolic}/{rec.bp_diastolic}"
            else:
                rec.bp_display = 'Not recorded'

    @api.depends('bp_systolic', 'bp_diastolic')
    def _compute_bp_status(self):
        for rec in self:
            s, d = rec.bp_systolic, rec.bp_diastolic
            if not s or not d:
                rec.bp_status = ''
            elif s < 90 or d < 60:
                rec.bp_status = '⚠ Low'
            elif s < 120 and d < 80:
                rec.bp_status = '✓ Normal'
            elif s < 130 and d < 80:
                rec.bp_status = 'Elevated'
            elif s < 140 or d < 90:
                rec.bp_status = 'Stage 1 High'
            else:
                rec.bp_status = '⚠ Stage 2 High'

    @api.depends('weight', 'height')
    def _compute_bmi(self):
        for rec in self:
            if rec.height > 0 and rec.weight > 0:
                bmi = round(rec.weight / (rec.height / 100) ** 2, 1)
                rec.bmi = bmi
                if bmi < 18.5:
                    rec.bmi_category = 'Underweight'
                elif bmi < 25:
                    rec.bmi_category = 'Normal'
                elif bmi < 30:
                    rec.bmi_category = 'Overweight'
                else:
                    rec.bmi_category = '⚠ Obese'
            else:
                rec.bmi = 0.0
                rec.bmi_category = ''

    @api.depends('rbs')
    def _compute_rbs_status(self):
        for rec in self:
            if not rec.rbs:
                rec.rbs_status = ''
            elif rec.rbs < 2.8:
                rec.rbs_status = '⚠ Hypoglycaemia'
            elif rec.rbs < 7.8:
                rec.rbs_status = '✓ Normal'
            elif rec.rbs < 11.1:
                rec.rbs_status = 'Pre-diabetic range'
            else:
                rec.rbs_status = '⚠ High — check'

    @api.depends('gcs_eye', 'gcs_verbal', 'gcs_motor')
    def _compute_gcs(self):
        for rec in self:
            rec.gcs_total = rec.gcs_eye + rec.gcs_verbal + rec.gcs_motor
