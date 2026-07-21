from odoo import api, fields, models
from odoo.exceptions import UserError

CONSUMABLE_CATEGORIES = [
    ('ppe', 'PPE (gloves, masks, gowns)'),
    ('iv', 'IV / Infusion'),
    ('dressing', 'Dressing / Wound Care'),
    ('syringe', 'Syringes / Needles'),
    ('catheter', 'Catheters / Tubes'),
    ('other', 'Other Sundry'),
]


class HmsOpdConsumable(models.Model):
    """OPD consumable / sundry (gloves, syringes, dressings…) kept in an OPD
    store: request stock from the central store, see levels, and it is deducted
    (and optionally billed) when used on an OPD visit."""
    _name = 'hms.opd.consumable'
    _description = 'OPD Consumable / Sundry'
    _order = 'name'

    name = fields.Char('Consumable', required=True)
    code = fields.Char('Code')
    category = fields.Selection(CONSUMABLE_CATEGORIES, default='other', required=True)
    product_id = fields.Many2one('product.product', 'Stock Product', copy=False,
        help='Storable product used for stock. Auto-created when the consumable is created.')
    unit = fields.Char('Unit', default='unit')
    track_expiry = fields.Boolean('Track Lot / Expiry')
    reorder_level = fields.Float('Reorder Level', default=0.0)
    qty_available = fields.Float('On Hand (OPD Store)', compute='_compute_qty_available')
    below_reorder = fields.Boolean('Low Stock', compute='_compute_qty_available')
    active = fields.Boolean(default=True)

    @api.model
    def _get_opd_store_location(self):
        return self.env.ref('nest_hms_opd.location_opd_store', raise_if_not_found=False)

    def _compute_qty_available(self):
        loc = self._get_opd_store_location()
        Quant = self.env['stock.quant']
        for rec in self:
            if rec.product_id and loc:
                quants = Quant.sudo().search([
                    ('product_id', '=', rec.product_id.id),
                    ('location_id', 'child_of', loc.id)])
                rec.qty_available = sum(quants.mapped('quantity'))
            else:
                rec.qty_available = 0.0
            rec.below_reorder = rec.reorder_level > 0 and rec.qty_available <= rec.reorder_level

    def _build_product_vals(self):
        self.ensure_one()
        categ = self.env.ref('nest_hms_opd.prod_categ_opd_consumables', raise_if_not_found=False)
        vals = {
            'name': self.name,
            'type': 'consu',
            'is_storable': True,
            'sale_ok': False,   # consumables are not billed - stock/usage tracking only
            'purchase_ok': True,
        }
        if self.code:
            vals['default_code'] = self.code
        if categ:
            vals['categ_id'] = categ.id
        if self.track_expiry:
            vals.update({'tracking': 'lot', 'use_expiration_date': True})
        return vals

    def _ensure_product(self):
        self.ensure_one()
        if not self.product_id:
            tmpl = self.env['product.template'].sudo().create(self._build_product_vals())
            self.product_id = tmpl.product_variant_id
        return self.product_id

    def action_create_product(self):
        for rec in self:
            rec._ensure_product()
        return True

    def action_view_stock_moves(self):
        """Completed stock moves for this consumable at the OPD store - both what
        came IN (requisition receipts) and what went OUT (used on visits)."""
        self.ensure_one()
        loc = self._get_opd_store_location()
        if not self.product_id or not loc:
            raise UserError("Create the stock product first.")
        return {
            'type': 'ir.actions.act_window',
            'name': 'Stock History - %s' % self.name,
            'res_model': 'stock.move.line',
            'view_mode': 'list',
            'domain': ['&', '&',
                       ('product_id', '=', self.product_id.id),
                       ('state', '=', 'done'),
                       '|', ('location_id', 'child_of', loc.id),
                            ('location_dest_id', 'child_of', loc.id)],
            'context': {'create': False, 'edit': False},
        }

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if not rec.product_id:
                rec._ensure_product()
        return records


class HmsOpdVisitConsumable(models.Model):
    """An OPD consumable used on a visit. Recording it deducts stock from the OPD
    store; billing (if chargeable) is added by nest_hms_billing."""
    _name = 'hms.opd.visit.consumable'
    _description = 'OPD Consumable Used'
    _order = 'date_used desc, id desc'

    visit_id = fields.Many2one('hms.opd.visit', required=True, ondelete='cascade')
    patient_id = fields.Many2one(related='visit_id.patient_id', store=True, readonly=True)
    consumable_id = fields.Many2one('hms.opd.consumable', 'Consumable', required=True)
    quantity = fields.Float('Qty', default=1.0, required=True)
    date_used = fields.Datetime('Used At', default=fields.Datetime.now)
    picking_id = fields.Many2one('stock.picking', 'Stock Issue', readonly=True)
    note = fields.Char('Note')

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec._deduct_stock()
        return records

    def _deduct_stock(self):
        self.ensure_one()
        consumable = self.consumable_id
        product = consumable.product_id
        loc = consumable._get_opd_store_location()
        qty = self.quantity or 1.0
        if not product or not loc:
            return
        if consumable.qty_available < qty:
            self.note = (self.note or '') + ' [insufficient stock - not deducted]'
            return
        customer_loc = self.env.ref('stock.stock_location_customers', raise_if_not_found=False)
        picking_type = self.env['stock.picking.type'].sudo().search([
            ('code', '=', 'outgoing'), ('company_id', '=', self.env.company.id)], limit=1)
        if not customer_loc or not picking_type:
            return
        picking = self.env['stock.picking'].sudo().create({
            'picking_type_id': picking_type.id,
            'location_id': loc.id,
            'location_dest_id': customer_loc.id,
            'origin': 'OPD: %s' % (self.visit_id.name or ''),
            'move_ids': [(0, 0, {
                'name': consumable.name,
                'product_id': product.id,
                'product_uom_qty': qty,
                'product_uom': product.uom_id.id,
                'location_id': loc.id,
                'location_dest_id': customer_loc.id,
            })],
        })
        picking.sudo().action_confirm()
        picking.sudo().action_assign()
        for ml in picking.move_line_ids:
            if not ml.quantity:
                ml.quantity = ml.reserved_qty or ml.move_id.product_uom_qty
            if product.tracking != 'none' and not ml.lot_id:
                lot = self._pick_fefo_lot(product, loc)
                if lot:
                    ml.lot_id = lot.id
        picking.sudo().with_context(skip_backorder=True, skip_immediate=True,
                                    immediate_transfer=True).button_validate()
        self.picking_id = picking.id

    def _pick_fefo_lot(self, product, loc):
        quants = self.env['stock.quant'].sudo().search([
            ('product_id', '=', product.id),
            ('location_id', 'child_of', loc.id),
            ('quantity', '>', 0),
            ('lot_id', '!=', False)])
        quants = quants.sorted(
            key=lambda q: (q.lot_id.expiration_date or fields.Datetime.now()))
        return quants[:1].lot_id


class HmsOpdVisitConsumableExt(models.Model):
    _inherit = 'hms.opd.visit'

    consumable_ids = fields.One2many('hms.opd.visit.consumable', 'visit_id', 'Consumables Used')
