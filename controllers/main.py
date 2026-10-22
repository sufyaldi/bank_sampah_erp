# -*- coding: utf-8 -*-
import json
import time
import hmac
import hashlib
import base64
import logging
from odoo import http, fields, _
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

JWT_SECRET_KEY = b'bank_sampah_secret_key_2026'

def base64url_encode(data):
    if isinstance(data, str):
        data = data.encode('utf-8')
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

def base64url_decode(data):
    padding = '=' * (4 - (len(data) % 4)) if len(data) % 4 else ''
    return base64.urlsafe_b64decode(data + padding)

def generate_jwt(payload):
    header = json.dumps({'typ': 'JWT', 'alg': 'HS256'}, separators=(',', ':'))
    payload_str = json.dumps(payload, separators=(',', ':'))
    b64_header = base64url_encode(header)
    b64_payload = base64url_encode(payload_str)
    msg = f"{b64_header}.{b64_payload}".encode('utf-8')
    sig = hmac.new(JWT_SECRET_KEY, msg, hashlib.sha256).digest()
    b64_sig = base64url_encode(sig)
    return f"{b64_header}.{b64_payload}.{b64_sig}"

def validate_jwt(token):
    if not token or token.count('.') != 2:
        return None
    try:
        b64_header, b64_payload, b64_sig = token.split('.')
        msg = f"{b64_header}.{b64_payload}".encode('utf-8')
        expected_sig = base64url_encode(hmac.new(JWT_SECRET_KEY, msg, hashlib.sha256).digest())
        if not hmac.compare_digest(b64_sig, expected_sig):
            return None
        payload = json.loads(base64url_decode(b64_payload).decode('utf-8'))
        if 'exp' in payload and payload['exp'] < time.time():
            return None
        return payload
    except Exception as e:
        _logger.warning("JWT validation error: %s", e)
        return None


class SiritaSampahApiController(http.Controller):

    def _cors_headers(self):
        return [
            ('Content-Type', 'application/json; charset=utf-8'),
            ('Access-Control-Allow-Origin', '*'),
            ('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS'),
            ('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With, ngrok-skip-browser-warning'),
        ]

    def _json_response(self, success, message='', data=None, status=200, extra=None):
        payload = {
            'success': success,
            'message': message,
        }
        if data is not None:
            payload['data'] = data
        if extra:
            payload.update(extra)

        headers = self._cors_headers()
        return Response(json.dumps(payload, default=str), status=status, headers=headers)

    def _get_bearer_token(self):
        auth_header = request.httprequest.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            return auth_header.split(' ', 1)[1].strip()
        return None

    def _parse_input(self):
        if request.httprequest.content_type and 'application/json' in request.httprequest.content_type:
            try:
                return json.loads(request.httprequest.data.decode('utf-8'))
            except Exception:
                return {}
        return request.params or {}

    # -------------------------------------------------------------
    # 0. CONFIG & HEALTH CHECK
    # -------------------------------------------------------------
    @http.route([
        '/bank_sampah_api/config',
        '/bank_sampah_api/config.php'
    ], type='http', auth='public', methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    def api_config(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return Response(status=200, headers=self._cors_headers())
        return self._json_response(
            True,
            message='API Bank Sampah Aktif & Terhubung ke Odoo 20 (SIRITA)',
            extra={'database': 'app-my', 'engine': 'Odoo 20 Enterprise Backend'}
        )

    # -------------------------------------------------------------
    # 1. AUTH / LOGIN
    # -------------------------------------------------------------
    @http.route([
        '/bank_sampah_api/auth/login',
        '/bank_sampah_api/auth/login.php'
    ], type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def api_login(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return Response(status=200, headers=self._cors_headers())

        data = self._parse_input()
        email = (data.get('email') or '').strip().lower()
        password = data.get('password') or ''

        if not email or not password:
            return self._json_response(False, message='Email dan password wajib diisi', status=400)

        # Cari partner di Odoo
        partner = request.env['res.partner'].sudo().search([('email', '=ilike', email)], limit=1)

        # Jika belum ada, cari user odoo
        user = request.env['res.users'].sudo().search([('login', '=ilike', email)], limit=1)
        if user and not partner:
            partner = user.partner_id

        if not partner:
            return self._json_response(False, message='Email atau password salah', status=401)

        # Verifikasi Password jika partner memiliki nasabah_password atau merupakan user odoo
        if partner.nasabah_password:
            import hashlib
            input_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
            if input_hash != partner.nasabah_password and password != partner.nasabah_password:
                return self._json_response(False, message='Email atau password salah', status=401)
        elif user:
            try:
                user_auth = request.env['res.users'].sudo().with_user(user.id)._check_credentials(password, {'interactive': False})
            except Exception:
                # Password user Odoo tidak cocok
                return self._json_response(False, message='Email atau password salah', status=401)

        role = 'nasabah'
        if getattr(partner, 'is_admin_sampah', False) or (user and (user.has_group('sirita_sampah.group_sirita_sampah_manager') or user.has_group('base.group_system'))):
            role = 'admin'
        elif partner.is_petugas_sampah:
            role = 'petugas'

        payload = {
            'id': str(partner.id),
            'email': partner.email,
            'role': role,
            'exp': int(time.time()) + (86400 * 30),
        }
        token = generate_jwt(payload)

        partner_data = {
            'id': str(partner.id),
            'phone_number': partner.phone or getattr(partner, 'mobile', '') or '',
            'email': partner.email,
            'full_name': partner.name,
            'role': role,
            'address': partner.street or partner.contact_address or '',
            'default_setor_method': partner.default_setor_method or 'drop_in',
            'point_balance': int(partner.point_balance),
            'is_active': 1 if partner.active else 0,
        }

        return self._json_response(
            True,
            message='Login berhasil',
            data=partner_data,
            extra={'token': token}
        )

    # -------------------------------------------------------------
    # 2. WASTE CATEGORIES
    # -------------------------------------------------------------
    @http.route([
        '/bank_sampah_api/waste_categories',
        '/bank_sampah_api/waste_categories/',
        '/bank_sampah_api/waste_categories/index.php'
    ], type='http', auth='public', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'], csrf=False, cors='*')
    def api_waste_categories(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return Response(status=200, headers=self._cors_headers())

        method = request.httprequest.method

        if method == 'GET':
            categories = request.env['sirita.sampah.category'].sudo().search([])
            cat_list = []
            for c in categories:
                cat_list.append({
                    'id': c.id,
                    'name': c.name,
                    'point_per_kg': int(c.point_per_kg),
                    'price_per_kg': int(c.price_per_kg),
                    'icon_url': 'icon_default.png',
                    'is_active': 1 if c.is_active else 0,
                    'description': c.description or '',
                })
            return self._json_response(True, data=cat_list)

        token = self._get_bearer_token()
        token_data = validate_jwt(token)
        if not token_data:
            return self._json_response(False, message='Unauthorized', status=401)

        data = self._parse_input()
        if method == 'POST':
            name = data.get('name')
            point = float(data.get('point_per_kg') or 1000)
            request.env['sirita.sampah.category'].sudo().create({
                'name': name,
                'point_per_kg': point,
                'price_per_kg': point,
            })
            return self._json_response(True, message='Kategori berhasil dibuat')

        return self._json_response(False, message='Method not allowed', status=405)

    # -------------------------------------------------------------
    # 3. DROP POINTS
    # -------------------------------------------------------------
    @http.route([
        '/bank_sampah_api/drop_points',
        '/bank_sampah_api/drop_points/',
        '/bank_sampah_api/drop_points/index.php'
    ], type='http', auth='public', methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    def api_drop_points(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return Response(status=200, headers=self._cors_headers())

        points = request.env['sirita.sampah.drop.point'].sudo().search([('is_active', '=', True)])
        dp_list = []
        for p in points:
            dp_list.append({
                'id': str(p.id),
                'name': p.name,
                'address': p.address or '',
                'latitude': str(p.latitude or 0.0),
                'longitude': str(p.longitude or 0.0),
                'capacity_status': p.capacity_status or 'aman',
                'operating_hours': p.operating_hours or '08:00 - 17:00',
            })
        return self._json_response(True, data=dp_list)

    # -------------------------------------------------------------
    # 4. TRANSACTIONS
    # -------------------------------------------------------------
    @http.route([
        '/bank_sampah_api/transactions',
        '/bank_sampah_api/transactions/',
        '/bank_sampah_api/transactions/index.php'
    ], type='http', auth='public', methods=['GET', 'POST', 'PUT', 'OPTIONS'], csrf=False, cors='*')
    def api_transactions(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return Response(status=200, headers=self._cors_headers())

        token = self._get_bearer_token()
        token_data = validate_jwt(token)
        if not token_data:
            return self._json_response(False, message='Unauthorized', status=401)

        method = request.httprequest.method
        tx_obj = request.env['sirita.sampah.transaction'].sudo()

        if method == 'GET':
            tx_id = kwargs.get('id')
            if tx_id:
                tx = tx_obj.search(['|', ('id', '=', tx_id if tx_id.isdigit() else 0), ('name', '=', tx_id)], limit=1)
                if not tx:
                    return self._json_response(False, message='Transaksi tidak ditemukan', status=404)

                items = []
                for line in tx.line_ids:
                    items.append({
                        'id': line.id,
                        'transaction_id': tx.name,
                        'waste_category_id': line.category_id.id,
                        'category_name': line.category_id.name,
                        'weight': line.weight,
                        'points_per_kg': int(line.point_rate),
                        'total_points': int(line.subtotal_points),
                    })

                tx_data = {
                    'id': tx.name,
                    'nasabah_id': str(tx.partner_id.id),
                    'nasabah_name': tx.partner_id.name,
                    'type': tx.transaction_type,
                    'status': tx.state,
                    'created_at': str(tx.date),
                    'total_actual_points': int(tx.total_points),
                    'total_est_points': int(tx.total_points),
                    'items': items,
                }
                return self._json_response(True, data=tx_data)

            # Filter list
            domain = []
            if token_data.get('role') == 'nasabah':
                domain.append(('partner_id', '=', int(token_data['id'])))
            elif kwargs.get('nasabah_id'):
                domain.append(('partner_id', '=', int(kwargs['nasabah_id'])))

            status = kwargs.get('status')
            if status:
                statuses = status.split(',')
                domain.append(('state', 'in', statuses))

            txs = tx_obj.search(domain, order='date desc', limit=50)
            data_list = []
            for t in txs:
                data_list.append({
                    'id': t.name,
                    'nasabah_id': str(t.partner_id.id),
                    'nasabah_name': t.partner_id.name,
                    'type': t.transaction_type,
                    'status': t.state,
                    'created_at': str(t.date),
                    'total_actual_points': int(t.total_points),
                    'total_est_points': int(t.total_points),
                })
            return self._json_response(True, data=data_list)

        elif method == 'POST':
            payload = self._parse_input()
            partner_id = int(token_data['id']) if token_data.get('role') == 'nasabah' else int(payload.get('nasabah_id') or token_data['id'])
            tx_type = payload.get('type') or 'drop_in'

            vals = {
                'partner_id': partner_id,
                'transaction_type': tx_type,
                'pickup_address': payload.get('address') or payload.get('pickup_address') or '',
                'pickup_lat': float(payload.get('pickup_lat') or 0.0),
                'pickup_lng': float(payload.get('pickup_lng') or 0.0),
                'notes': payload.get('notes') or '',
            }

            dp_id = payload.get('drop_point_id')
            if dp_id and str(dp_id).isdigit():
                vals['drop_point_id'] = int(dp_id)

            lines = []
            for item in payload.get('items', []):
                cat_id = int(item.get('waste_category_id') or 1)
                weight = float(item.get('weight') or item.get('estimated_weight') or 0.0)
                lines.append((0, 0, {
                    'category_id': cat_id,
                    'weight': weight,
                }))

            if lines:
                vals['line_ids'] = lines

            new_tx = tx_obj.create(vals)
            return self._json_response(
                True,
                message='Transaksi berhasil dibuat',
                data={'id': new_tx.name, 'name': new_tx.name}
            )

        elif method == 'PUT':
            payload = self._parse_input()
            tx_id = kwargs.get('id') or payload.get('id')
            tx = tx_obj.search(['|', ('id', '=', int(tx_id) if str(tx_id).isdigit() else 0), ('name', '=', tx_id)], limit=1)
            if not tx:
                return self._json_response(False, message='Transaksi tidak ditemukan', status=404)

            new_status = payload.get('status')
            if new_status == 'selesai':
                tx.action_done()
            elif new_status == 'dikonfirmasi':
                tx.action_confirm()
            elif new_status == 'menuju_lokasi':
                tx.action_on_the_way()
            elif new_status == 'tiba':
                tx.action_arrived()
            elif new_status == 'dibatalkan':
                tx.action_cancel()

            return self._json_response(True, message='Status transaksi berhasil diperbarui')

        return self._json_response(False, message='Method not allowed', status=405)

    # -------------------------------------------------------------
    # 5. WITHDRAWALS
    # -------------------------------------------------------------
    @http.route([
        '/bank_sampah_api/withdrawals',
        '/bank_sampah_api/withdrawals/',
        '/bank_sampah_api/withdrawals/index.php'
    ], type='http', auth='public', methods=['GET', 'POST', 'PUT', 'OPTIONS'], csrf=False, cors='*')
    def api_withdrawals(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return Response(status=200, headers=self._cors_headers())

        token = self._get_bearer_token()
        token_data = validate_jwt(token)
        if not token_data:
            return self._json_response(False, message='Unauthorized', status=401)

        wd_obj = request.env['sirita.sampah.withdrawal'].sudo()
        method = request.httprequest.method

        if method == 'GET':
            domain = []
            if token_data.get('role') == 'nasabah':
                domain.append(('partner_id', '=', int(token_data['id'])))

            wds = wd_obj.search(domain, order='date desc')
            data_list = []
            for w in wds:
                data_list.append({
                    'id': w.name,
                    'nasabah_id': str(w.partner_id.id),
                    'nasabah_name': w.partner_id.name,
                    'points_deducted': int(w.points_redeemed),
                    'amount': int(w.amount_rp),
                    'method': w.payout_method,
                    'account_details': w.account_info or '',
                    'status': w.state,
                    'created_at': str(w.date),
                })
            return self._json_response(True, data=data_list)

        elif method == 'POST':
            payload = self._parse_input()
            partner_id = int(token_data['id'])
            points = float(payload.get('points_deducted') or payload.get('points') or 0)

            partner = request.env['res.partner'].sudo().browse(partner_id)
            if partner.point_balance < points:
                return self._json_response(False, message='Saldo poin tidak mencukupi', status=400)

            new_wd = wd_obj.create({
                'partner_id': partner_id,
                'points_redeemed': points,
                'account_info': payload.get('account_details') or '',
                'payout_method': 'transfer',
            })
            return self._json_response(True, message='Pengajuan penarikan berhasil dikirim', data={'id': new_wd.name})

        return self._json_response(False, message='Method not allowed', status=405)

    # -------------------------------------------------------------
    # 6. DASHBOARD STATS
    # -------------------------------------------------------------
    @http.route([
        '/bank_sampah_api/dashboard/stats',
        '/bank_sampah_api/dashboard/stats.php'
    ], type='http', auth='public', methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    def api_dashboard_stats(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return Response(status=200, headers=self._cors_headers())

        total_tx = request.env['sirita.sampah.transaction'].sudo().search_count([('state', '=', 'selesai')])
        total_nasabah = request.env['res.partner'].sudo().search_count([('is_nasabah_sampah', '=', True)])
        
        # Total berat sampah
        all_tx = request.env['sirita.sampah.transaction'].sudo().search([('state', '=', 'selesai')])
        total_kg = sum(t.total_weight for t in all_tx)
        total_points = sum(t.total_points for t in all_tx)

        stats = {
            'total_transactions': total_tx,
            'total_nasabah': total_nasabah,
            'total_weight_kg': round(total_kg, 2),
            'total_points_distributed': int(total_points),
        }
        return self._json_response(True, data=stats)

    # -------------------------------------------------------------
    # 7. TASKS (PENJEMPUTAN)
    # -------------------------------------------------------------
    @http.route([
        '/bank_sampah_api/tasks',
        '/bank_sampah_api/tasks/',
        '/bank_sampah_api/tasks/index.php'
    ], type='http', auth='public', methods=['GET', 'PUT', 'OPTIONS'], csrf=False, cors='*')
    def api_tasks(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return Response(status=200, headers=self._cors_headers())

        method = request.httprequest.method
        task_obj = request.env['sirita.sampah.pickup.task'].sudo()

        if method == 'GET':
            domain = []
            status = kwargs.get('status')
            if status:
                domain.append(('state', 'in', status.split(',')))
            tasks = task_obj.search(domain, order='scheduled_date desc', limit=50)
            data_list = []
            for t in tasks:
                data_list.append({
                    'id': t.name,
                    'transaction_id': t.transaction_id.name if t.transaction_id else '',
                    'nasabah_name': t.nasabah_id.name if t.nasabah_id else '',
                    'phone_number': t.nasabah_id.phone or getattr(t.nasabah_id, 'mobile', '') or '',
                    'nasabah_address': t.pickup_address or '',
                    'scheduled_date': str(t.scheduled_date),
                    'time_slot': t.time_slot or '',
                    'status': t.state,
                })
            return self._json_response(True, data=data_list)
        elif method == 'PUT':
            payload = self._parse_input()
            task_id = kwargs.get('id') or payload.get('id')
            t = task_obj.search(['|', ('id', '=', int(task_id) if str(task_id).isdigit() else 0), ('name', '=', task_id)], limit=1)
            if not t:
                return self._json_response(False, message='Tugas tidak ditemukan', status=404)
            new_status = payload.get('status')
            if new_status == 'assigned':
                t.action_assign()
            elif new_status in ('on_the_way', 'menuju_lokasi'):
                t.action_start()
            elif new_status in ('done', 'selesai'):
                t.action_complete()
            return self._json_response(True, message='Status tugas berhasil diperbarui')
        return self._json_response(False, message='Method not allowed', status=405)

    # -------------------------------------------------------------
    # 8. USERS / PARTNERS
    # -------------------------------------------------------------
    @http.route([
        '/bank_sampah_api/users',
        '/bank_sampah_api/users/',
        '/bank_sampah_api/users/index.php'
    ], type='http', auth='public', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'], csrf=False, cors='*')
    def api_users(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return Response(status=200, headers=self._cors_headers())

        method = request.httprequest.method
        partner_obj = request.env['res.partner'].sudo()

        if method == 'GET':
            user_id = kwargs.get('id')
            if user_id:
                p = partner_obj.search(['|', ('id', '=', int(user_id) if str(user_id).isdigit() else 0), ('nasabah_code', '=', user_id)], limit=1)
                if not p:
                    return self._json_response(False, message='User tidak ditemukan', status=404)
                return self._json_response(True, data={
                    'id': str(p.id),
                    'full_name': p.name,
                    'email': p.email,
                    'phone_number': p.phone or getattr(p, 'mobile', '') or '',
                    'address': p.street or '',
                    'point_balance': int(p.point_balance),
                    'role': 'petugas' if p.is_petugas_sampah else 'nasabah',
                    'default_setor_method': p.default_setor_method or 'drop_in',
                })
            # List users
            partners = partner_obj.search([('is_nasabah_sampah', '=', True)], limit=100)
            data_list = []
            for p in partners:
                data_list.append({
                    'id': str(p.id),
                    'full_name': p.name,
                    'email': p.email,
                    'phone_number': p.phone or getattr(p, 'mobile', '') or '',
                    'point_balance': int(p.point_balance),
                    'role': 'petugas' if p.is_petugas_sampah else 'nasabah',
                })
            return self._json_response(True, data=data_list)

        elif method == 'POST':
            data = self._parse_input()
            email = (data.get('email') or '').strip().lower()
            name = (data.get('full_name') or data.get('name') or '').strip()
            phone = (data.get('phone_number') or data.get('phone') or '').strip()
            role = (data.get('role') or 'nasabah').strip().lower()
            address = (data.get('address') or '').strip()

            if not email or not name:
                return self._json_response(False, message='Nama dan email wajib diisi', status=400)

            # Cek apakah partner/nasabah dengan email ini sudah ada
            existing = partner_obj.search([('email', '=ilike', email)], limit=1)
            if existing:
                return self._json_response(False, message='Email sudah terdaftar. Silakan gunakan email lain atau langsung login.', status=400)

            # Generate nasabah_code jika belum ada
            next_code = partner_obj.search_count([]) + 1
            nasabah_code = f"NSB-{next_code:04d}"

            vals = {
                'name': name,
                'email': email,
                'phone': phone,
                'street': address,
                'is_nasabah_sampah': True if role == 'nasabah' else False,
                'is_petugas_sampah': True if role == 'petugas' else False,
                'nasabah_code': nasabah_code,
                'default_setor_method': data.get('default_setor_method') or 'drop_in',
                'point_balance': 0.0,
            }
            if data.get('password'):
                import hashlib
                raw_pwd = str(data.get('password')).strip()
                vals['nasabah_password'] = hashlib.sha256(raw_pwd.encode('utf-8')).hexdigest()

            try:
                new_partner = partner_obj.create(vals)
                _logger.info("Nasabah/Petugas baru berhasil dibuat: %s (%s)", new_partner.name, new_partner.email)
                return self._json_response(True, message='Pendaftaran berhasil', data={
                    'id': str(new_partner.id),
                    'full_name': new_partner.name,
                    'email': new_partner.email,
                    'role': 'petugas' if new_partner.is_petugas_sampah else 'nasabah',
                    'nasabah_code': new_partner.nasabah_code,
                }, status=201)
            except Exception as e:
                _logger.error("Gagal membuat user baru di Odoo: %s", str(e))
                return self._json_response(False, message=f'Gagal mendaftar: {str(e)}', status=500)

        elif method == 'PUT':
            data = self._parse_input()
            user_id = kwargs.get('id') or data.get('id')
            if not user_id:
                return self._json_response(False, message='ID User wajib disertakan', status=400)

            partner = partner_obj.search(['|', ('id', '=', int(user_id) if str(user_id).isdigit() else 0), ('nasabah_code', '=', user_id)], limit=1)
            if not partner:
                return self._json_response(False, message='User tidak ditemukan', status=404)

            vals = {}
            if 'full_name' in data:
                vals['name'] = data['full_name']
            if 'phone_number' in data:
                vals['phone'] = data['phone_number']
            if 'address' in data:
                vals['street'] = data['address']
            if 'default_setor_method' in data:
                vals['default_setor_method'] = data['default_setor_method']
            if 'password' in data and data['password']:
                import hashlib
                raw_pwd = str(data['password']).strip()
                vals['nasabah_password'] = hashlib.sha256(raw_pwd.encode('utf-8')).hexdigest()

            if vals:
                partner.write(vals)
            return self._json_response(True, message='Data profil berhasil diperbarui')

        return self._json_response(False, message='Method not allowed', status=405)

    # -------------------------------------------------------------
    # 9. UPLOADS (PHOTO & AVATAR)
    # -------------------------------------------------------------
    @http.route([
        '/bank_sampah_api/transactions/upload_photo',
        '/bank_sampah_api/transactions/upload_photo.php',
        '/bank_sampah_api/users/upload_avatar',
        '/bank_sampah_api/users/upload_avatar.php',
    ], type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def api_uploads(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return Response(status=200, headers=self._cors_headers())

        file_obj = request.httprequest.files.get('photo') or request.httprequest.files.get('avatar') or request.httprequest.files.get('file')
        file_url = '/web/static/img/placeholder.png'
        if file_obj:
            file_data = file_obj.read()
            b64_data = base64.b64encode(file_data)
            att = request.env['ir.attachment'].sudo().create({
                'name': file_obj.filename or 'upload.jpg',
                'type': 'binary',
                'datas': b64_data,
                'public': True,
                'mimetype': file_obj.mimetype or 'image/jpeg',
            })
            file_url = f'/web/content/{att.id}'

        return self._json_response(True, message='Upload berhasil', data={'url': file_url, 'photo_url': file_url, 'avatar_url': file_url})

    # -------------------------------------------------------------
    # 10. ATTENDANCE (PRESENSI PETUGAS)
    # -------------------------------------------------------------
    @http.route([
        '/bank_sampah_api/attendance',
        '/bank_sampah_api/attendance/',
        '/bank_sampah_api/attendance/index.php'
    ], type='http', auth='public', methods=['GET', 'POST', 'OPTIONS'], csrf=False, cors='*')
    def api_attendance(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return Response(status=200, headers=self._cors_headers())

        att_obj = request.env['sirita.sampah.attendance'].sudo()
        method = request.httprequest.method

        if method == 'GET':
            partner_id = kwargs.get('partner_id') or kwargs.get('user_id')
            email = kwargs.get('email')
            domain = []
            if partner_id:
                partner = None
                if str(partner_id).isdigit():
                    partner = request.env['res.partner'].sudo().browse(int(partner_id))
                if not partner or not partner.exists():
                    partner = request.env['res.partner'].sudo().search([
                        '|', ('ref', '=', str(partner_id)),
                        '|', ('email', '=', str(email or partner_id)),
                             ('name', 'ilike', str(partner_id))
                    ], limit=1)
                
                if partner and partner.exists():
                    domain.append(('partner_id', '=', partner.id))
                else:
                    return self._json_response(True, data=[])
            elif email:
                partner = request.env['res.partner'].sudo().search([('email', '=', str(email))], limit=1)
                if partner:
                    domain.append(('partner_id', '=', partner.id))
                else:
                    return self._json_response(True, data=[])
            
            attendances = att_obj.search(domain, limit=30, order='check_in desc')
            data_list = []
            for a in attendances:
                data_list.append({
                    'id': a.id,
                    'partner_id': a.partner_id.id,
                    'partner_name': a.partner_id.name,
                    'date': str(a.date),
                    'check_in': a.check_in.strftime('%Y-%m-%d %H:%M:%S') if a.check_in else '',
                    'check_out': a.check_out.strftime('%Y-%m-%d %H:%M:%S') if a.check_out else '',
                    'in_location': a.in_location or '',
                    'out_location': a.out_location or '',
                    'state': a.state,
                })
            return self._json_response(True, data=data_list)

        elif method == 'POST':
            data = self._parse_input()
            partner_id = data.get('partner_id') or data.get('user_id')
            email = data.get('email')
            name = data.get('name')
            action = data.get('action') or 'check_in' # 'check_in' or 'check_out'
            lat = float(data.get('latitude') or 0.0)
            lng = float(data.get('longitude') or 0.0)
            location = (data.get('location') or '').strip()

            if not partner_id and not email:
                return self._json_response(False, message='ID Petugas atau Email wajib disertakan', status=400)

            partner = None
            if partner_id and str(partner_id).isdigit():
                partner = request.env['res.partner'].sudo().browse(int(partner_id))
            
            if not partner or not partner.exists():
                lookup_terms = []
                if partner_id:
                    lookup_terms.extend([('ref', '=', str(partner_id)), ('email', '=', str(partner_id)), ('name', 'ilike', str(partner_id))])
                if email:
                    lookup_terms.append(('email', '=', str(email)))
                if name:
                    lookup_terms.append(('name', 'ilike', str(name)))
                
                # Combine lookup with OR
                domain = []
                for idx, term in enumerate(lookup_terms):
                    if idx > 0:
                        domain.insert(0, '|')
                    domain.append(term)
                
                if domain:
                    partner = request.env['res.partner'].sudo().search(domain, limit=1)

            if not partner or not partner.exists():
                return self._json_response(False, message='Petugas tidak ditemukan', status=404)

            today = fields.Date.context_today(att_obj)
            now = fields.Datetime.now()

            # Cari absen hari ini
            active_att = att_obj.search([
                ('partner_id', '=', partner.id),
                ('date', '=', today)
            ], limit=1, order='id desc')

            if action == 'check_in':
                if active_att and not active_att.check_out:
                    return self._json_response(False, message='Anda sudah melakukan absen masuk hari ini.')
                
                new_att = att_obj.create({
                    'partner_id': partner.id,
                    'date': today,
                    'check_in': now,
                    'in_latitude': lat,
                    'in_longitude': lng,
                    'in_location': location or 'Kampus IAIN Parepare',
                })
                return self._json_response(True, message='Absen masuk berhasil dicatat!', data={
                    'id': new_att.id,
                    'check_in': new_att.check_in.strftime('%Y-%m-%d %H:%M:%S'),
                    'state': new_att.state,
                })

            elif action == 'check_out':
                if not active_att:
                    return self._json_response(False, message='Belum ada riwayat absen masuk untuk hari ini.')
                if active_att.check_out:
                    return self._json_response(False, message='Anda sudah melakukan absen keluar hari ini.')

                active_att.write({
                    'check_out': now,
                    'out_latitude': lat,
                    'out_longitude': lng,
                    'out_location': location or 'Kampus IAIN Parepare',
                })
                return self._json_response(True, message='Absen keluar berhasil dicatat!', data={
                    'id': active_att.id,
                    'check_out': active_att.check_out.strftime('%Y-%m-%d %H:%M:%S'),
                    'state': active_att.state,
                })

            return self._json_response(False, message='Aksi tidak valid (gunakan check_in atau check_out)', status=400)

    # -------------------------------------------------------------
    # 11. AUDIT LOGS, CHATS, REPORTS (FALLBACK)
    # -------------------------------------------------------------
    @http.route([
        '/bank_sampah_api/audit_logs',
        '/bank_sampah_api/audit_logs/index.php',
        '/bank_sampah_api/chats/get_admins',
        '/bank_sampah_api/chats/get_admins.php',
        '/bank_sampah_api/chats/get_chat_users',
        '/bank_sampah_api/chats/get_chat_users.php',
        '/bank_sampah_api/chats/get_messages',
        '/bank_sampah_api/chats/get_messages.php',
        '/bank_sampah_api/chats/send_message',
        '/bank_sampah_api/chats/send_message.php',
        '/bank_sampah_api/reports/operasional',
        '/bank_sampah_api/reports/operasional.php',
    ], type='http', auth='public', methods=['GET', 'POST', 'OPTIONS'], csrf=False, cors='*')
    def api_extras(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return Response(status=200, headers=self._cors_headers())
        return self._json_response(True, data=[])

