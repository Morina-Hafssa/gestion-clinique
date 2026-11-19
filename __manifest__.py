
{
    'name': 'Gestion Clinique',
    'version': '18.0.1.0.0',
    'summary': 'Module de gestion de clinique médicale',
    'description': """
        Module de gestion de clinique :
        - Patients (dossier unique, anti-doublon, consentements)
        - Rendez-vous (à venir)
        - Consultations (à venir)
        - Facturation (à venir)
    """,
    'author': 'Clinicsys',
    'category': 'Healthcare',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'base_setup',
        'mail',
        'contacts',
        'calendar',
        'hr'
    ],
    'data': [
        'security/clinic_security.xml',           # 1. groups
        'security/clinic_record_rules.xml',       # 2. record rules (depend on groups)
        'security/ir.model.access.csv',           # 3. ACLs (depend on groups)
        'data/ir_sequence_data.xml',              # 4. sequences
        'views/clinic_patient_views.xml',
        'views/clinic_patient_duplicate_wizard_views.xml',
        'views/clinic_patient_merge_wizard_views.xml',
        'views/clinic_appointment_views.xml',
        'views/clinic_visit_views.xml',
        'views/clinic_queue_views.xml',
        'views/clinic_appointment_wizard_views.xml',
        'views/res_config_settings_views.xml',
        'views/clinic_menus.xml',                 # last (menus reference actions)
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
