# -*- coding: utf-8 -*-
from odoo import models, fields, api

class SiritaSampahCategory(models.Model):
    _name = 'sirita.sampah.category'
    _description = 'Kategori Jenis Sampah'
    _order = 'sequence, name'

    sequence = fields.Integer(string='Urutan', default=10)
    name = fields.Char(string='Nama Kategori', required=True, index=True)
    code = fields.Char(string='Kode Kategori')
    point_per_kg = fields.Float(string='Poin per Kg', default=1000.0, required=True)
    price_per_kg = fields.Float(string='Estimasi Rupiah per Kg', default=1000.0, required=True)
    icon_image = fields.Binary(string='Ikon Kategori', attachment=True)
    is_active = fields.Boolean(string='Status Aktif', default=True)
    description = fields.Text(string='Deskripsi / Panduan Pemilahan')

    transaction_line_count = fields.Integer(
        string='Jumlah Penimbangan',
        compute='_compute_transaction_line_count'
    )

    def _compute_transaction_line_count(self):
        line_data = self.env['sirita.sampah.transaction.line'].read_group(
            [('category_id', 'in', self.ids)],
            ['category_id'],
            ['category_id']
        )
        mapped_data = {item['category_id'][0]: item['category_id_count'] for item in line_data}
        for record in self:
            record.transaction_line_count = mapped_data.get(record.id, 0)
