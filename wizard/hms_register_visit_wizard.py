from odoo import api, fields, models


class HmsRegisterVisitWizard(models.TransientModel):
    """
    Quick-registration wizard launched from the reception desk.
    Searches existing patients first, creates a new patient if not found,
    then opens a new OPD visit in one flow.
    """
    _name = 'hms.register.visit.wizard'
    _description = 'Quick Register OPD Visit'

    # ── Step 1: Find or create patient ───────────────────────────────────────
    search_phone = fields.Char('Phone / NHIF No.', help='Search by phone or NHIF number')
    patient_id = fields.Many2one('hms.patient', 'Patient')
    is_new_patient = fields.Boolean('New Patient?')

    # New patient fields (only if is_new_patient)
    new_name = fields.Char('Full Name')
    new_dob = fields.Date('Date of Birth')
    new_gender = fields.Selection([
        ('male', 'Male'), ('female', 'Female'), ('other', 'Other')
    ], 'Gender')
    new_phone = fields.Char('Phone (M-Pesa)')
    new_id_type = fields.Selection([
        ('national_id', 'National ID (NIDA)'),
        ('passport', 'Passport'),
        ('voter_id', 'Voter Card'),
        ('birth_cert', 'Birth Certificate'),
    ], 'ID Type', default='national_id')
    new_id_number = fields.Char('ID Number')
    new_nhif_number = fields.Char('NHIF Number')

    # ── Step 2: Visit Details ─────────────────────────────────────────────────
    visit_type = fields.Selection([
        ('new', 'New Patient'),
        ('return', 'Return Visit'),
        ('referral_in', 'Referral In'),
        ('emergency', 'Emergency'),
        ('anc', 'ANC / Maternity'),
        ('corporate', 'Corporate Visit'),
    ], 'Visit Type', default='new', required=True)
    department = fields.Selection([
        ('general', 'General OPD'),
        ('paediatric', 'Paediatric OPD'),
        ('maternity', 'Maternity / ANC'),
        ('emergency', 'Emergency / A&E'),
        ('specialist', 'Specialist Clinic'),
    ], 'Department', default='general', required=True)
    attending_doctor_id = fields.Many2one('hr.employee', 'Preferred Doctor')
    chief_complaint = fields.Text('Chief Complaint')

    # ─────────────────────────────────── Methods ──────────────────────────────

    @api.onchange('search_phone')
    def _onchange_search_phone(self):
        if self.search_phone:
            patient = self.env['hms.patient'].search([
                '|',
                ('phone', 'ilike', self.search_phone),
                ('nhif_number', '=', self.search_phone),
            ], limit=1)
            if patient:
                self.patient_id = patient
                self.visit_type = 'return'
                self.is_new_patient = False
            else:
                self.patient_id = False
                self.is_new_patient = True
                self.new_phone = self.search_phone
                self.visit_type = 'new'

    @api.onchange('patient_id')
    def _onchange_patient_id(self):
        if self.patient_id:
            self.is_new_patient = False
            visit_count = self.env['hms.opd.visit'].search_count(
                [('patient_id', '=', self.patient_id.id)]
            )
            self.visit_type = 'return' if visit_count > 0 else 'new'

    def action_register(self):
        """Create patient if new, then create OPD visit and open it."""
        self.ensure_one()

        # 1. Resolve patient
        if self.is_new_patient:
            if not self.new_name or not self.new_gender or not self.new_phone:
                raise models.ValidationError(
                    'Please provide at minimum: Full Name, Gender and Phone Number for the new patient.'
                )
            patient = self.env['hms.patient'].create({
                'name': self.new_name,
                'date_of_birth': self.new_dob,
                'gender': self.new_gender,
                'phone': self.new_phone,
                'id_type': self.new_id_type,
                'id_number': self.new_id_number,
                'nhif_number': self.new_nhif_number,
                'state': 'active',
            })
        else:
            patient = self.patient_id
            if not patient:
                raise models.ValidationError('Please select or register a patient.')

        # 2. Create OPD visit
        visit_vals = {
            'patient_id': patient.id,
            'visit_type': self.visit_type,
            'department': self.department,
            'attending_doctor_id': self.attending_doctor_id.id if self.attending_doctor_id else False,
            'chief_complaint': self.chief_complaint,
        }
        visit = self.env['hms.opd.visit'].create(visit_vals)

        # 3. Open the visit form
        return {
            'type': 'ir.actions.act_window',
            'name': 'OPD Visit',
            'res_model': 'hms.opd.visit',
            'view_mode': 'form',
            'res_id': visit.id,
        }
