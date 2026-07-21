from odoo import api, fields, models


class HmsQueue(models.Model):
    """
    Digital OPD patient queue.
    One queue entry per visit. Queue numbers reset daily.
    Priority is driven by triage category (Red patients jump the queue).
    """
    _name = 'hms.queue'
    _description = 'OPD Patient Queue'
    _order = 'priority desc, queue_number asc'

    # ── Links ─────────────────────────────────────────────────────────────────
    visit_id = fields.Many2one('hms.opd.visit', 'OPD Visit', required=True, ondelete='cascade')
    patient_id = fields.Many2one('hms.patient', related='visit_id.patient_id',
                                 string='Patient', store=True, readonly=True)
    doctor_id = fields.Many2one('hr.employee', 'Assigned Doctor')

    # ── Queue Number ──────────────────────────────────────────────────────────
    queue_date = fields.Date('Queue Date', default=fields.Date.today, required=True)
    queue_number = fields.Integer('Queue No.', readonly=True)

    # ── Priority (from triage) ────────────────────────────────────────────────
    priority = fields.Integer(
        'Priority', default=2,
        help='5=Red (immediate) → 1=Black. Higher = served first.',
    )
    triage_category = fields.Selection(
        related='visit_id.triage_category', string='Triage', readonly=True
    )

    # ── State & Timestamps ────────────────────────────────────────────────────
    state = fields.Selection([
        ('waiting', 'Waiting'),
        ('called', 'Called / Ready'),
        ('in_progress', 'In Consultation'),
        ('done', 'Done'),
        ('skipped', 'Skipped / No-show'),
    ], 'Status', default='waiting', required=True)

    registered_at = fields.Datetime('Registered At', default=fields.Datetime.now)
    called_at = fields.Datetime('Called At', readonly=True)
    started_at = fields.Datetime('Consultation Start', readonly=True)
    completed_at = fields.Datetime('Completed At', readonly=True)

    # ── Wait Time ─────────────────────────────────────────────────────────────
    wait_minutes = fields.Integer('Wait (min)', compute='_compute_wait', help='Minutes from registration to being called')
    consult_minutes = fields.Integer('Consult (min)', compute='_compute_wait', help='Minutes from called to completed')

    # ─────────────────────────────────── ORM ──────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('queue_number'):
                vals['queue_number'] = self._next_queue_number(
                    vals.get('queue_date', fields.Date.today())
                )
            # Sync priority from visit triage
            if vals.get('visit_id'):
                visit = self.env['hms.opd.visit'].browse(vals['visit_id'])
                if visit.triage_priority:
                    vals['priority'] = visit.triage_priority
        return super().create(vals_list)

    def _next_queue_number(self, queue_date):
        last = self.search([('queue_date', '=', queue_date)], order='queue_number desc', limit=1)
        return (last.queue_number + 1) if last else 1

    # ─────────────────────────────────── Computes ─────────────────────────────

    def _compute_wait(self):
        for rec in self:
            if rec.registered_at and rec.called_at:
                delta = rec.called_at - rec.registered_at
                rec.wait_minutes = int(delta.total_seconds() / 60)
            else:
                rec.wait_minutes = 0
            if rec.called_at and rec.completed_at:
                delta = rec.completed_at - rec.called_at
                rec.consult_minutes = int(delta.total_seconds() / 60)
            else:
                rec.consult_minutes = 0

    # ─────────────────────────────────── Actions ──────────────────────────────

    def action_call_patient(self):
        self.write({'state': 'called', 'called_at': fields.Datetime.now()})

    def action_start_consult(self):
        self.write({'state': 'in_progress', 'started_at': fields.Datetime.now()})

    def action_done(self):
        self.write({'state': 'done', 'completed_at': fields.Datetime.now()})

    def action_skip(self):
        self.write({'state': 'skipped'})
