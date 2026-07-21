from markupsafe import Markup, escape

from odoo import api, fields, models


# Small inline-styled building blocks so the snapshot reads like a dashboard
# without needing external CSS.
_CARD = ('<div style="border:1px solid #d9e1e2;border-radius:6px;margin:0 0 12px 0;'
         'overflow:hidden;">')
_HEAD = ('<div style="background:#2f7f8f;color:#fff;padding:6px 10px;font-weight:600;">'
         '{title}</div>')
_BODY = '<div style="padding:8px 10px;">{body}</div>'


class HmsPatientSnapshot(models.Model):
    """Read-only 'one-glance' clinical snapshot of a patient, aggregating data
    from OPD plus any installed clinical module (lab, radiology, pharmacy).
    Rendered as an HTML field on a dedicated view; existing pages are untouched."""
    _inherit = 'hms.patient'

    clinical_snapshot = fields.Html(
        'Clinical Snapshot', compute='_compute_clinical_snapshot', sanitize=False)

    # ── helpers ───────────────────────────────────────────────────────────
    def _snap_card(self, title, body):
        if not body:
            body = Markup('<span style="color:#888;">None recorded.</span>')
        html = _CARD + _HEAD.format(title=escape(title)) + _BODY.format(body='{body}') + '</div>'
        return Markup(html).format(body=body)

    def _snap_rows(self, rows):
        """rows: list of (label, value) tuples -> definition-style HTML."""
        out = Markup('')
        for label, value in rows:
            out += Markup(
                '<div style="display:flex;justify-content:space-between;'
                'padding:2px 0;border-bottom:1px dotted #eee;">'
                '<span style="color:#555;">%s</span><span>%s</span></div>'
            ) % (escape(label), escape('' if value is None else value))
        return out

    # ── compute ───────────────────────────────────────────────────────────
    def _compute_clinical_snapshot(self):
        for rec in self:
            rec.clinical_snapshot = rec._build_snapshot()

    def _build_snapshot(self):
        self.ensure_one()
        env = self.env
        left, right = Markup(''), Markup('')

        # Allergies banner
        banner = Markup('')
        if self.allergy_ids:
            allergens = ', '.join(self.allergy_ids.mapped('allergen'))
            banner = Markup(
                '<div style="background:#f8d7da;color:#842029;border:1px solid #f5c2c7;'
                'border-radius:6px;padding:6px 10px;margin-bottom:12px;">'
                '<b>Allergy alert:</b> %s</div>') % escape(allergens)

        visits = self.opd_visit_ids.sorted('visit_date', reverse=True)

        # ── Diagnoses (across visits) ──
        diag_body = Markup('')
        diags = visits.mapped('diagnosis_ids')
        for d in diags[:12]:
            code = ('%s ' % d.icd10_code) if d.icd10_code else ''
            diag_body += Markup(
                '<div style="padding:3px 0;border-bottom:1px dotted #eee;">'
                '<b>%s%s</b> <span style="color:#888;">(%s%s)</span></div>'
            ) % (escape(code), escape(d.description or ''),
                 escape(dict(d._fields['diagnosis_type'].selection).get(d.diagnosis_type, '')),
                 Markup(', confirmed') if d.confirmed else Markup(''))
        left += self._snap_card('Diagnoses', diag_body)

        # ── Latest vitals (from most recent triage) ──
        vit_body = Markup('')
        tri = visits.mapped('triage_id')[:1]
        if tri:
            t = tri[0]
            vit_body = self._snap_rows([
                ('Blood Pressure', '%s/%s mmHg' % (t.bp_systolic or 0, t.bp_diastolic or 0)),
                ('Temperature', '%.1f C' % (t.temperature or 0)),
                ('Pulse', '%s /min' % (t.pulse or 0)),
                ('Resp. Rate', '%s /min' % (t.respiratory_rate or 0)),
                ('SpO2', '%.0f %%' % (t.spo2 or 0)),
                ('Weight', '%.1f kg' % (t.weight or 0)),
            ])
        left += self._snap_card('Latest Vitals', vit_body)

        # ── Radiology (if module installed) ──
        if 'hms.radiology.request' in env:
            rad_body = Markup('')
            for r in env['hms.radiology.request'].search(
                    [('patient_id', '=', self.id)], order='id desc', limit=8):
                rad_body += Markup(
                    '<div style="padding:3px 0;border-bottom:1px dotted #eee;">%s '
                    '<span style="color:#888;">(%s)</span></div>'
                ) % (escape(r.study_id.name or r.modality_id.name or 'Imaging'),
                     escape(r.state or ''))
            left += self._snap_card('Radiology Orders', rad_body)

        # ── Visits ──
        vis_body = Markup('')
        for v in visits[:8]:
            vtype = dict(v._fields['visit_type'].selection).get(v.visit_type, '')
            vis_body += Markup(
                '<div style="padding:3px 0;border-bottom:1px dotted #eee;">'
                '<b>%s</b> &nbsp; <span style="color:#888;">%s - %s</span></div>'
            ) % (escape(v.visit_date), escape(vtype), escape(v.state or ''))
        right += self._snap_card('Visits', vis_body)

        # ── Lab results (if module installed) ──
        if 'hms.lab.request' in env:
            lab_body = Markup('')
            for req in env['hms.lab.request'].search(
                    [('patient_id', '=', self.id)], order='id desc', limit=8):
                tests = ', '.join(req.test_line_ids.mapped('test_id.name'))
                lab_body += Markup(
                    '<div style="padding:3px 0;border-bottom:1px dotted #eee;">'
                    '<b>%s</b> <span style="color:#888;">%s</span><br/>'
                    '<span style="font-size:12px;">%s</span></div>'
                ) % (escape(req.name or ''), escape(req.state or ''), escape(tests))
            right += self._snap_card('Lab Results', lab_body)

        # ── Treatments / Medications (if pharmacy installed) ──
        if 'hms.prescription' in env:
            rx_body = Markup('')
            rxs = env['hms.prescription'].search(
                [('patient_id', '=', self.id)], order='id desc', limit=5)
            for line in rxs.mapped('line_ids')[:15] if 'line_ids' in env['hms.prescription']._fields else []:
                rx_body += Markup(
                    '<div style="padding:3px 0;border-bottom:1px dotted #eee;">'
                    '<b>%s</b> <span style="color:#888;">%s %s</span></div>'
                ) % (escape(line.drug_id.name if 'drug_id' in line._fields and line.drug_id else ''),
                     escape(getattr(line, 'frequency', '') or ''),
                     escape('x %s d' % getattr(line, 'duration_days', '') if getattr(line, 'duration_days', 0) else ''))
            right += self._snap_card('Treatments', rx_body)

        # ── Disposition (latest visit) ──
        disp_body = Markup('')
        if visits and visits[0].discharge_summary:
            disp_body = escape(visits[0].discharge_summary)
        right += self._snap_card('Disposition', disp_body)

        grid = Markup(
            '<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">'
            '<div>%s</div><div>%s</div></div>') % (left, right)
        return banner + grid

    # ── entry point from the patient form ────────────────────────────────
    def action_open_snapshot(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Clinical Snapshot - %s' % (self.name or ''),
            'res_model': 'hms.patient',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(self.env.ref('nest_hms_opd.view_hms_patient_snapshot').id, 'form')],
            'target': 'current',
        }
