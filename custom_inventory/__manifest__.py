# -*- coding: utf-8 -*-
{
    'name': "custom_inventory",

    'summary': """
        Inventory Adjustment function and report""",

    'description': """
        Inventory Adjustment function and report
    """,

    'author': "Ropo John Olatujoye, +2348086180775",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Inventory Customization',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'stock', 'product_brand', 'product_expiry'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/custom_inventory_view.xml',
        'report/custom_inventory_report.xml',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}