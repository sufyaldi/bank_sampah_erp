# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class SiritaSampahPickupTask(models.Model):
    _name = 'sirita.sampah.pickup.task'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Penugasan Penjemputan Sampah Lapangan'
    _order = 'scheduled_date desc, id desc'

    name = fields.Char(
        string='No. Tugas',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    transaction_id = fields.Many2one(
        'sirita.sampah.transaction',
        string='Referensi Transaksi Setor',
        ondelete='cascade'
    )
    nasabah_id = fields.Many2one(
        'res.partner',
        string='Nasabah',
        related='transaction_id.partner_id',
        store=True,
        tracking=True
    )
    collector_id = fields.Many2one(
        'res.partner',
        string='Petugas Lapangan',
        domain="[('is_petugas_sampah', '=', True)]",
        tracking=True
    )
    scheduled_date = fields.Date(
        string='Jadwal Penjemputan',
        default=fields.Date.today,
        required=True,
        tracking=True
    )
    time_slot = fields.Char(string='Sesi Waktu (Jam)', default='09:00 - 12:00')
    pickup_address = fields.Text(string='Alamat Penjemputan', related='transaction_id.pickup_address', readonly=False)
    pickup_lat = fields.Float(string='Latitude', related='transaction_id.pickup_lat', readonly=False)
    pickup_lng = fields.Float(string='Longitude', related='transaction_id.pickup_lng', readonly=False)

    notes = fields.Text(string='Instruksi / Catatan Kurir')

    state = fields.Selection([
        ('pending', 'Menunggu Petugas'),
        ('assigned', 'Ditugaskan'),
        ('on_the_way', 'Sedang Dijemput'),
        ('done', 'Selesai'),
        ('cancelled', 'Dibatalkan'),
    ], string='Status Penugasan', default='pending', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('sirita.sampah.pickup.task') or _('New')
        return super(SiritaSampahPickupTask, self).create(vals_list)

    def action_assign(self):
        self.write({'state': 'assigned'})

    def action_start(self):
        self.write({'state': 'on_the_way'})
        if self.transaction_id:
            self.transaction_id.action_on_the_way()

    def action_complete(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})
