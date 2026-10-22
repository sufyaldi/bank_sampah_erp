# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_nasabah_sampah = fields.Boolean(string='Nasabah Bank Sampah', default=False)
    is_petugas_sampah = fields.Boolean(string='Petugas Bank Sampah', default=False)
    is_admin_sampah = fields.Boolean(string='Admin Bank Sampah', default=False)
    nasabah_code = fields.Char(string='ID / Kode Nasabah')
    point_balance = fields.Float(string='Saldo Poin', default=0.0)
    rupiah_balance = fields.Float(
        string='Estimasi Nilai Rupiah',
        compute='_compute_rupiah_balance',
        store=True
    )
    default_setor_method = fields.Selection([
        ('drop_in', 'Drop-In Mandiri'),
        ('pickup', 'Jemput Sampah'),
        ('rvm', 'Reverse Vending Machine'),
        ('donasi', 'Donasi Lingkungan'),
    ], string='Metode Setor Favorit', default='drop_in')
    nasabah_latitude = fields.Float(string='Latitude Lokasi Default', digits=(10, 7))
    nasabah_longitude = fields.Float(string='Longitude Lokasi Default', digits=(10, 7))
    nasabah_password = fields.Char(string='Password Hash Nasabah', copy=False)

    transaction_count = fields.Integer(
        string='Total Transaksi Setor',
        compute='_compute_sampah_stats'
    )
    total_waste_kg = fields.Float(
        string='Total Sampah Terkumpul (Kg)',
        compute='_compute_sampah_stats'
    )

    @api.depends('point_balance')
    def _compute_rupiah_balance(self):
        for partner in self:
            # 1 Poin = Rp 1 (atau dapat disesuaikan rasio sistem)
            partner.rupiah_balance = partner.point_balance * 1.0

    def _compute_sampah_stats(self):
        for partner in self:
            txs = self.env['sirita.sampah.transaction'].search([
                ('partner_id', '=', partner.id),
                ('state', '=', 'selesai')
            ])
            partner.transaction_count = len(txs)
            partner.total_waste_kg = sum(tx.total_weight for tx in txs)

    def action_reset_sampah_password(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reset Kata Sandi Akun',
            'res_model': 'sampah.reset.password.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
            }
        }

