# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SiritaSampahWithdrawal(models.Model):
    _name = 'sirita.sampah.withdrawal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Pengajuan Penarikan Saldo Poin'
    _order = 'date desc, id desc'

    name = fields.Char(
        string='No. Penarikan',
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
    date = fields.Datetime(
        string='Tanggal Pengajuan',
        default=fields.Datetime.now,
        required=True
    )
    current_point_balance = fields.Float(
        string='Saldo Poin Saat Ini',
        related='partner_id.point_balance',
        readonly=True
    )
    points_redeemed = fields.Float(
        string='Jumlah Poin yang Ditarik',
        required=True,
        tracking=True
    )
    amount_rp = fields.Float(
        string='Nominal Rupiah (Rp)',
        compute='_compute_amount_rp',
        store=True,
        tracking=True
    )
    payout_method = fields.Selection([
        ('cash', 'Tunai di Kantor Bank Sampah'),
        ('transfer', 'Transfer Bank / E-Wallet'),
        ('potong_mahad', 'Potong Iuran Ma\'had Al-Jami\'ah'),
        ('voucher', 'Voucher Kantin / Koperasi Kampus'),
    ], string='Metode Pencairan', default='transfer', required=True, tracking=True)

    account_info = fields.Char(string='No. Rekening / No. HP E-Wallet / NIM')
    account_name = fields.Char(string='Nama Pemilik Rekening / Mahasiswa')
    transfer_proof = fields.Binary(string='Bukti Pembayaran / Penyerahan', attachment=True)
    notes = fields.Text(string='Catatan Petugas')

    approved_by = fields.Many2one('res.users', string='Disetujui Oleh', readonly=True)
    state = fields.Selection([
        ('submitted', 'Diajukan'),
        ('approved', 'Disetujui Admin'),
        ('done', 'Selesai / Terbayar'),
        ('rejected', 'Ditolak'),
    ], string='Status Pengajuan', default='submitted', required=True, tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('sirita.sampah.withdrawal') or _('New')
        return super(SiritaSampahWithdrawal, self).create(vals_list)

    @api.depends('points_redeemed')
    def _compute_amount_rp(self):
        for wd in self:
            # 1 Poin = Rp 1
            wd.amount_rp = wd.points_redeemed * 1.0

    def action_approve(self):
        for wd in self:
            if wd.points_redeemed <= 0:
                raise UserError(_('Jumlah poin yang ditarik harus lebih dari 0!'))
            if wd.partner_id.point_balance < wd.points_redeemed:
                raise UserError(_('Saldo poin nasabah tidak mencukupi untuk penarikan ini!'))
            wd.write({
                'state': 'approved',
                'approved_by': self.env.user.id
            })

    def action_done(self):
        for wd in self:
            if wd.partner_id.point_balance < wd.points_redeemed:
                raise UserError(_('Saldo poin nasabah tidak mencukupi!'))
            # Kurangi saldo poin nasabah
            wd.partner_id.point_balance -= wd.points_redeemed
            wd.write({'state': 'done'})

    def action_reject(self):
        self.write({'state': 'rejected'})
