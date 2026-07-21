from odoo import api, fields, models
from odoo.exceptions import UserError

# Departments that keep their own store. Each maps to a stock location xmlid,
# resolved at runtime (no hard module dependency needed).
DEPARTMENTS = [
    ('opd', 'OPD'),
    ('ipd', 'IPD Ward'),
    ('rch', 'RCH'),
]
DEPT_STORE_XMLID = {
    'opd': 'nest_hms_opd.location_opd_store',
    'ipd': 'nest_hms_ipd.location_ward_store',
    'rch': 'nest_hms_rch.location_rch_store',
}


class HmsDeptRequisition(models.Model):
    """One requisition used by every department (OPD, IPD ward, RCH). Each
    department still raises its own requests into its own store, but a request
    line can be ANY stockable product - medications, consumables or commodities -
    pulled from the central/pharmacy store."""
    _name = 'hms.dept.requisition'
    _description = 'Department Stock Requisition'
    _inherit = ['mail.thread']
    _order = 'id desc'
    _rec_name = 'name'

    name = fields.Char('Reference', readonly=True, copy=False, default='New')
    department = fields.Selection(
        DEPARTMENTS, string='Department', required=True, tracking=True,
        default=lambda s: s.env.context.get('default_department', 'opd'))
    requisition_date = fields.Datetime('Date', default=fields.Datetime.now, required=True)
    source_location_id = fields.Many2one(
        'stock.location', 'Supply From', required=True,
        default=lambda s: s._default_source_location())
    destination_location_id = fields.Many2one(
        'stock.location', 'Deliver To (Dept Store)', required=True,
        compute='_compute_destination', store=True, readonly=False, precompute=True)
    line_ids = fields.One2many('hms.dept.requisition.line', 'requisition_id', 'Items')
    picking_id = fields.Many2one('stock.picking', 'Transfer', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Submitted'), ('approved', 'Approved'),
        ('transferred', 'Received'), ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True)

    @api.model
    def _store_for_department(self, dept):
        xmlid = DEPT_STORE_XMLID.get(dept)
        return self.env.ref(xmlid, raise_if_not_found=False) if xmlid else False

    @api.depends('department')
    def _compute_destination(self):
        for rec in self:
            loc = rec._store_for_department(rec.department)
            if loc:
                rec.destination_location_id = loc

    def _default_source_location(self):
        company = self.env.company
        if 'central_store_location_id' in company._fields and company.central_store_location_id:
            return company.central_store_location_id
        wh = self.env['stock.warehouse'].sudo().search([('name', 'ilike', 'central')], limit=1)
        if wh and wh.lot_stock_id:
            return wh.lot_stock_id
        return self.env['stock.location'].sudo().search(
            [('usage', '=', 'internal'), ('name', 'ilike', 'central')], limit=1)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('hms.dept.requisition') or 'New'
        return super().create(vals_list)

    def action_submit(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError("Add at least one item before submitting.")
        self.state = 'submitted'

    def action_approve(self):
        self.ensure_one()
        if self.state != 'submitted':
            raise UserError("Only submitted requisitions can be approved.")
        picking_type = self.env['stock.picking.type'].sudo().search([
            ('code', '=', 'internal'), ('company_id', '=', self.env.company.id)], limit=1)
        if not picking_type:
            raise UserError("No internal transfer operation type found. Configure your warehouse.")
        move_vals = []
        for ln in self.line_ids:
            product = ln.product_id
            qty = ln.quantity_approved or ln.quantity_requested
            if not product or qty <= 0:
                continue
            move_vals.append((0, 0, {
                'name': product.name,
                'product_id': product.id,
                'product_uom_qty': qty,
                'product_uom': product.uom_id.id,
                'location_id': self.source_location_id.id,
                'location_dest_id': self.destination_location_id.id,
            }))
        if not move_vals:
            raise UserError("Nothing to transfer - set quantities.")
        picking = self.env['stock.picking'].sudo().create({
            'picking_type_id': picking_type.id,
            'location_id': self.source_location_id.id,
            'location_dest_id': self.destination_location_id.id,
            'origin': self.name,
            'move_ids': move_vals,
        })
        picking.sudo().action_confirm()
        self.picking_id = picking
        self.state = 'approved'
        self.message_post(body="Approved. Internal transfer %s created." % picking.name)

    def action_receive(self):
        self.ensure_one()
        if self.state != 'approved' or not self.picking_id:
            raise UserError("Approve the requisition first.")
        picking = self.picking_id.sudo()
        picking.action_assign()
        for ml in picking.move_line_ids:
            if not ml.quantity:
                ml.quantity = ml.reserved_qty or ml.move_id.product_uom_qty
        picking.with_context(skip_backorder=True, skip_immediate=True,
                             immediate_transfer=True).button_validate()
        self.state = 'transferred'
        self.message_post(body="Stock received into %s." % self.destination_location_id.name)

    def action_cancel(self):
        self.ensure_one()
        if self.picking_id and self.picking_id.state not in ('done', 'cancel'):
            self.picking_id.action_cancel()
        self.state = 'cancelled'

    def action_view_transfer(self):
        self.ensure_one()
        if not self.picking_id:
            return False
        return {
            'type': 'ir.actions.act_window', 'res_model': 'stock.picking',
            'res_id': self.picking_id.id, 'view_mode': 'form', 'target': 'current',
        }


class HmsDeptRequisitionLine(models.Model):
    _name = 'hms.dept.requisition.line'
    _description = 'Department Requisition Line'

    requisition_id = fields.Many2one('hms.dept.requisition', required=True, ondelete='cascade')
    product_id = fields.Many2one(
        'product.product', 'Product', required=True,
        domain=[('type', '=', 'consu')],
        help='Any stockable item - medication, consumable or commodity.')
    quantity_requested = fields.Float('Qty Requested', default=1.0)
    quantity_approved = fields.Float('Qty Approved', help='Leave 0 to approve the full requested qty.')
    quantity_available = fields.Float('Available in Source', compute='_compute_avail')

    @api.depends('product_id', 'requisition_id.source_location_id')
    def _compute_avail(self):
        Quant = self.env['stock.quant']
        for ln in self:
            if ln.product_id and ln.requisition_id.source_location_id:
                q = Quant.sudo().search([
                    ('product_id', '=', ln.product_id.id),
                    ('location_id', 'child_of', ln.requisition_id.source_location_id.id)])
                ln.quantity_available = sum(q.mapped('quantity'))
            else:
                ln.quantity_available = 0.0
