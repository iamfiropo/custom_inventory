# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class custom_inventory(models.Model):
    _inherit = 'stock.inventory'

    @api.multi
    def reset(self):
        empty_obj = self.env[self._name]

        for key, value in self._fields.iteritems():
            if value.name not in models.MAGIC_COLUMNS:
                setattr(self, key, getattr(empty_obj, key))

    # Override and Change required to false
    filter = fields.Selection(
        string='Inventory of', selection='_selection_filter',
        required=False,
        default='none',
        help="If you do an entire inventory, you can choose 'All Products' and it will prefill the inventory with the current stock.  If you only do some products  "
             "(e.g. Cycle Counting) you can choose 'Manual Selection of Products' and the system won't propose anything.  You can also let the "
             "system propose for a single product / lot /... ")

    # Add boolean fields
    filter_all = fields.Boolean(string='All products', default=True)
    filter_category = fields.Boolean(string='One product category')
    filter_only = fields.Boolean(string='One product only')
    filter_partial = fields.Boolean(string='Select products manually')
    filter_lot = fields.Boolean(string='One Lot/Serial Number')
    filter_supplier = fields.Boolean(string='Supplier')
    filter_brand = fields.Boolean(string='Brand')
    is_exhausted = fields.Boolean(string='Is Exhausted')

    supplier = fields.Many2one('res.partner', 'Vendor')
    product_brand_id = fields.Many2one('product.brand', 'Brand')

    lot_id = fields.Many2one(
        'stock.production.lot', 'Inventoried Lot/Serial Number',
        readonly=True,
        states={'draft': [('readonly', False)]},
        help="Specify Lot/Serial Number to focus your inventory on a particular Lot/Serial Number.")


    @api.onchange('filter_all','filter_category')
    def _onchange_filt(self):
        if self.filter_all == True:
            self.is_exhausted = True
        elif self.filter_category == True:
            self.is_exhausted = True
        else:
            self.is_exhausted = False

    @api.one
    @api.constrains('filter', 'product_id', 'lot_id', 'partner_id', 'package_id')
    def _check_filter_product(self):
        pass


    @api.multi
    def action_start(self, values):
        for inventory in self.filtered(lambda x: x.state not in ('done','cancel')):
            vals = {'state': 'confirm', 'date': fields.Datetime.now()}
            if (inventory.filter_partial != True) and not inventory.line_ids:
                vals.update({'line_ids': [(0, 0, line_values) for line_values in inventory._get_inventory_lines_values()]})
            inventory.write(vals)
        return True

    def _get_inventory_lines_values(self):
        # TDE CLEANME: is sql really necessary ? I don't think so
        locations = self.env['stock.location'].search([('id', 'child_of', [self.location_id.id])])
        domain = ' location_id in %s AND active = TRUE'
        args = (tuple(locations.ids),)

        vals = []
        Product = self.env['product.product']
        # Empty recordset of products available in stock_quants
        quant_products = self.env['product.product']
        # Empty recordset of products to filter
        products_to_filter = self.env['product.product']

        # case 0: Filter on company
        if self.company_id:
            domain += ' AND company_id = %s'
            args += (self.company_id.id,)

        # case 1: Filter on One owner only or One product for a specific owner
        if self.partner_id:
            domain += ' AND owner_id = %s'
            args += (self.partner_id.id,)
        # case 2: Filter on One Lot/Serial Number
        if self.lot_id:
            domain += ' AND lot_id = %s'
            args += (self.lot_id.id,)
        # case 3: Filter on One product
        if self.product_id:
            domain += ' AND product_id = %s'
            args += (self.product_id.id,)
            products_to_filter |= self.product_id
        # case 4: Filter on A Pack
        if self.package_id:
            domain += ' AND package_id = %s'
            args += (self.package_id.id,)
        # case 5: Filter on A Vendor
        if self.supplier:
            domain += ' AND supplier = %s'
            args += (self.supplier.id,)
        # case 6: Filter on A Brand
        if self.product_brand_id:
            domain += ' AND product_brand_id = %s'
            args += (self.product_brand_id.id,)
        # case 7: Filter on One product category + Exahausted Products
        if self.category_id:
            categ_products = Product.search([('categ_id', '=', self.category_id.id)])
            domain += ' AND product_id = ANY (%s)'
            args += (categ_products.ids,)
            products_to_filter |= categ_products

        self.env.cr.execute("""SELECT product_id, sum(quantity) as product_qty, supplier as vendor, product_brand_id as Brand, location_id, lot_id as prod_lot_id, package_id, owner_id as partner_id
                            FROM stock_quant
                            LEFT JOIN product_product
                            ON product_product.id = stock_quant.product_id
                            WHERE %s
                            GROUP BY product_id, location_id, supplier, product_brand_id, lot_id, package_id, partner_id """ % domain,
                            args)

        for product_data in self.env.cr.dictfetchall():
            # replace the None the dictionary by False, because falsy values are tested later on
            for void_field in [item[0] for item in product_data.items() if item[1] is None]:
                product_data[void_field] = False
            product_data['theoretical_qty'] = product_data['product_qty']
            if product_data['product_id']:
                product_data['product_uom_id'] = Product.browse(product_data['product_id']).uom_id.id
                quant_products |= Product.browse(product_data['product_id'])
            vals.append(product_data)
        if self.exhausted:
            exhausted_vals = self._get_exhausted_inventory_line(products_to_filter, quant_products)
            vals.extend(exhausted_vals)
        return vals

class InventoryLine(models.Model):
    _inherit = 'stock.inventory.line'

    supplier = fields.Many2one('res.partner', 'Vendor')
    product_brand_id = fields.Many2one('product.brand', 'Brand')

    cg_id = fields.Many2one('product.category', string='Category', related='product_id.categ_id', store=True)

    expiry = fields.Datetime(
        'Expiry Date', related='prod_lot_id.life_date', store=True)
    value = fields.Float(
        'Value (Of Difference)', compute='_compute_value_of_difference',
        readonly=True)

    # pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', required=True, readonly=True,
    #                                states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
    #                                help="Pricelist for current sales order.")
    # currency_id = fields.Many2one("res.currency", related='pricelist_id.currency_id', string="Currency", readonly=True,
    #                               required=True)

    # cost price to calculate value of difference
    cost_price = fields.Float(related='product_id.standard_price')

    # Value of difference computation
    @api.one
    @api.depends('theoretical_qty', 'product_qty')
    def _compute_value_of_difference(self):
        dif = self.product_qty - self.theoretical_qty
        self.value = dif * self.cost_price

    # @api.model
    # def create(self, values):
    #     values.pop('product_name', False)
    #     if 'product_id' in values and 'product_uom_id' not in values:
    #         values['product_uom_id'] = self.env['product.product'].browse(values['product_id']).uom_id.id
    #     existings = self.search([
    #         ('product_id', '=', values.get('product_id')),
    #         ('inventory_id.state', '=', 'confirm'),
    #         ('location_id', '=', values.get('location_id')),
    #         ('partner_id', '=', values.get('partner_id')),
    #         ('supplier', '=', values.get('supplier')),
    #         ('product_brand_id', '=', values.get('product_brand_id')),
    #         ('package_id', '=', values.get('package_id')),
    #         # ('lot_serial_no', '=', values.get('lot_serial_no'))
    #     ])
    #     res = super(InventoryLine, self).create(values)
    #     if existings:
    #         raise UserError(_("You cannot have two inventory adjustements in state 'in Progress' with the same product "
    #                           "(%s), same location (%s), same package, same supplier, same brand, same owner and same lot. Please first validate "
    #                           "the first inventory adjustement with this product before creating another one.") %
    #                         (res.product_id.display_name, res.location_id.display_name))
    #     return res

    @api.model
    def _get_quants(self):
        return self.env['stock.quant'].search([
            ('company_id', '=', self.company_id.id),
            ('location_id', '=', self.location_id.id),
            ('lot_id', '=', self.prod_lot_id.id),
            ('product_id', '=', self.product_id.id),
            ('supplier', '=', self.supplier.id),
            ('product_brand_id', '=', self.product_brand_id.id),
            ('owner_id', '=', self.partner_id.id),
            ('package_id', '=', self.package_id.id)])

    @api.model
    def _get_move_values(self, qty, location_id, location_dest_id, out):
        self.ensure_one()
        return {
            'name': _('INV:') + (self.inventory_id.name or ''),
            'product_id': self.product_id.id,
            'product_uom': self.product_uom_id.id,
            'product_uom_qty': qty,
            'date': self.inventory_id.date,
            'company_id': self.inventory_id.company_id.id,
            'inventory_id': self.inventory_id.id,
            'state': 'confirmed',
            'restrict_partner_id': self.partner_id.id,
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'move_line_ids': [(0, 0, {
                'product_id': self.product_id.id,
                'lot_id': self.prod_lot_id.id,
                'product_uom_qty': 0,  # bypass reservation here
                'product_uom_id': self.product_uom_id.id,
                'qty_done': qty,
                'package_id': out and self.package_id.id or False,
                'result_package_id': (not out) and self.package_id.id or False,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'supplier': self.supplier.id,
                # 'lot_serial_no': self.lot_serial_no,
                'product_brand_id': self.product_brand_id.id,
                'owner_id': self.partner_id.id,
            })]
        }


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    supplier = fields.Many2one('res.partner', 'Vendor')
    product_brand_id = fields.Many2one('product.brand', 'Brand')
    category_id = fields.Many2one('product.category', 'Inventoried Category')

# class Product(models.Model):
#     _inherit = 'product.product'
#
#     categ_id = fields.Many2one(
#         'product.category', 'Internal Category')