# -*- coding: utf-8 -*-
from odoo import models, fields

class SiritaSampahDropPoint(models.Model):
    _name = 'sirita.sampah.drop.point'
    _description = 'Titik Drop Point Sampah Kampus'
    _order = 'name'

    name = fields.Char(string='Nama Drop Point', required=True, index=True)
    code = fields.Char(string='Kode Lokasi')
    address = fields.Text(string='Alamat / Lokasi Gedung')
    latitude = fields.Float(string='Latitude', digits=(10, 7))
    longitude = fields.Float(string='Longitude', digits=(10, 7))
    capacity_status = fields.Selection([
        ('aman', 'Aman (Masih Tersedia Ruang)'),
        ('hampir_penuh', 'Hampir Penuh'),
        ('penuh', 'Penuh (Perlu Pengosongan Segera)'),
    ], string='Status Kapasitas', default='aman', required=True)
    operating_hours = fields.Char(string='Jam Operasional', default='08:00 - 17:00')
    is_active = fields.Boolean(string='Aktif', default=True)
    notes = fields.Text(string='Keterangan Tambahan')
