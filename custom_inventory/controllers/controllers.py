# -*- coding: utf-8 -*-
from odoo import http

# class CustomInventory(http.Controller):
#     @http.route('/custom_inventory/custom_inventory/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_inventory/custom_inventory/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_inventory.listing', {
#             'root': '/custom_inventory/custom_inventory',
#             'objects': http.request.env['custom_inventory.custom_inventory'].search([]),
#         })

#     @http.route('/custom_inventory/custom_inventory/objects/<model("custom_inventory.custom_inventory"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_inventory.object', {
#             'object': obj
#         })