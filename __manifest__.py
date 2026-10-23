# -*- coding: utf-8 -*-
{
    'name': 'Sirita Bank Sampah',
    'version': '20.0.1.0.0',
    'category': 'Sustainability',
    'summary': 'Pengelolaan Bank Sampah Terintegrasi Kampus Hijau IAIN Parepare',
    'description': """
Sirita Bank Sampah — Green Campus ERP Ecosystem
===============================================
Modul pengelolaan Bank Sampah IAIN Parepare yang terintegrasi dengan ekosistem SIRITA:
* Manajemen Kategori Sampah, Harga Beli, dan Rasio Poin per Kg.
* Pencatatan Penimbangan Transaksi Setor Sampah (Drop-In, Penjemputan, RVM, Donasi).
* Manajemen Penugasan Petugas Lapangan / Kurir Penjemputan Sampah Kampus.
* Pengelolaan Saldo Poin & Verifikasi Permohonan Penarikan Saldo (Cash, Transfer, Pemotong Iuran Ma'had).
* Titik Drop Point / Lokasi GPS Titik Kumpul Sampah Kampus.
* Terintegrasi dengan Akun Civitas (Mahasiswa/Dosen/Tendik).
    """,
    'author': 'sufyALDI | UPT TIPD IAIN Parepare',
    'website': 'https://banksampah.iainpare.ac.id',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'mail',
    ],
    'data': [
        'security/sirita_sampah_security.xml',
        'security/ir.access.csv',
        'data/sequence_data.xml',
        'data/default_categories.xml',
        'views/dashboard_views.xml',
        'views/category_views.xml',
        'views/drop_point_views.xml',
        'views/transaction_views.xml',
        'views/pickup_views.xml',
        'views/withdrawal_views.xml',
        'views/attendance_views.xml',
        'wizard/reset_password_wizard_views.xml',
        'views/partner_views.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'sirita_sampah/static/src/css/sampah_dashboard.css',
            'sirita_sampah/static/src/js/sampah_dashboard.js',
            'sirita_sampah/static/src/xml/sampah_dashboard.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
