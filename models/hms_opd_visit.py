from odoo import api, fields, models


class HmsOpdVisit(models.Model):
    """
    OPD Visit — the core clinical episode for every outpatient encounter.
    Lifecycle: Registration → Triage → Waiting (Queue) → Consultation
               → Investigation → Discharge → Completed
    All clinical orders (drugs, tests, procedures) auto-generate billing entries.
    """
    _name = 'hms.opd.visit'
    _description = 'OPD Visit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'visit_date desc, id desc'
    _rec_name = 'name'

    # ── Identity ──────────────────────────────────────────────────────────────
    name = fields.Char('Visit No.', readonly=True, copy=False, default='New', tracking=True)
    patient_id = fields.Many2one('hms.patient', 'Patient', required=True,
                                 ondelete='restrict', tracking=True)

    # ── Quick-access patient info (read-only, for convenience on the form) ───
    patient_age = fields.Integer(related='patient_id.age', string='Age (yrs)', readonly=True)
    patient_age_display = fields.Char(related='patient_id.age_display', string='Age', readonly=True)
    patient_gender = fields.Selection(related='patient_id.gender', string='Gender', readonly=True)
    patient_blood_group = fields.Char(related='patient_id.blood_group', string='Blood Group', readonly=True)
    patient_nhif_number = fields.Char(related='patient_id.nhif_number', string='NHIF No.', readonly=True)
    has_allergies = fields.Boolean(related='patient_id.has_allergies', string='Allergy Alert', readonly=True)
    is_paediatric = fields.Boolean(related='patient_id.is_paediatric', string='Paediatric', readonly=True)

    # ── Visit Classification ──────────────────────────────────────────────────
    visit_date = fields.Datetime('Visit Date/Time', default=fields.Datetime.now,
                                 required=True, tracking=True)
    visit_type = fields.Selection([
        ('new', 'New Patient'),
        ('return', 'Return Visit'),
        ('referral_in', 'Referral In'),
        ('emergency', 'Emergency'),
    ], 'Visit Type', required=True, default='new', tracking=True)
    # OPD sub-clinic only. Other departments (Dental, RCH, Maternity) are
    # their own visit forms launched from the patient hub, not options here.
    department = fields.Selection([
        ('general', 'General OPD'),
        ('paediatric', 'Paediatric OPD'),
        ('specialist', 'Specialist Clinic'),
    ], 'OPD Clinic', default='general', tracking=True)

    # ── Payer / Payment Class ────────────────────────────────────────────────
    payer_type = fields.Selection([
        ('cash', 'Cash / Self-pay'),
        ('insurance', 'Insurance / Scheme'),
        ('corporate', 'Corporate / Employer'),
        ('nhif', 'NHIF'),
        ('waiver', 'Waiver / Free'),
    ], string='Payer Type', default='cash', required=True, tracking=True)
    insurance_scheme_id = fields.Many2one(
        'hms.insurance.scheme', string='Insurance Scheme',
        domain="[('active', '=', True)]")

    # ── Consultation ─────────────────────────────────────────────────────────
    # Kept for backward compatibility with visits billed before multi-consultation.
    consultation_product_id = fields.Many2one(
        'product.product', string='Consultation Fee',
        domain="[('type', '=', 'service')]",
        help='Legacy single consultation fee. New visits use the Consultations list.')
    consultation_ids = fields.One2many(
        'hms.visit.consultation', 'visit_id', 'Consultations')

    # ── Triage ───────────────────────────────────────────────────────────────
    triage_id = fields.Many2one('hms.triage', 'Triage Record', readonly=True)
    triage_category = fields.Selection(
        related='triage_id.category', string='Triage Colour', store=True, readonly=True
    )
    triage_priority = fields.Integer(
        related='triage_id.priority', string='Priority', store=True, readonly=True
    )

    # ── Attending Doctor ─────────────────────────────────────────────────────
    attending_doctor_id = fields.Many2one(
        'hr.employee', 'Attending Doctor', tracking=True,
        default=lambda self: self.env.user.employee_id.id)

    # ── Queue ─────────────────────────────────────────────────────────────────
    queue_id = fields.Many2one('hms.queue', 'Queue', readonly=True)
    queue_number = fields.Integer(related='queue_id.queue_number', string='Queue No.', readonly=True)
    queue_state = fields.Selection(related='queue_id.state', string='Queue Status', readonly=True)

    # ── Vital Signs ───────────────────────────────────────────────────────────
    vitals_ids = fields.One2many('hms.vitals', 'visit_id', 'Vital Signs')
    latest_bp = fields.Char('Latest BP', compute='_compute_latest_vitals')
    latest_temp = fields.Float('Latest Temp (°C)', compute='_compute_latest_vitals')
    latest_spo2 = fields.Float('Latest SpO2 (%)', compute='_compute_latest_vitals')
    latest_pulse = fields.Integer('Latest Pulse', compute='_compute_latest_vitals')

    # Full vitals snapshot from the latest triage (read-only display on the tab)
    triage_bp_systolic = fields.Integer(related='triage_id.bp_systolic', string='BP Systolic (mmHg)', readonly=True)
    triage_bp_diastolic = fields.Integer(related='triage_id.bp_diastolic', string='BP Diastolic (mmHg)', readonly=True)
    triage_bp_display = fields.Char(related='triage_id.bp_display', string='Blood Pressure', readonly=True)
    triage_pulse = fields.Integer(related='triage_id.pulse', string='Pulse Rate (bpm)', readonly=True)
    triage_temperature = fields.Float(related='triage_id.temperature', string='Temperature (°C)', readonly=True)
    triage_respiratory_rate = fields.Integer(related='triage_id.respiratory_rate', string='Respiratory Rate (/min)', readonly=True)
    triage_spo2 = fields.Float(related='triage_id.spo2', string='SpO2 (%)', readonly=True)
    triage_weight = fields.Float(related='triage_id.weight', string='Weight (kg)', readonly=True)
    triage_height = fields.Float(related='triage_id.height', string='Height (cm)', readonly=True)
    triage_bmi = fields.Float(related='triage_id.bmi', string='BMI', readonly=True)
    triage_rbs = fields.Float(related='triage_id.rbs', string='RBS (mmol/L)', readonly=True)
    triage_gcs = fields.Integer(related='triage_id.gcs', string='GCS', readonly=True)
    triage_pain_scale = fields.Selection(related='triage_id.pain_scale', string='Pain Scale', readonly=True)

    # ── Clinical ──────────────────────────────────────────────────────────────
    chief_complaint = fields.Text('Chief Complaint', tracking=True)
    history = fields.Html('History of Presenting Illness')
    examination_findings = fields.Text('Examination Findings')
    pain_scale = fields.Selection([
        ('0', '0 — No Pain'),
        ('2', '2 — Mild'),
        ('4', '4 — Moderate'),
        ('6', '6 — Severe'),
        ('8', '8 — Very Severe'),
        ('10', '10 — Worst'),
    ], 'Pain Scale')

    # ── Diagnosis ─────────────────────────────────────────────────────────────
    diagnosis_ids = fields.One2many('hms.visit.diagnosis', 'visit_id', 'Diagnoses')
    primary_diagnosis = fields.Char('Primary Diagnosis', tracking=True,
                                    help='ICD-10 code or free text — set from Diagnoses tab')

    # ── Management Plan ───────────────────────────────────────────────────────
    management_plan = fields.Text('Management Plan')
    referral_required = fields.Boolean('Referral Required')
    referral_to = fields.Char('Referred To (Specialist / Facility)')
    admission_required = fields.Boolean('Admission Required', tracking=True)
    ward_preference = fields.Selection([
        ('general', 'General Ward'),
        ('semi_private', 'Semi-Private'),
        ('private', 'Private Room'),
        ('vip', 'VIP Suite'),
        ('icu', 'ICU'),
        ('hdu', 'HDU'),
        ('maternity', 'Maternity Ward'),
        ('paediatric', 'Paediatric Ward'),
    ], 'Preferred Ward Category', help='Only applicable when admission is required')

    # ── Discharge ─────────────────────────────────────────────────────────────
    discharge_summary = fields.Text('Discharge Summary')
    follow_up_date = fields.Date('Follow-up Appointment')
    follow_up_notes = fields.Char('Follow-up Instructions')
    discharge_time = fields.Datetime('Discharge Time', readonly=True)

    # ── Status ────────────────────────────────────────────────────────────────
    state = fields.Selection([
        ('registration', 'Registration'),
        ('triage', 'Triage'),
        ('waiting', 'Waiting for Doctor'),
        ('consultation', 'In Consultation'),
        ('investigation', 'Awaiting Results'),
        ('discharge', 'Ready for Discharge'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], 'Status', default='registration', tracking=True, required=True)

    # ── Billing Placeholder ───────────────────────────────────────────────────
    # Detailed billing lines will be added in the billing module.
    # These summary fields give a quick view on the visit form.
    total_billed = fields.Float('Total Billed (TZS)', default=0.0)
    total_paid = fields.Float('Total Paid (TZS)', default=0.0)
    balance_due = fields.Float('Balance Due', compute='_compute_balance_due')

    # ─────────────────────────────────── Computes ─────────────────────────────

    @api.depends('total_billed', 'total_paid')
    def _compute_balance_due(self):
        for rec in self:
            rec.balance_due = rec.total_billed - rec.total_paid

    @api.depends('vitals_ids', 'vitals_ids.temperature', 'vitals_ids.bp_systolic',
                 'vitals_ids.spo2', 'vitals_ids.pulse',
                 'triage_id', 'triage_id.temperature', 'triage_id.bp_systolic',
                 'triage_id.spo2', 'triage_id.pulse')
    def _compute_latest_vitals(self):
        for rec in self:
            # Latest recorded vitals; fall back to the triage reading when no
            # separate vitals record has been captured yet.
            vitals = rec.vitals_ids.sorted('recorded_at', reverse=True)
            src = vitals[0] if vitals else rec.triage_id
            if src:
                rec.latest_bp = f"{src.bp_systolic}/{src.bp_diastolic}" if src.bp_systolic else ''
                rec.latest_temp = src.temperature
                rec.latest_spo2 = src.spo2
                rec.latest_pulse = src.pulse
            else:
                rec.latest_bp = ''
                rec.latest_temp = 0.0
                rec.latest_spo2 = 0.0
                rec.latest_pulse = 0

    # ─────────────────────────────────── ORM ──────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('hms.opd.visit') or 'New'
            
            # Check if patient already has an active visit
            patient_id = vals.get('patient_id')
            if patient_id:
                active_visit = self.search([
                    ('patient_id', '=', patient_id),
                    ('state', 'not in', ['completed', 'cancelled', 'discharge'])
                ], limit=1)
                if active_visit:
                    raise models.ValidationError(
                        f"Patient {active_visit.patient_id.name} already has an active visit "
                        f"({active_visit.name}). Please complete or cancel the existing visit first."
                    )
        
        return super().create(vals_list)

    # ─────────────────────────────────── State Actions ────────────────────────

    def action_to_waiting(self):
        """Move to queue after triage is complete."""
        self.ensure_one()
        if not self.triage_id:
            raise models.ValidationError(
                'Please complete the Triage assessment before moving to the queue.'
            )
        # Create queue entry
        queue = self.env['hms.queue'].create({
            'visit_id': self.id,
            'patient_id': self.patient_id.id,
            'doctor_id': self.attending_doctor_id.id if self.attending_doctor_id else False,
        })
        self.write({'state': 'waiting', 'queue_id': queue.id})

    def action_start_consultation(self):
        self.ensure_one()
        if self.queue_id:
            self.queue_id.action_call_patient()
        self.write({'state': 'consultation'})

    def action_awaiting_investigation(self):
        self.write({'state': 'investigation'})

    def action_ready_discharge(self):
        self.write({'state': 'discharge'})

    def action_complete(self):
        self.write({'state': 'completed', 'discharge_time': fields.Datetime.now()})
        if self.queue_id:
            self.queue_id.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})
        if self.queue_id:
            self.queue_id.write({'state': 'skipped'})

    def _is_consultation_paid(self):
        """Return True if payer is non-cash OR consultation bill line is paid."""
        self.ensure_one()
        if self.payer_type != 'cash':
            return True
        # Check if the consultation bill line is paid
        Bill = self.env['hms.bill']
        bill = Bill.search([
            ('opd_visit_id', '=', self.id),
            ('state', 'not in', ('cancelled', 'written_off')),
        ], limit=1)
        if not bill:
            return False
        consult_line = bill.line_ids.filtered(
            lambda l: l.source_model == 'hms.opd.visit' and l.source_record_id == self.id
        )
        return bool(consult_line and all(l.is_paid for l in consult_line))

    def action_open_triage(self):
        """Open (or create) the triage record for this visit."""
        self.ensure_one()
        if self.payer_type == 'cash' and not self._is_consultation_paid():
            raise models.ValidationError(
                'Consultation fee has not been paid yet. '
                'Please collect payment before proceeding to triage.'
            )
        if self.triage_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Triage',
                'res_model': 'hms.triage',
                'view_mode': 'form',
                'res_id': self.triage_id.id,
            }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Triage Assessment',
            'res_model': 'hms.triage',
            'view_mode': 'form',
            'context': {
                'default_visit_id': self.id,
                'default_patient_id': self.patient_id.id,
            },
            'target': 'new',
        }

    def action_view_triage_history(self):
        """Open all triage records for this visit."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Triage — {self.name}',
            'res_model': 'hms.triage',
            'view_mode': 'list,form',
            'domain': [('visit_id', '=', self.id)],
            'context': {
                'default_visit_id': self.id,
                'default_patient_id': self.patient_id.id,
            },
        }


class HmsVisitDiagnosis(models.Model):
    """ICD-10 diagnoses linked to an OPD visit. Supports primary + secondary."""
    _name = 'hms.visit.diagnosis'
    _description = 'Visit Diagnosis'
    _order = 'diagnosis_type, icd10_code'

    visit_id = fields.Many2one('hms.opd.visit', required=True, ondelete='cascade')
    icd10_id = fields.Many2one('hms.icd10', 'ICD-10', index=True,
                               help='Pick from the ICD-10 catalogue; fills the code and description.')
    icd10_code = fields.Char('ICD-10 Code')
    description = fields.Char('Diagnosis Description', required=True)

    @api.onchange('icd10_id')
    def _onchange_icd10_id(self):
        if self.icd10_id:
            self.icd10_code = self.icd10_id.code
            if not self.description:
                self.description = self.icd10_id.name
    diagnosis_type = fields.Selection([
        ('primary', 'Primary Diagnosis'),
        ('secondary', 'Secondary / Comorbidity'),
        ('differential', 'Differential Diagnosis'),
    ], 'Type', default='primary', required=True)
    confirmed = fields.Boolean('Confirmed', default=True,
                               help='Uncheck for differential / suspected diagnoses')
    notes = fields.Char('Notes')


class HmsVisitConsultation(models.Model):
    """A consultation charge on an OPD visit. A visit may have several
    (e.g. general clinician then a specialist review in the same encounter).
    Each line raises its own bill line the moment it is added."""
    _name = 'hms.visit.consultation'
    _description = 'OPD Visit Consultation'
    _order = 'consultation_date, id'

    visit_id = fields.Many2one('hms.opd.visit', required=True, ondelete='cascade')
    consultation_product_id = fields.Many2one(
        'product.product', 'Consultation', required=True,
        domain="[('type', '=', 'service'), ('categ_id.complete_name', 'ilike', 'Consultation')]",
        help='Consultation service product. Only products in a Consultation category appear here.')
    clinician_id = fields.Many2one('hr.employee', 'Clinician')
    consultation_date = fields.Datetime('Date/Time', default=fields.Datetime.now, required=True)
    unit_price = fields.Float('Fee (TZS)', digits=(14, 0),
                              compute='_compute_unit_price', store=True, readonly=False)
    chargeable = fields.Boolean('Chargeable', default=True,
                                help='Uncheck for a waived or already-covered consultation.')
    notes = fields.Char('Notes')

    @api.depends('consultation_product_id')
    def _compute_unit_price(self):
        for rec in self:
            if rec.consultation_product_id and not rec.unit_price:
                rec.unit_price = rec.consultation_product_id.list_price
