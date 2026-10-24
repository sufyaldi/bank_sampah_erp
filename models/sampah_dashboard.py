# -*- coding: utf-8 -*-
from odoo import models, fields, api

class SampahDashboard(models.TransientModel):
    _name = 'sampah.dashboard'
    _description = 'Bank Sampah Interactive Dashboard'

    @api.model
    def get_statistics(self):
        """Menghitung ringkasan metrik statistik Bank Sampah untuk dashboard."""
        today = fields.Date.today()
        first_day_of_month = today.replace(day=1)
        first_datetime = fields.Datetime.to_datetime(first_day_of_month)

        # 1. Nasabah
        total_nasabah = self.env['res.partner'].search_count([('is_nasabah_sampah', '=', True)])
        
        # 2. Total Berat & Poin dari Transaksi Selesai
        tx_selesai = self.env['sirita.sampah.transaction'].search([('state', '=', 'selesai')])
        total_weight = sum(tx_selesai.mapped('total_weight'))
        total_points = sum(tx_selesai.mapped('total_points'))

        # 3. Transaksi Bulan Ini
        tx_month = self.env['sirita.sampah.transaction'].search([
            ('date', '>=', first_datetime),
        ])
        monthly_tx_count = len(tx_month)
        monthly_weight = sum(tx_month.filtered(lambda t: t.state == 'selesai').mapped('total_weight'))

        # 4. Penjemputan Pending / Aktif
        active_pickups = self.env['sirita.sampah.pickup.task'].search_count([
            ('state', 'in', ['pending', 'assigned', 'on_the_way'])
        ])

        # 5. Penarikan Saldo Pending (state = 'submitted')
        pending_withdrawals = self.env['sirita.sampah.withdrawal'].search_count([
            ('state', '=', 'submitted')
        ])

        # 6. Kategori Sampah Terpopuler (field is_active dan point_per_kg)
        categories_data = []
        categories = self.env['sirita.sampah.category'].search([('is_active', '=', True)], limit=5)
        for cat in categories:
            lines = self.env['sirita.sampah.transaction.line'].search([
                ('category_id', '=', cat.id),
                ('transaction_id.state', '=', 'selesai')
            ])
            cat_weight = sum(lines.mapped('weight'))
            categories_data.append({
                'name': cat.name,
                'weight': round(cat_weight, 1),
                'point_rate': cat.point_per_kg,
            })

        return {
            'total_nasabah': total_nasabah,
            'total_weight': round(total_weight, 1),
            'total_points': round(total_points, 0),
            'monthly_tx_count': monthly_tx_count,
            'monthly_weight': round(monthly_weight, 1),
            'active_pickups': active_pickups,
            'pending_withdrawals': pending_withdrawals,
            'categories_data': categories_data,
        }
