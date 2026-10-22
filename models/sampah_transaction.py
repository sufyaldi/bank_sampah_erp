# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SiritaSampahTransaction(models.Model):
    _name = 'sirita.sampah.transaction'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Transaksi Setor / Penimbangan Sampah'
    _order = 'date desc, id desc'

    name = fields.Char(
        string='No. Transaksi',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Nasabah',
        required=True,
        tracking=True,
        domain="[('is_nasabah_sampah', '=', True)]"
    )
    collector_id = fields.Many2one(
        'res.partner',
        string='Petugas Lapangan',
        tracking=True,
        domain="[('is_petugas_sampah', '=', True)]"
    )
    date = fields.Datetime(
        string='Tanggal & Waktu Transaksi',
        default=fields.Datetime.now,
        required=True,
        tracking=True
    )
    transaction_type = fields.Selection([
        ('drop_in', 'Drop-In Mandiri'),
        ('pickup', 'Jemput Sampah'),
        ('rvm', 'Reverse Vending Machine'),
        ('donasi', 'Donasi Lingkungan'),
    ], string='Jenis Layanan', default='drop_in', required=True, tracking=True)

    drop_point_id = fields.Many2one(
        'sirita.sampah.drop.point',
        string='Lokasi Titik Kumpul (Drop Point)'
    )
    pickup_address = fields.Text(string='Alamat Penjemputan')
    pickup_lat = fields.Float(string='Latitude', digits=(10, 7))
    pickup_lng = fields.Float(string='Longitude', digits=(10, 7))

    line_ids = fields.One2many(
        'sirita.sampah.transaction.line',
        'transaction_id',
        string='Rincian Penimbangan'
    )

    total_weight = fields.Float(
        string='Total Berat (Kg)',
        compute='_compute_totals',
        store=True,
        tracking=True
    )
    total_points = fields.Float(
        string='Total Poin Diberikan',
        compute='_compute_totals',
        store=True,
        tracking=True
    )
    total_amount_rp = fields.Float(
        string='Estimasi Nilai (Rp)',
        compute='_compute_totals',
        store=True
    )

    photo_evidence = fields.Binary(string='Foto Bukti Timbangan / Serah Terima', attachment=True)
    notes = fields.Text(string='Catatan Transaksi')

    state = fields.Selection([
        ('draft', 'Menunggu'),
        ('dikonfirmasi', 'Dikonfirmasi'),
        ('menuju_lokasi', 'Petugas Menuju Lokasi'),
        ('tiba', 'Tiba di Lokasi'),
        ('selesai', 'Selesai & Terverifikasi'),
        ('dibatalkan', 'Dibatalkan'),
    ], string='Status', default='draft', required=True, tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('sirita.sampah.transaction') or _('New')
        return super(SiritaSampahTransaction, self).create(vals_list)

    @api.depends('line_ids.weight', 'line_ids.subtotal_points', 'line_ids.subtotal_amount_rp')
    def _compute_totals(self):
        for tx in self:
            tx.total_weight = sum(line.weight for line in tx.line_ids)
            tx.total_points = sum(line.subtotal_points for line in tx.line_ids)
            tx.total_amount_rp = sum(line.subtotal_amount_rp for line in tx.line_ids)

    def action_confirm(self):
        self.write({'state': 'dikonfirmasi'})

    def action_on_the_way(self):
        self.write({'state': 'menuju_lokasi'})

    def action_arrived(self):
        self.write({'state': 'tiba'})

    def action_done(self):
        for tx in self:
            if not tx.line_ids:
                raise UserError(_('Tidak dapat menyelesaikan transaksi tanpa ada rincian berat sampah!'))
            # Tambahkan saldo poin ke nasabah
            tx.partner_id.point_balance += tx.total_points
            tx.write({'state': 'selesai'})

    def action_cancel(self):
        for tx in self:
            if tx.state == 'selesai':
                # Batalkan dan kurangi saldo poin jika sebelumnya sudah selesai
                tx.partner_id.point_balance -= tx.total_points
            tx.write({'state': 'dibatalkan'})


class SiritaSampahTransactionLine(models.Model):
    _name = 'sirita.sampah.transaction.line'
    _description = 'Rincian Baris Penimbangan Sampah'

    transaction_id = fields.Many2one(
        'sirita.sampah.transaction',
        string='Transaksi Induk',
        required=True,
        ondelete='cascade'
    )
    category_id = fields.Many2one(
        'sirita.sampah.category',
        string='Jenis Sampah',
        required=True
    )
    weight = fields.Float(string='Berat (Kg)', required=True, default=0.0)
    point_rate = fields.Float(string='Poin/Kg', related='category_id.point_per_kg', readonly=True)
    price_rate = fields.Float(string='Rp/Kg', related='category_id.price_per_kg', readonly=True)

    subtotal_points = fields.Float(
        string='Subtotal Poin',
        compute='_compute_subtotals',
        store=True
    )
    subtotal_amount_rp = fields.Float(
        string='Subtotal Nilai (Rp)',
        compute='_compute_subtotals',
        store=True
    )

    @api.depends('weight', 'point_rate', 'price_rate')
    def _compute_subtotals(self):
        for line in self:
            line.subtotal_points = line.weight * (line.point_rate or 0.0)
            line.subtotal_amount_rp = line.weight * (line.price_rate or 0.0)
