{
    'name': 'nestHMS - OPD & Patient Registration',
    'version': '18.0.1.0.0',
    'category': 'Healthcare',
    'summary': 'Full OPD & Patient Registration — Hospital, Tanzania',
    'description': """
        nestHMS OPD Module
        ==================
        Covers the complete Outpatient Department workflow:
        - Patient master record (Tanzania-specific fields, NHIF/CHF, regions)
        - OPD visit lifecycle: Registration → Triage → Queue → Consultation → Discharge
        - Triage with 5-level colour coding (Red/Yellow/Orange/Green/Black)
        - Digital patient queue with wait-time tracking
        - Vital signs capture per visit
        - ICD-10 diagnosis recording
        - Insurance (NHIF, CHF + private) and corporate payer support
        - Paediatric and geriatric auto-flagging
        - Tanzania 31-region administrative structure
    """,
    'author': 'Codenest Tanzania',
    'depends': ['mail', 'hr', 'product', 'stock'],
    'data': [
        # 1. Groups first
        'security/hms_opd_security.xml',
        # 2. Access rights
        'security/ir.model.access.csv',
        # 3. Master data
        'data/hms_sequence_data.xml',
        'data/hms_county_data.xml',
        'data/hms_insurance_data.xml',
        'data/hms_service_data.xml',
        'data/hms_visit_type_data.xml',
        'data/hms_icd10_data.xml',
        'data/hms_opd_store_data.xml',
        # 4. Views
        'views/hms_hr_views.xml',
        'views/hms_master_views.xml',
        'views/hms_queue_views.xml',
        'views/hms_triage_views.xml',
        'views/hms_opd_visit_views.xml',
        'views/hms_patient_views.xml',
        'views/hms_patient_snapshot_views.xml',
        'views/menu_views.xml',
        'views/hms_procedure_views.xml',
        'views/hms_service_views.xml',
        'views/hms_dept_requisition_views.xml',
        'views/hms_opd_consumable_views.xml',
        'views/hms_visit_type_views.xml',
        'views/hms_icd10_views.xml',
        'wizard/hms_register_visit_wizard_views.xml',
        'wizard/hms_visit_launcher_views.xml',
    ],
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}
