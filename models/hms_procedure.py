from odoo import api, fields, models


class HmsProcedure(models.Model):
    """A clinical procedure performed during an OPD encounter (treatment room):
    injection, wound dressing, suturing, nebulisation, catheterisation, etc.

    Billed as a service product; may consume stock items recorded as
    consumable lines. Always attached to an OPD visit (the encounter that
    carries the bill, queue and HMIS attendance)."""
    _name = 'hms.procedure'
    _description = 'Clinical Procedure'
    _inherit = ['mail.thread']
    _order = 'procedure_date desc, id desc'
    _rec_name = 'name'

    name = fields.Char('Procedure No.', readonly=True, copy=False, default='New')
    opd_visit_id = fields.Many2one(
        'hms.opd.visit', 'OPD Visit', required=True, ondelete='cascade', tracking=True)
    patient_id = fields.Many2one(
        related='opd_visit_id.patient_id', string='Patient', store=True, readonly=True)

    procedure_product_id = fields.Many2one(
        'product.product', 'Procedure', required=True,
        domain="[('type', '=', 'service'), ('categ_id.complete_name', 'ilike', 'Procedure')]",
        help='Procedure service product. Only products in a Procedure category appear here.')
    procedure_date = fields.Datetime('Date/Time', default=fields.Datetime.now, required=True)
    performed_by_id = fields.Many2one('hr.employee', 'Performed By')
    quantity = fields.Float('Qty', default=1.0)
    unit_price = fields.Float(
        'Unit Price (TZS)', digits=(14, 0),
        compute='_compute_unit_price', store=True, readonly=False)
    chargeable = fields.Boolean(
        'Chargeable', default=True,
        help='Uncheck for a prepaid course or free service - the procedure is '
             'still recorded, but no bill line is raised.')
    notes = fields.Text('Clinical Notes')

    consumable_line_ids = fields.One2many(
        'hms.procedure.consumable', 'procedure_id', 'Consumables Used')

    state = fields.Selection([
        ('ordered', 'Ordered'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], 'Status', default='ordered', required=True, tracking=True)

    @api.depends('procedure_product_id')
    def _compute_unit_price(self):
        for rec in self:
            if rec.procedure_product_id and not rec.unit_price:
                rec.unit_price = rec.procedure_product_id.list_price

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('hms.procedure') or 'New'
        return super().create(vals_list)

    # ── Workflow ──────────────────────────────────────────────────────────────
    def action_done(self):
        self.write({'state': 'done'})
        self._post_done()

    def _post_done(self):
        """Extension hook. Overridden in:
        - billing  → raise the procedure bill line
        - pharmacy → deduct consumables from stock
        """
        return True

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset(self):
        self.write({'state': 'ordered'})


class HmsProcedureConsumable(models.Model):
    """Stock item (drug / supply) used during a procedure - e.g. syringe, gauze,
    the injectable itself. Pharmacy deducts these from stock on completion."""
    _name = 'hms.procedure.consumable'
    _description = 'Procedure Consumable'

    procedure_id = fields.Many2one('hms.procedure', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Item', required=True)
    quantity = fields.Float('Qty', default=1.0, required=True)
    notes = fields.Char('Notes')


class HmsOpdVisitProcedureExt(models.Model):
    """Add procedures to the OPD encounter."""
    _inherit = 'hms.opd.visit'

    procedure_ids = fields.One2many('hms.procedure', 'opd_visit_id', 'Procedures')
    procedure_count = fields.Integer('Procedures', compute='_compute_procedure_count')

    @api.depends('procedure_ids')
    def _compute_procedure_count(self):
        for rec in self:
            rec.procedure_count = len(rec.procedure_ids)

    def action_view_procedures(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Procedures - %s' % self.name,
            'res_model': 'hms.procedure',
            'view_mode': 'list,form',
            'domain': [('opd_visit_id', '=', self.id)],
            'context': {'default_opd_visit_id': self.id},
        }
