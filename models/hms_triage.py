from odoo import api, fields, models


# Triage colour → display label and maximum expected wait
TRIAGE_META = {
    'red':    {'label': 'Red — Immediate',    'wait': 'Immediate — no waiting',   'priority': 5},
    'yellow': {'label': 'Yellow — Urgent',    'wait': 'Within 30 minutes',        'priority': 4},
    'orange': {'label': 'Orange — Semi-urgent','wait': 'Within 60 minutes',       'priority': 3},
    'green':  {'label': 'Green — Non-urgent', 'wait': 'As queue allows',          'priority': 2},
    'black':  {'label': 'Black — DOA',        'wait': 'Documentation only',       'priority': 1},
}


class HmsTriage(models.Model):
    """
    Triage assessment performed by the triage nurse at arrival.
    Assigns a 5-level colour category that drives queue priority.
    Also records initial vital signs captured at triage.
    """
    _name = 'hms.triage'
    _description = 'Patient Triage'
    _inherit = ['mail.thread']
    _order = 'triage_time desc'
    _rec_name = 'display_name'

    # ── Links ─────────────────────────────────────────────────────────────────
    visit_id = fields.Many2one('hms.opd.visit', 'OPD Visit', required=True, ondelete='cascade')
    patient_id = fields.Many2one(related='visit_id.patient_id', string='Patient',
                                 store=True, readonly=True)

    # ── Triage Officer ────────────────────────────────────────────────────────
    nurse_id = fields.Many2one('hr.employee', 'Triage Nurse', required=True,
                               default=lambda self: self.env.user.employee_id)
    triage_time = fields.Datetime('Triage Time', default=fields.Datetime.now, required=True)

    # ── Category ──────────────────────────────────────────────────────────────
    category = fields.Selection([
        ('red',    'Red — Immediate (life-threatening)'),
        ('yellow', 'Yellow — Urgent (within 30 min)'),
        ('orange', 'Orange — Semi-urgent (within 60 min)'),
        ('green',  'Green — Non-urgent (routine queue)'),
        ('black',  'Black — Dead on Arrival (DOA)'),
    ], 'Triage Colour', required=True, tracking=True)

    priority = fields.Integer('Priority Score', compute='_compute_priority', store=True,
                              help='5=Red (highest) → 1=Black (documentation only)')
    expected_wait = fields.Char('Expected Wait', compute='_compute_priority')

    # ── Presenting Complaint ──────────────────────────────────────────────────
    presenting_complaint = fields.Text('Presenting Complaint', required=True)
    mode_of_arrival = fields.Selection([
        ('walk_in', 'Walk-in'),
        ('ambulance', 'Ambulance'),
        ('referred', 'Referred'),
        ('carried', 'Carried by relative'),
    ], 'Mode of Arrival', default='walk_in')

    # ── Vital Signs at Triage ─────────────────────────────────────────────────
    bp_systolic = fields.Integer('BP Systolic (mmHg)')
    bp_diastolic = fields.Integer('BP Diastolic (mmHg)')
    bp_display = fields.Char('Blood Pressure', compute='_compute_bp_display')

    temperature = fields.Float('Temperature (°C)')
    pulse = fields.Integer('Pulse Rate (bpm)')
    respiratory_rate = fields.Integer('Respiratory Rate (/min)')
    spo2 = fields.Float('SpO2 (%)')
    weight = fields.Float('Weight (kg)')
    height = fields.Float('Height (cm)')
    bmi = fields.Float('BMI', compute='_compute_bmi', store=True)
    rbs = fields.Float('RBS (mmol/L)', help='Random Blood Sugar')
    gcs = fields.Integer('GCS', default=15, help='Glasgow Coma Scale (3–15)')

    # Pain Scale
    pain_scale = fields.Selection([
        ('0', '0 — No Pain'),
        ('2', '2 — Mild'),
        ('4', '4 — Moderate'),
        ('6', '6 — Severe'),
        ('8', '8 — Very Severe'),
        ('10', '10 — Worst'),
    ], 'Pain Scale')

    # ── DOA Fields ────────────────────────────────────────────────────────────
    is_doa = fields.Boolean('Dead on Arrival', compute='_compute_is_doa', store=True)
    doa_certifying_doctor = fields.Many2one('hr.employee', 'Certifying Doctor (DOA)')
    police_notified = fields.Boolean('Police Notified')
    police_ob_number = fields.Char('Police OB Number')

    # ── Notes ─────────────────────────────────────────────────────────────────
    notes = fields.Text('Triage Notes')

    # ─────────────────────────────────── Computes ─────────────────────────────

    @api.depends('category')
    def _compute_priority(self):
        for rec in self:
            meta = TRIAGE_META.get(rec.category, {})
            rec.priority = meta.get('priority', 0)
            rec.expected_wait = meta.get('wait', '')

    @api.depends('category')
    def _compute_is_doa(self):
        for rec in self:
            rec.is_doa = rec.category == 'black'

    @api.depends('bp_systolic', 'bp_diastolic')
    def _compute_bp_display(self):
        for rec in self:
            if rec.bp_systolic and rec.bp_diastolic:
                rec.bp_display = f"{rec.bp_systolic}/{rec.bp_diastolic} mmHg"
            else:
                rec.bp_display = ''

    @api.depends('weight', 'height')
    def _compute_bmi(self):
        for rec in self:
            if rec.height > 0 and rec.weight > 0:
                rec.bmi = round(rec.weight / (rec.height / 100) ** 2, 1)
            else:
                rec.bmi = 0.0

    # ─────────────────────────────────── ORM ──────────────────────────────────

    def write(self, vals):
        res = super().write(vals)
        # Keep visit triage_id and state in sync
        for rec in self:
            visit = rec.visit_id
            if visit.triage_id.id != rec.id:
                visit.write({'triage_id': rec.id})
            # Advance visit to 'triage' state once triage exists
            if visit.state == 'registration':
                visit.write({'state': 'triage'})
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            visit = rec.visit_id
            visit.write({'triage_id': rec.id})
            if visit.state == 'registration':
                visit.write({'state': 'triage'})
        return records


class HmsOpdVisitTriageExt(models.Model):
    """Add triage history count + action to OPD visit."""
    _inherit = 'hms.opd.visit'

    triage_ids = fields.One2many('hms.triage', 'visit_id', string='Triage Records')
    triage_count = fields.Integer(compute='_compute_triage_count', string='Triage')

    @api.depends('triage_ids')
    def _compute_triage_count(self):
        for r in self:
            r.triage_count = len(r.triage_ids)
