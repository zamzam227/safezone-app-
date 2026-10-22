#!/usr/bin/env python3
"""Safe-Zone App: server web + API + SQLite. Hanya butuh Python 3.9+ (tanpa pip install)."""
import os, sys, re, json, time, sqlite3, hashlib, hmac, secrets, base64, threading, datetime
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
HOST = os.environ.get('HOST', '127.0.0.1')
PORT = int(os.environ.get('PORT', 3000))
DATA = os.environ.get('DATA_DIR', os.path.join(ROOT, 'data'))
SECURE = os.environ.get('COOKIE_SECURE') == '1'
PROXY = os.environ.get('TRUST_PROXY') == '1'
os.makedirs(os.path.join(DATA, 'uploads'), exist_ok=True)
DB = os.path.join(DATA, 'safezone.db')
DAY = 86400000
STATUS = ['Pengaduan Diterima', 'Menunggu Peninjauan', 'Sedang Ditinjau', 'Tindak Lanjut', 'Pemantauan', 'Selesai Ditangani']
KAT = ['Pesan kasar', 'Penyebaran foto', 'Akun palsu', 'Dikucilkan online', 'Lainnya']
MAGIC = [('png', b'\x89PNG', 'image/png'), ('jpg', b'\xff\xd8\xff', 'image/jpeg'), ('pdf', b'%PDF', 'application/pdf')]
SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE NOT NULL,name TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN('siswa','petugas','admin')),pw TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,uid INTEGER NOT NULL REFERENCES users(id),exp INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS reports(ref TEXT PRIMARY KEY,owner INTEGER NOT NULL REFERENCES users(id),kat TEXT NOT NULL,plat TEXT NOT NULL,body TEXT NOT NULL,anon INTEGER NOT NULL,file TEXT,fname TEXT,assignee INTEGER REFERENCES users(id),st INTEGER NOT NULL DEFAULT 0,created INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,ref TEXT NOT NULL,s INTEGER NOT NULL,t INTEGER NOT NULL,actor TEXT NOT NULL,n TEXT);
CREATE TABLE IF NOT EXISTS notes(id INTEGER PRIMARY KEY,ref TEXT NOT NULL,t INTEGER NOT NULL,actor TEXT NOT NULL,n TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS activity(id INTEGER PRIMARY KEY,t INTEGER NOT NULL,uid INTEGER,actor TEXT NOT NULL,a TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS journal(id INTEGER PRIMARY KEY,uid INTEGER NOT NULL,e TEXT NOT NULL,n TEXT NOT NULL,t INTEGER NOT NULL);
"""

def conn():
    c = sqlite3.connect(DB, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    return c

def rows(c, sql, *a): return [dict(r) for r in c.execute(sql, a).fetchall()]
def row(c, sql, *a):
    r = c.execute(sql, a).fetchone()
    return dict(r) if r else None
def now(): return int(time.time() * 1000)

def hash_pw(pw):
    salt = os.urandom(16)
    return salt.hex() + ':' + hashlib.scrypt(pw.encode(), salt=salt, n=16384, r=8, p=1, dklen=64).hex()
def check_pw(pw, h):
    try:
        s, k = h.split(':')
        d = hashlib.scrypt(pw.encode(), salt=bytes.fromhex(s), n=16384, r=8, p=1, dklen=64)
        return hmac.compare_digest(d, bytes.fromhex(k))
    except Exception:
        return False
DUMMY = hash_pw('dummy')

def add_user(c, username, name, role, pw):
    return c.execute('INSERT INTO users(username,name,role,pw) VALUES(?,?,?,?)', (username.lower(), name, role, hash_pw(pw))).lastrowid

with conn() as _c:
    _c.executescript('PRAGMA journal_mode=WAL;' + SCHEMA)
    if len(sys.argv) > 1 and sys.argv[1] == 'add-user':
        a = sys.argv[2:]
        if len(a) != 4 or a[2] not in ('petugas', 'admin') or len(a[3]) < 8:
            sys.exit('Pemakaian: python server.py add-user <username> "<Nama>" <petugas|admin> <kata-sandi-min-8>')
        try:
            add_user(_c, a[0], a[1], a[2], a[3]); _c.commit(); print('Akun dibuat:', a[0], a[2]); sys.exit(0)
        except sqlite3.IntegrityError:
            sys.exit('Gagal: nama pengguna sudah ada.')
    if not row(_c, "SELECT 1 x FROM users WHERE role='admin'"):
        p = os.environ.get('ADMIN_PASSWORD') or secrets.token_urlsafe(9)
        add_user(_c, 'admin', 'Koordinator BK', 'admin', p); _c.commit()
        print('Akun admin dibuat (kata sandi dari ADMIN_PASSWORD).' if os.environ.get('ADMIN_PASSWORD')
              else f'Akun admin dibuat. Username: admin  Kata sandi: {p}  (catat sekarang, tidak ditampilkan lagi)')

class Err(Exception):
    def __init__(s, code, msg): s.code, s.msg = code, msg
def fail(code, msg): raise Err(code, msg)
def S(v, mn, mx, msg):
    v = v.strip() if isinstance(v, str) else ''
    if not mn <= len(v) <= mx: fail(400, msg)
    return v
def sha(t): return hashlib.sha256(t.encode()).hexdigest()

TR, LK = {}, threading.Lock()
def count(key, win, inc=0):
    with LK:
        n, t = TR.get(key, (0, time.time()))
        if time.time() - t > win: n, t = 0, time.time()
        n += inc; TR[key] = (n, t); return n

def auth(c, cookie):
    m = re.search(r'(?:^|;\s*)sz=([a-f0-9]{64})', cookie or '')
    if not m: return None
    return row(c, 'SELECT u.id,u.username,u.name,u.role FROM sessions s JOIN users u ON u.id=s.uid WHERE s.token=? AND s.exp>?', sha(m.group(1)), now())
def new_session(c, uid):
    tok = secrets.token_hex(32)
    c.execute('DELETE FROM sessions WHERE exp<?', (now(),))
    c.execute('INSERT INTO sessions VALUES(?,?,?)', (sha(tok), uid, now() + 7 * DAY))
    return {'Set-Cookie': f'sz={tok}; HttpOnly; SameSite=Strict; Path=/; Max-Age={7*86400}' + ('; Secure' if SECURE else '')}
def need(me, *roles):
    if not me: fail(401, 'Silakan masuk dulu.')
    if roles and me['role'] not in roles: fail(403, 'Kamu tidak punya akses untuk ini.')
def act(c, me, a): c.execute('INSERT INTO activity(t,uid,actor,a) VALUES(?,?,?,?)', (now(), me['id'], me['name'], a))
def pub(u): return {'id': u['id'], 'name': u['name'], 'role': u['role']}

BASE = 'SELECT r.*,o.name oname,a.name aname FROM reports r JOIN users o ON o.id=r.owner LEFT JOIN users a ON a.id=r.assignee'
def visible(r, me):
    return me['role'] == 'admin' or (me['role'] == 'siswa' and r['owner'] == me['id']) or \
           (me['role'] == 'petugas' and (r['assignee'] is None or r['assignee'] == me['id']))
def get_rep(c, ref, me):
    r = row(c, BASE + ' WHERE r.ref=?', ref)
    if not r or not visible(r, me): fail(404, 'Pengaduan tidak ditemukan.')
    return r
def ser(c, r, me):
    staff = me['role'] != 'siswa'
    return {'ref': r['ref'], 'kat': r['kat'], 'plat': r['plat'], 'desc': r['body'], 'anon': bool(r['anon']), 'st': r['st'],
            'assign': r['aname'] or '', 'assignId': r['assignee'],
            'pelapor': r['oname'] if me['role'] == 'siswa' else ('Anonim (disembunyikan)' if r['anon'] else r['oname']),
            'hasFile': bool(r['file']), 'bukti': [r['fname']] if r['fname'] else [],
            'hist': [{'s': h['s'], 't': h['t'], 'by': h['actor'], **({'n': h['n']} if h['n'] else {})} for h in rows(c, 'SELECT s,t,actor,n FROM events WHERE ref=? ORDER BY id', r['ref'])],
            'notes': [{'t': x['t'], 'by': x['actor'], 'n': x['n']} for x in rows(c, 'SELECT t,actor,n FROM notes WHERE ref=? ORDER BY id', r['ref'])] if staff else []}

def api(h, c, M, p, b):
    me = auth(c, h.headers.get('Cookie'))
    ip = (h.headers.get('X-Forwarded-For', '').split(',')[0].strip() if PROXY else h.client_address[0])
    if M == 'GET' and p == '/api/me': return 200, {'user': pub(me) if me else None}, {}
    if M == 'POST' and p == '/api/register':
        un = S(b.get('username'), 3, 24, 'Nama pengguna 3-24 karakter.').lower()
        nm = S(b.get('name'), 2, 60, 'Nama panggilan 2-60 karakter.')
        if not re.fullmatch(r'[a-z0-9_.]+', un): fail(400, 'Nama pengguna hanya huruf, angka, titik, dan garis bawah.')
        pw = b.get('password')
        if not isinstance(pw, str) or not 8 <= len(pw) <= 100: fail(400, 'Kata sandi minimal 8 karakter.')
        if count('r|' + ip, 3600, 1) > 20: fail(429, 'Terlalu banyak pendaftaran. Coba lagi nanti.')
        try: uid = add_user(c, un, nm, 'siswa', pw)
        except sqlite3.IntegrityError: fail(409, 'Nama pengguna sudah dipakai.')
        return 201, {'user': {'id': uid, 'name': nm, 'role': 'siswa'}}, new_session(c, uid)
    if M == 'POST' and p == '/api/login':
        un = S(b.get('username'), 1, 40, 'Isi nama pengguna.').lower(); k = f'l|{ip}|{un}'
        if count(k, 600) >= 5: fail(429, 'Terlalu banyak percobaan. Coba lagi 10 menit lagi.')
        u = row(c, 'SELECT * FROM users WHERE username=?', un); pw = b.get('password') if isinstance(b.get('password'), str) else ''
        ok = check_pw(pw, u['pw'] if u else DUMMY) and u is not None
        if not ok: count(k, 600, 1); fail(401, 'Nama pengguna atau kata sandi salah.')
        TR.pop(k, None); return 200, {'user': pub(u)}, new_session(c, u['id'])
    if M == 'POST' and p == '/api/logout':
        m = re.search(r'sz=([a-f0-9]{64})', h.headers.get('Cookie') or '')
        if m: c.execute('DELETE FROM sessions WHERE token=?', (sha(m.group(1)),))
        return 200, {'ok': True}, {'Set-Cookie': 'sz=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'}
    need(me)
    if M == 'GET' and p == '/api/staff':
        need(me, 'petugas', 'admin')
        return 200, {'staff': rows(c, "SELECT id,name FROM users WHERE role IN('petugas','admin') ORDER BY name")}, {}
    if M == 'GET' and p == '/api/reports':
        if me['role'] == 'siswa': rs = rows(c, BASE + ' WHERE r.owner=? ORDER BY r.created DESC LIMIT 200', me['id'])
        elif me['role'] == 'admin': rs = rows(c, BASE + ' ORDER BY r.created DESC LIMIT 500')
        else: rs = rows(c, BASE + ' WHERE r.assignee IS NULL OR r.assignee=? ORDER BY r.created DESC LIMIT 500', me['id'])
        return 200, {'reports': [ser(c, r, me) for r in rs]}, {}
    if M == 'POST' and p == '/api/reports':
        need(me, 'siswa')
        kat = S(b.get('kat'), 1, 40, 'Pilih jenis kejadian.'); plat = S(b.get('plat'), 1, 80, 'Tulis di mana kejadiannya.')
        body = S(b.get('desc'), 20, 3000, 'Cerita minimal 20 huruf.')
        if kat not in KAT: fail(400, 'Jenis kejadian tidak dikenal.')
        file = fname = None; f = b.get('file')
        if f:
            try: buf = base64.b64decode(str(f.get('data') or ''), validate=True)
            except Exception: fail(400, 'Berkas bukti tidak valid.')
            if not buf or len(buf) > 2097152: fail(400, 'Berkas bukti maksimal 2 MB.')
            mg = next((x for x in MAGIC if buf.startswith(x[1])), None)
            if not mg: fail(400, 'Bukti harus berupa gambar PNG/JPG atau PDF.')
            file = secrets.token_hex(16) + '.' + mg[0]; fname = re.sub(r'[^\w.\- ]', '_', str(f.get('name') or 'bukti'))[:80]
            with open(os.path.join(DATA, 'uploads', file), 'wb') as fh: fh.write(buf)
        d = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d')
        for i in range(5):
            ref = f'SZ-{d}-{secrets.randbelow(900000) + 100000}'
            if not row(c, 'SELECT 1 x FROM reports WHERE ref=?', ref): break
        t = now()
        c.execute('INSERT INTO reports(ref,owner,kat,plat,body,anon,file,fname,created) VALUES(?,?,?,?,?,?,?,?,?)', (ref, me['id'], kat, plat, body, 1 if b.get('anon') else 0, file, fname, t))
        c.execute('INSERT INTO events(ref,s,t,actor) VALUES(?,0,?,?)', (ref, t, 'Sistem'))
        return 201, {'ref': ref}, {}
    m = re.fullmatch(r'/api/reports/(SZ-\d{8}-\d{6})(?:/(file|assign|notes|advance))?', p)
    if m:
        r = get_rep(c, m.group(1), me); sub = m.group(2)
        if M == 'GET' and not sub: return 200, {'report': ser(c, r, me)}, {}
        if M == 'GET' and sub == 'file':
            if not r['file']: fail(404, 'Tidak ada bukti.')
            ext = r['file'].split('.')[1]; mg = next(x for x in MAGIC if x[0] == ext)
            with open(os.path.join(DATA, 'uploads', r['file']), 'rb') as fh: return 'file', fh.read(), {'Content-Type': mg[2], 'Content-Disposition': f'attachment; filename="bukti.{ext}"'}
        if M == 'POST' and sub == 'assign':
            need(me, 'petugas', 'admin'); u = b.get('uid')
            if u is not None:
                if isinstance(u, bool) or not (isinstance(u, int) or (isinstance(u, str) and u.isdigit())): fail(400, 'Petugas tidak valid.')
                u = int(u)
            if me['role'] == 'petugas' and not ((u == me['id'] and r['assignee'] is None) or (u is None and r['assignee'] == me['id'])):
                fail(403, 'Petugas hanya bisa mengambil laporan yang belum ditugaskan atau melepas laporannya sendiri.')
            nm = '(kosong)'
            if u is not None:
                s = row(c, "SELECT name FROM users WHERE id=? AND role IN('petugas','admin')", u)
                if not s: fail(400, 'Petugas tidak ditemukan.')
                nm = s['name']
            c.execute('UPDATE reports SET assignee=? WHERE ref=?', (u, r['ref'])); act(c, me, f"Menugaskan {r['ref']} ke {nm}")
            return 200, {'ok': True}, {}
        if M == 'POST' and sub == 'notes':
            need(me, 'petugas', 'admin'); n = S(b.get('n'), 3, 1000, 'Catatan minimal 3 huruf.')
            c.execute('INSERT INTO notes(ref,t,actor,n) VALUES(?,?,?,?)', (r['ref'], now(), me['name'], n)); act(c, me, f"Catatan tindak lanjut pada {r['ref']}")
            return 200, {'ok': True}, {}
        if M == 'POST' and sub == 'advance':
            need(me, 'petugas', 'admin')
            if me['role'] == 'petugas' and r['assignee'] != me['id']: fail(409, 'Ambil laporan ini dulu lewat kolom Petugas.')
            if r['st'] >= 5: fail(409, 'Laporan sudah selesai ditangani.')
            n = b['n'].strip()[:1000] if isinstance(b.get('n'), str) else ''
            if r['st'] >= 2 and len(n) < 3: fail(400, 'Isi catatan tindak lanjut sebelum mengubah status.')
            t, s = now(), r['st'] + 1
            if c.execute('UPDATE reports SET st=? WHERE ref=? AND st=?', (s, r['ref'], r['st'])).rowcount == 0: fail(409, 'Status sudah berubah, muat ulang.')
            c.execute('INSERT INTO events(ref,s,t,actor,n) VALUES(?,?,?,?,?)', (r['ref'], s, t, me['name'], n or None))
            if n: c.execute('INSERT INTO notes(ref,t,actor,n) VALUES(?,?,?,?)', (r['ref'], t, me['name'], n))
            act(c, me, f'Status {r["ref"]} menjadi "{STATUS[s]}"')
            return 200, {'ok': True}, {}
    if p == '/api/journal':
        need(me, 'siswa')
        if M == 'GET': return 200, {'items': rows(c, 'SELECT e,n,t FROM journal WHERE uid=? ORDER BY id DESC LIMIT 100', me['id'])}, {}
        if M == 'POST':
            e = S(b.get('e'), 1, 8, 'Pilih perasaan.'); n = S(b.get('n'), 1, 1000, 'Tulis sedikit cerita.')
            c.execute('INSERT INTO journal(uid,e,n,t) VALUES(?,?,?,?)', (me['id'], e, n, now())); return 201, {'ok': True}, {}
    if M == 'GET' and p == '/api/activity':
        need(me, 'petugas', 'admin')
        rs = rows(c, 'SELECT t,actor,a FROM activity ORDER BY id DESC LIMIT 300') if me['role'] == 'admin' else rows(c, 'SELECT t,actor,a FROM activity WHERE uid=? ORDER BY id DESC LIMIT 300', me['id'])
        return 200, {'items': [{'t': x['t'], 'by': x['actor'], 'a': x['a']} for x in rs]}, {}
    fail(404, 'Tidak ditemukan.')

PUB = os.path.join(ROOT, 'public')
FILES = {'/': 'index.html', '/index.html': 'index.html', '/app.js': 'app.js', '/logo.png': 'logo.png'}
TYPES = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.png': 'image/png'}
CSP = "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"

class H(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def log_message(self, *a): pass
    def reply(self, code, body, headers):
        self.send_response(code)
        for k, v in {'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer', 'Content-Security-Policy': CSP, 'Content-Length': str(len(body)), **headers}.items(): self.send_header(k, v)
        self.end_headers(); self.wfile.write(body)
    def js(self, code, obj, headers=None):
        self.reply(code, json.dumps(obj, ensure_ascii=False).encode(), {'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', **(headers or {})})
    def do_GET(self): self.go('GET')
    def do_POST(self): self.go('POST')
    def go(self, M):
        p = urlparse(self.path).path
        try:
            if p.startswith('/api/'):
                n = int(self.headers.get('Content-Length') or 0)
                if n > 3_000_000: self.close_connection = True; fail(413, 'Permintaan terlalu besar.')
                raw = self.rfile.read(n) if n else b''
                if M == 'POST' and self.headers.get('X-Requested-With') != 'fetch': fail(403, 'Permintaan ditolak.')
                try: b = json.loads(raw) if raw else {}
                except ValueError: b = None
                if not isinstance(b, dict): fail(400, 'Format data tidak valid.')
                c = conn()
                try:
                    code, obj, hd = api(self, c, M, p, b); c.commit()
                finally: c.close()
                if code == 'file': return self.reply(200, obj, {**hd, 'Cache-Control': 'private, no-store'})
                return self.js(code, obj, hd)
            f = FILES.get(p)
            if not f or M != 'GET': fail(404, 'Tidak ditemukan.')
            with open(os.path.join(PUB, f), 'rb') as fh: self.reply(200, fh.read(), {'Content-Type': TYPES[os.path.splitext(f)[1]], 'Cache-Control': 'no-cache'})
        except Err as e: self.js(e.code, {'error': e.msg})
        except Exception as e:
            print('ERROR', repr(e)); self.js(500, {'error': 'Terjadi kesalahan server.'})

if __name__ == '__main__':
    srv = ThreadingHTTPServer((HOST, PORT), H)
    print(f'Safe-Zone App berjalan di http://localhost:{PORT}  (hentikan dengan Ctrl+C)')
    try: srv.serve_forever()
    except KeyboardInterrupt: print('\nServer dihentikan.')
