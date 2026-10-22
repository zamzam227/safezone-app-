"""Uji integrasi: python test_api.py  (menjalankan server sementara dengan database kosong)"""
import os, sys, json, time, base64, subprocess, tempfile, random, urllib.request, urllib.error
PORT = random.randint(4100, 4600); B = f'http://localhost:{PORT}'
env = {**os.environ, 'PORT': str(PORT), 'DATA_DIR': tempfile.mkdtemp(), 'ADMIN_PASSWORD': 'admin-pass-123'}
here = os.path.dirname(os.path.abspath(__file__)); fails = 0
def ok(c, m):
    global fails; print(('PASS ' if c else 'FAIL ') + m); fails += 0 if c else 1
class C:
    def __init__(s): s.ck = ''
    def r(s, m, u, b=None, h=None):
        hd = {'Content-Type': 'application/json', 'X-Requested-With': 'fetch', **({'Cookie': s.ck} if s.ck else {}), **(h or {})}
        data = json.dumps(b).encode() if b is not None else (b'' if m == 'POST' else None)
        try: rs = urllib.request.urlopen(urllib.request.Request(B + u, data=data, headers=hd, method=m))
        except urllib.error.HTTPError as e: rs = e
        sc = rs.headers.get('Set-Cookie')
        if sc: s.ck = sc.split(';')[0]
        raw = rs.read(); return rs.status, (json.loads(raw) if 'json' in rs.headers.get('Content-Type', '') else raw)
def cli(*a): subprocess.run([sys.executable, 'server.py', *a], cwd=here, env=env, capture_output=True)
cli('add-user', 'bu.sari', 'Bu Sari', 'petugas', 'petugas-123'); cli('add-user', 'pak.eko', 'Pak Eko', 'petugas', 'petugas-456')
srv = subprocess.Popen([sys.executable, 'server.py'], cwd=here, env=env, stdout=subprocess.DEVNULL); time.sleep(1.2)
try:
    A, Bc, S, E, AD, X = (C() for _ in range(6))
    ok(X.r('GET', '/api/reports')[0] == 401, 'tanpa login ditolak (401)')
    ok(A.r('POST', '/api/register', {'username': 'rani', 'name': 'Rani', 'password': 'rahasia123'})[0] == 201, 'siswa A daftar')
    ok(Bc.r('POST', '/api/register', {'username': 'dimas', 'name': 'Dimas', 'password': 'rahasia123'})[0] == 201, 'siswa B daftar')
    ok(X.r('POST', '/api/register', {'username': 'x', 'name': 'X', 'password': 'rahasia123'})[0] == 400, 'validasi username pendek')
    ok(X.r('POST', '/api/login', {'username': 'rani', 'password': 'salah-salah'})[0] == 401, 'login salah ditolak')
    png = base64.b64encode(bytes.fromhex('89504e470d0a1a0a0000')).decode()
    ok(A.r('POST', '/api/reports', {'kat': 'Pesan kasar', 'plat': 'WA', 'desc': 'pendek'})[0] == 400, 'validasi cerita terlalu pendek')
    ok(A.r('POST', '/api/reports', {'kat': 'Pesan kasar', 'plat': 'WA', 'desc': 'cerita yang cukup panjang ya', 'file': {'name': 'x.exe', 'data': base64.b64encode(b'MZ....').decode()}})[0] == 400, 'file non-gambar ditolak')
    s, d = A.r('POST', '/api/reports', {'kat': 'Pesan kasar', 'plat': 'Grup WA', 'desc': 'Ada teman yang terus mengejek di grup kelas.', 'anon': True, 'file': {'name': 'bukti.png', 'data': png}})
    ref = d['ref']; ok(s == 201 and ref.startswith('SZ-'), 'pengaduan dibuat, ref ' + ref)
    ok(Bc.r('GET', '/api/reports/' + ref)[0] == 404, 'siswa B tidak bisa lihat laporan A')
    ok(Bc.r('GET', f'/api/reports/{ref}/file')[0] == 404, 'siswa B tidak bisa unduh bukti A')
    ok(A.r('GET', f'/api/reports/{ref}/file')[0] == 200, 'siswa A bisa unduh bukti sendiri')
    ok(len(Bc.r('GET', '/api/reports')[1]['reports']) == 0, 'daftar B kosong')
    ok(A.r('POST', f'/api/reports/{ref}/advance', {})[0] == 403, 'siswa tidak bisa ubah status')
    ok(A.r('GET', '/api/activity')[0] == 403, 'siswa tidak bisa lihat log')
    ok(A.r('POST', '/api/reports', {'kat': 'Pesan kasar', 'plat': 'x', 'desc': 'cerita yang cukup panjang ya'}, {'X-Requested-With': ''})[0] == 403, 'tanpa header anti-CSRF ditolak')
    ok(S.r('POST', '/api/login', {'username': 'bu.sari', 'password': 'petugas-123'})[0] == 200, 'petugas masuk')
    E.r('POST', '/api/login', {'username': 'pak.eko', 'password': 'petugas-456'}); AD.r('POST', '/api/login', {'username': 'admin', 'password': 'admin-pass-123'})
    ok(S.r('GET', '/api/reports/' + ref)[1]['report']['pelapor'].startswith('Anonim'), 'nama pelapor anonim disembunyikan dari petugas')
    ok(S.r('POST', f'/api/reports/{ref}/advance', {})[0] == 409, 'maju status tanpa ambil laporan ditolak')
    sid = next(x['id'] for x in S.r('GET', '/api/staff')[1]['staff'] if x['name'] == 'Bu Sari')
    ok(E.r('POST', f'/api/reports/{ref}/assign', {'uid': sid})[0] == 403, 'petugas tidak bisa menugaskan orang lain')
    ok(S.r('POST', f'/api/reports/{ref}/assign', {'uid': str(sid)})[0] == 200, 'petugas mengambil laporan')
    ok(E.r('GET', '/api/reports/' + ref)[0] == 404, 'petugas lain tidak bisa akses laporan orang lain')
    for i in range(1, 6):
        n = f'Catatan langkah {i}' if i >= 3 else ''
        if i == 3: ok(S.r('POST', f'/api/reports/{ref}/advance', {})[0] == 400, 'tahap Tindak Lanjut dst. wajib catatan')
        ok(S.r('POST', f'/api/reports/{ref}/advance', {'n': n})[0] == 200, f'maju ke tahap {i}')
    ok(S.r('POST', f'/api/reports/{ref}/advance', {'n': 'lagi'})[0] == 409, 'tidak bisa melewati Selesai')
    r = A.r('GET', '/api/reports/' + ref)[1]['report']; ok(r['st'] == 5 and len(r['hist']) == 6 and r['notes'] == [], 'siswa lihat 6 status, tanpa catatan internal')
    ok(len(AD.r('GET', '/api/activity')[1]['items']) >= 6, 'admin melihat riwayat aktivitas')
    ok(A.r('POST', '/api/journal', {'e': '😊', 'n': 'Hari ini baik'})[0] == 201 and len(A.r('GET', '/api/journal')[1]['items']) == 1, 'jurnal tersimpan')
    ok(len(Bc.r('GET', '/api/journal')[1]['items']) == 0, 'jurnal A tidak terlihat B')
    last = [X.r('POST', '/api/login', {'username': 'rani', 'password': 'salahsalah'})[0] for _ in range(6)][-1]; ok(last == 429, 'pembatasan percobaan login (429)')
    h = urllib.request.urlopen(B + '/'); ok(h.status == 200 and bool(h.headers.get('Content-Security-Policy')), 'halaman statis + CSP')
finally:
    srv.terminate()
print(f'\n{fails} GAGAL' if fails else '\nSemua uji lulus'); sys.exit(1 if fails else 0)
