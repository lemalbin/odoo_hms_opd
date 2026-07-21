from odoo import api, fields, models


class HmsVisitType(models.Model):
    """Registry of visit / encounter types launchable from the patient hub.

    Each record points to a target model by NAME (e.g. hms.opd.visit,
    hms.dental.visit) so the patient form can launch any department's visit
    form WITHOUT a code dependency on that department. Add one record per
    department from Configuration > Visit Types once its model exists; types
    whose module is not installed simply do not appear."""
    _name = 'hms.visit.type'
    _description = 'HMS Visit Type'
    _order = 'sequence, name'

    name = fields.Char('Visit Type', required=True, translate=True)
    res_model = fields.Char(
        'Target Model', required=True,
        help='Technical model opened for this visit, e.g. hms.opd.visit, '
             'hms.dental.visit, hms.mortuary.admission')
    icon = fields.Char('Icon', default='fa-stethoscope',
                       help='Font Awesome icon, e.g. fa-tooth, fa-ambulance, fa-heartbeat')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    note = fields.Char('Description')
    is_available = fields.Boolean('Installed', compute='_compute_is_available',
                                  search='_search_is_available',
                                  help='True when the target model exists in this database.')

    @api.depends('res_model')
    def _compute_is_available(self):
        for rec in self:
            rec.is_available = bool(rec.res_model) and rec.res_model in self.env.registry.models

    def _search_is_available(self, operator, value):
        # Evaluate the (non-stored) availability live so it always reflects
        # which department modules are actually installed right now.
        available = self.with_context(active_test=False).search([]).filtered('is_available')
        match = available.ids if value else []
        if operator in ('!=', '<>'):
            match = (self.search([]) - available).ids
        return [('id', 'in', match)]


class HmsPatientVisitHub(models.Model):
    """Add the 'New Visit' launcher entry point to the patient form."""
    _inherit = 'hms.patient'

    def action_open_visit_launcher(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Register Visit',
            'res_model': 'hms.visit.launcher',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_patient_id': self.id},
        }
