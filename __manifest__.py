
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
    ],
    'data': [
        'security/clinic_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/clinic_patient_views.xml',
        'views/clinic_patient_duplicate_wizard_views.xml',
        'views/clinic_patient_merge_wizard_views.xml',
        'views/clinic_menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
