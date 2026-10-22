# -*- coding: utf-8 -*-
from odoo import models, fields, api

class SampahAttendance(models.Model):
    _name = 'sirita.sampah.attendance'
    _description = 'Data Absensi & Kehadiran Petugas Bank Sampah'
    _order = 'check_in desc, id desc'

    partner_id = fields.Many2one(
        'res.partner',
        string='Petugas Lapangan',
        required=True,
        domain="[('is_petugas_sampah', '=', True)]",
        ondelete='cascade',
        index=True
    )
    date = fields.Date(
        string='Tanggal',
        default=fields.Date.context_today,
        required=True,
        index=True
    )
    check_in = fields.Datetime(string='Waktu Masuk', default=fields.Datetime.now, required=True)
    check_out = fields.Datetime(string='Waktu Keluar')
    
    in_latitude = fields.Float(string='Latitude Masuk', digits=(10, 7))
    in_longitude = fields.Float(string='Longitude Masuk', digits=(10, 7))
    in_location = fields.Char(string='Lokasi / Alamat Masuk')

    out_latitude = fields.Float(string='Latitude Keluar', digits=(10, 7))
    out_longitude = fields.Float(string='Longitude Keluar', digits=(10, 7))
    out_location = fields.Char(string='Lokasi / Alamat Keluar')

    state = fields.Selection([
        ('in', 'Sedang Bertugas'),
        ('out', 'Selesai Bertugas'),
    ], string='Status', default='in', compute='_compute_state', store=True)

    notes = fields.Text(string='Catatan / Keterangan')

    @api.depends('check_in', 'check_out')
    def _compute_state(self):
        for rec in self:
            if rec.check_out:
                rec.state = 'out'
            else:
                rec.state = 'in'
