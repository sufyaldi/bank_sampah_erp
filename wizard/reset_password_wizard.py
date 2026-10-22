# -*- coding: utf-8 -*-
import hashlib
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SampahResetPasswordWizard(models.TransientModel):
    _name = 'sampah.reset.password.wizard'
    _description = 'Wizard Reset Password Nasabah Bank Sampah'

    partner_id = fields.Many2one(
        'res.partner',
        string='Nasabah / Petugas',
        required=True,
        readonly=True,
        default=lambda self: self.env.context.get('active_id')
    )
    email = fields.Char(related='partner_id.email', string='Email Akun', readonly=True)
    new_password = fields.Char(string='Kata Sandi Baru', required=True)

    def action_confirm_reset(self):
        self.ensure_one()
        if not self.new_password or len(self.new_password.strip()) < 6:
            raise UserError(_('Kata sandi baru minimal harus 6 karakter.'))

        raw_pwd = self.new_password.strip()
        pwd_hash = hashlib.sha256(raw_pwd.encode('utf-8')).hexdigest()

        # Simpan password hash ke field nasabah_password di res.partner
        self.partner_id.sudo().write({
            'nasabah_password': pwd_hash
        })

        # Jika nasabah tersebut kebetulan memiliki akun user Odoo (res.users), sinkronkan juga
        user = self.env['res.users'].sudo().search([('partner_id', '=', self.partner_id.id)], limit=1)
        if user:
            user._change_password(raw_pwd)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Berhasil'),
                'message': _('Kata sandi untuk %s (%s) berhasil direset.') % (self.partner_id.name, self.email),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
