"""
Student Record Management System
Flow:  Browser Form  ->  Controller (route handler)  ->  SQLite Database  ->  HTML Result

Run:   python app.py
Open:  http://localhost:8000

Uses only the Python standard library (http.server + sqlite3).
"""
import html
import os
import re
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs, urlencode, quote, unquote

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "students.db")
PORT = 8000

MSG_CREATED = "Student record successfully created!"
MSG_CREATE_ERROR = "Unable to save student record. Please check your input."


# ═════════════════════════ DATABASE LAYER ═════════════════════════
def db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    first_run = not os.path.exists(DB_FILE)
    with db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            student_id  TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            program     TEXT NOT NULL,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        );
        -- Deleted records are MOVED here, never destroyed.
        CREATE TABLE IF NOT EXISTS students_archive (
            archive_id  INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id  TEXT NOT NULL,
            name        TEXT NOT NULL,
            program     TEXT NOT NULL,
            created_at  TEXT,
            deleted_at  TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)
        if first_run:  # sample rows so the dashboard is not empty on first launch
            conn.executemany("INSERT INTO students (student_id, name, program) VALUES (?,?,?)",
                             [("2026-001", "Juan Dela Cruz", "BSIT"),
                              ("2026-002", "Maria Santos", "BSCS")])


# ═════════════════════════ VIEW HELPERS ═════════════════════════
def e(text):
    return html.escape(str(text if text is not None else ""))


def initials(name):
    parts = name.split()
    if not parts:
        return "?"
    return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()


NAV = [
    ("dashboard", "/", "🏠", "Dashboard"),
    ("students", "/students", "👨‍🎓", "Students"),
    ("add", "/add", "➕", "Add Student"),
    ("records", "/records", "📋", "Student Records"),
    ("archived", "/archived", "🗃️", "Archived Records"),
]

CSS = """
:root{
  --navy:#1E3A5F; --blue:#2563EB; --sky:#38BDF8; --green:#22C55E; --red:#EF4444;
  --bg:#F8FAFC; --card:#FFFFFF; --text:#1E293B; --muted:#64748B; --line:#E2E8F0;
  --shadow:0 1px 3px rgba(15,23,42,.06),0 6px 20px rgba(15,23,42,.05);
  --shadow-lg:0 4px 8px rgba(15,23,42,.06),0 14px 32px rgba(15,23,42,.10);
  --radius:16px; --sidebar:264px;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--text);
  font-family:"Inter","Segoe UI",system-ui,-apple-system,Roboto,sans-serif;line-height:1.5;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}

/* ---------- Sidebar ---------- */
.sidebar{position:fixed;inset:0 auto 0 0;width:var(--sidebar);background:linear-gradient(180deg,var(--navy) 0%,#16304f 100%);
  color:#fff;display:flex;flex-direction:column;padding:1.4rem 1rem;z-index:50;transition:transform .25s ease}
.brand{display:flex;align-items:center;gap:.75rem;padding:.25rem .6rem 1.4rem;border-bottom:1px solid rgba(255,255,255,.12);margin-bottom:1rem}
.brand .logo{width:42px;height:42px;border-radius:12px;background:var(--sky);display:grid;place-items:center;font-size:1.4rem;box-shadow:0 4px 12px rgba(56,189,248,.4)}
.brand b{display:block;font-size:1.05rem;letter-spacing:.2px} .brand small{color:#B6C7DD;font-size:.75rem}
.nav-label{font-size:.7rem;text-transform:uppercase;letter-spacing:1.2px;color:#8FA6C4;padding:.4rem .8rem;margin-top:.4rem}
.nav-item{display:flex;align-items:center;gap:.8rem;padding:.75rem .9rem;border-radius:12px;color:#D6E2F1;font-weight:500;
  margin-bottom:.25rem;transition:background .18s,transform .18s,color .18s}
.nav-item .ico{width:1.5rem;text-align:center;font-size:1.1rem}
.nav-item:hover{background:rgba(255,255,255,.10);color:#fff;transform:translateX(3px)}
.nav-item.active{background:var(--blue);color:#fff;box-shadow:0 6px 16px rgba(37,99,235,.45)}
.side-foot{margin-top:auto;font-size:.75rem;color:#8FA6C4;padding:.8rem .6rem 0;border-top:1px solid rgba(255,255,255,.12)}
.scrim{display:none;position:fixed;inset:0;background:rgba(15,23,42,.45);z-index:40}

/* ---------- Main ---------- */
.main{margin-left:var(--sidebar);min-height:100vh}
.topbar{display:flex;align-items:center;gap:1rem;padding:1.1rem 2rem;background:rgba(248,250,252,.85);backdrop-filter:blur(8px);
  position:sticky;top:0;z-index:30;border-bottom:1px solid var(--line)}
.topbar h1{font-size:1.35rem;margin:0;color:var(--navy)}
.topbar p{margin:0;color:var(--muted);font-size:.85rem}
.burger{display:none;border:0;background:var(--navy);color:#fff;width:42px;height:42px;border-radius:12px;font-size:1.3rem;cursor:pointer}
.content{padding:1.8rem 2rem 3rem;max-width:1200px}

/* ---------- Cards / buttons ---------- */
.card{background:var(--card);border-radius:var(--radius);box-shadow:var(--shadow);padding:1.5rem;margin-bottom:1.5rem}
.card h2{margin:0 0 1rem;font-size:1.1rem;color:var(--navy)}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:.4rem;border:0;border-radius:12px;padding:.7rem 1.2rem;
  font-family:inherit;font-size:.92rem;font-weight:600;line-height:1.25;cursor:pointer;color:#fff;transition:transform .15s,box-shadow .15s,background .15s}
.btn:hover{transform:translateY(-2px);box-shadow:0 8px 18px rgba(15,23,42,.18)}
.btn:active{transform:translateY(0)}
.btn-primary{background:var(--blue)} .btn-primary:hover{background:#1D4FD8}
.btn-danger{background:var(--red)} .btn-danger:hover{background:#DC2626}
.btn-success{background:var(--green)} .btn-success:hover{background:#16A34A}
.btn-ghost{background:#EEF2F7;color:var(--text)} .btn-ghost:hover{background:#E2E8F0}
.btn-lg{padding:.9rem 1.6rem;font-size:1rem;width:100%}
.btn-sm{padding:.45rem .8rem;font-size:.82rem;border-radius:10px}

/* ---------- Hero + stats ---------- */
.hero{background:linear-gradient(120deg,var(--navy),var(--blue));color:#fff;border-radius:var(--radius);padding:1.8rem 2rem;
  display:flex;justify-content:space-between;align-items:center;gap:1rem;flex-wrap:wrap;box-shadow:var(--shadow-lg);margin-bottom:1.5rem}
.hero h2{margin:0 0 .3rem;font-size:1.4rem} .hero p{margin:0;color:#DCE8FB;max-width:520px}
.hero .btn{background:#fff;color:var(--navy)}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:1.2rem;margin-bottom:1.5rem}
.stat{background:var(--card);border-radius:var(--radius);box-shadow:var(--shadow);padding:1.4rem;display:flex;align-items:center;gap:1rem;
  transition:transform .2s,box-shadow .2s;border-left:5px solid var(--blue)}
.stat:hover{transform:translateY(-4px);box-shadow:var(--shadow-lg)}
.stat .ico{width:54px;height:54px;border-radius:14px;display:grid;place-items:center;font-size:1.6rem;background:#E8F0FE}
.stat .num{font-size:2rem;font-weight:800;color:var(--navy);line-height:1} .stat .lbl{color:var(--muted);font-size:.88rem;margin-top:.25rem}
.stat.green{border-color:var(--green)} .stat.green .ico{background:#DCFCE7}
.stat.sky{border-color:var(--sky)} .stat.sky .ico{background:#E0F5FE}

/* ---------- Data-flow diagram ---------- */
.flow{display:flex;align-items:stretch;gap:.4rem}
.step{flex:1;min-width:0;text-align:center;padding:1rem .6rem;border-radius:14px;background:#EFF6FF;border:1px solid #DBEAFE;transition:transform .18s,box-shadow .18s}
.step:hover{transform:translateY(-3px);box-shadow:var(--shadow)}
.step .n{width:28px;height:28px;border-radius:50%;background:var(--blue);color:#fff;font-size:.8rem;font-weight:700;display:grid;place-items:center;margin:0 auto .5rem}
.step b{display:block;font-size:.88rem;color:var(--navy)} .step small{display:block;color:var(--muted);font-size:.72rem;margin-top:.2rem;word-break:break-word}
.step.db{background:#E0F5FE;border-color:#BAE6FD} .step.db .n{background:var(--sky)}
.step.ok{background:#DCFCE7;border-color:#BBF7D0} .step.ok .n{background:var(--green)}
.arrow{align-self:center;color:var(--sky);font-weight:800;font-size:1.3rem}
.crud{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem}
.crud-item{border-radius:14px;padding:1rem;color:#fff;transition:transform .18s,box-shadow .18s}
.crud-item:hover{transform:translateY(-3px);box-shadow:var(--shadow-lg)}
.crud-item .verb{font-size:.78rem;opacity:.85;letter-spacing:.5px} .crud-item .act{font-size:1.15rem;font-weight:800;margin:.15rem 0 .4rem}
.crud-item code{background:rgba(255,255,255,.18);padding:.15rem .5rem;border-radius:8px;font-size:.75rem}
.c-post{background:var(--blue)} .c-select{background:var(--sky);color:#0C4A6E} .c-select code{background:rgba(255,255,255,.5)}
.c-update{background:var(--navy)} .c-delete{background:var(--red)}

/* ---------- Forms ---------- */
.form-wrap{max-width:560px;margin:0 auto}
.form-wrap .card{padding:2rem}
.form-wrap h2{text-align:center;font-size:1.4rem;margin-bottom:.3rem}
.form-wrap .hint{text-align:center;color:var(--muted);margin:0 0 1.5rem;font-size:.9rem}
.field{margin-bottom:1.1rem}
.field label{display:block;font-weight:600;font-size:.88rem;margin-bottom:.35rem;color:var(--navy)}
.field input{width:100%;padding:.8rem 1rem;border:1.5px solid var(--line);border-radius:12px;font:inherit;background:#fff;transition:border .15s,box-shadow .15s}
.field input:focus{outline:0;border-color:var(--sky);box-shadow:0 0 0 4px rgba(56,189,248,.22)}
.field input:disabled{background:#F1F5F9;color:var(--muted)}
.form-actions{display:flex;gap:.7rem;margin-top:1.4rem} .form-actions .btn-ghost{flex:0 0 auto}

/* ---------- Toolbar / table ---------- */
.toolbar{display:flex;gap:.8rem;align-items:center;flex-wrap:wrap;margin-bottom:1.1rem}
.search{flex:1;min-width:220px;display:flex;gap:.5rem}
.search input{flex:1;min-width:0;padding:.7rem 1rem .7rem 2.6rem;border:1.5px solid var(--line);border-radius:12px;font:inherit;
  background:#fff url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' fill='none' stroke='%2364748B' stroke-width='2' stroke-linecap='round'%3E%3Ccircle cx='8' cy='8' r='6'/%3E%3Cpath d='m13 13 4 4'/%3E%3C/svg%3E") no-repeat 14px center}
.search input:focus{outline:0;border-color:var(--sky);box-shadow:0 0 0 4px rgba(56,189,248,.22)}
.count{background:#E8F0FE;color:var(--blue);font-weight:700;font-size:.85rem;padding:.45rem .9rem;border-radius:999px;white-space:nowrap}
.table-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse}
th{font-size:.72rem;text-transform:uppercase;letter-spacing:.8px;color:var(--muted);text-align:left;padding:.8rem 1rem;background:#F8FAFC;border-bottom:2px solid var(--line)}
th:first-child{border-radius:12px 0 0 0} th:last-child{border-radius:0 12px 0 0}
td{padding:.9rem 1rem;border-bottom:1px solid var(--line);vertical-align:middle}
tbody tr{transition:background .15s} tbody tr:hover{background:#F1F7FF}
.sid{font-weight:700;color:var(--navy);font-variant-numeric:tabular-nums}
.pill{display:inline-block;background:#E0F5FE;color:#0369A1;font-weight:700;font-size:.78rem;padding:.25rem .7rem;border-radius:999px}
.actions{display:flex;gap:.5rem;flex-wrap:wrap} .actions form{margin:0}
.empty{text-align:center;color:var(--muted);padding:2.5rem 1rem}
.empty .big{font-size:2.4rem;display:block;margin-bottom:.4rem}

/* ---------- Student directory cards ---------- */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:1.1rem}
.person{background:var(--card);border-radius:var(--radius);box-shadow:var(--shadow);padding:1.4rem;text-align:center;transition:transform .2s,box-shadow .2s}
.person:hover{transform:translateY(-4px);box-shadow:var(--shadow-lg)}
.avatar{width:64px;height:64px;border-radius:50%;margin:0 auto .8rem;display:grid;place-items:center;color:#fff;font-weight:800;font-size:1.2rem;
  background:linear-gradient(135deg,var(--blue),var(--sky))}
.person b{display:block;color:var(--navy)} .person small{color:var(--muted);display:block;margin-bottom:.6rem}
.recent{list-style:none;margin:0;padding:0} .recent li{display:flex;align-items:center;gap:.8rem;padding:.7rem 0;border-bottom:1px solid var(--line)}
.recent li:last-child{border:0} .recent .avatar{width:40px;height:40px;font-size:.85rem;margin:0}
.recent .who{flex:1;min-width:0} .recent .who b{display:block} .recent .who small{color:var(--muted)}

/* ---------- Toast ---------- */
.toast{position:fixed;top:1.2rem;right:1.2rem;z-index:100;min-width:280px;max-width:min(420px,calc(100vw - 2rem));display:flex;gap:.8rem;align-items:flex-start;
  padding:1rem 1.1rem;border-radius:14px;color:#fff;box-shadow:var(--shadow-lg);animation:slide .35s ease}
.toast.success{background:var(--green)} .toast.error{background:var(--red)}
.toast .ti{font-size:1.3rem;line-height:1.2} .toast b{display:block} .toast small{opacity:.95}
.toast button{margin-left:auto;background:none;border:0;color:#fff;font-size:1.2rem;cursor:pointer;opacity:.8}
.toast.hide{opacity:0;transform:translateX(30px);transition:.3s}
@keyframes slide{from{opacity:0;transform:translateX(40px)}to{opacity:1;transform:none}}

/* ---------- Confirm dialog ---------- */
dialog{border:0;border-radius:20px;padding:0;box-shadow:0 20px 60px rgba(15,23,42,.35);max-width:400px;width:calc(100% - 2rem);animation:pop .2s ease}
dialog::backdrop{background:rgba(15,23,42,.55);backdrop-filter:blur(2px)}
dialog form{padding:2rem;text-align:center}
.dlg-icon{width:64px;height:64px;border-radius:50%;background:#FEE2E2;display:grid;place-items:center;font-size:1.8rem;margin:0 auto 1rem}
dialog h3{margin:0 0 .4rem;color:var(--navy)} dialog p{margin:0 0 .3rem;color:var(--muted)}
#confirmName{display:block;color:var(--text);margin-bottom:1.3rem}
.dlg-actions{display:flex;gap:.7rem;justify-content:center;margin-top:1.2rem}
@keyframes pop{from{opacity:0;transform:scale(.94)}to{opacity:1;transform:none}}

/* ---------- Responsive ---------- */
@media (max-width:1100px){.crud{grid-template-columns:repeat(2,1fr)}}
@media (max-width:960px){
  .sidebar{transform:translateX(-100%)} body.nav-open .sidebar{transform:none;box-shadow:var(--shadow-lg)}
  body.nav-open .scrim{display:block}
  .main{margin-left:0} .burger{display:grid;place-items:center}
  .topbar,.content{padding-left:1.2rem;padding-right:1.2rem}
  .flow{flex-direction:column} .arrow{transform:rotate(90deg);line-height:1}
  .step{display:flex;align-items:center;gap:.8rem;text-align:left;padding:.8rem 1rem} .step .n{margin:0;flex:none}
}
@media (max-width:720px){
  .stats{grid-template-columns:1fr} .crud{grid-template-columns:1fr}
  .hero{padding:1.4rem} .form-wrap .card{padding:1.4rem}
  table,thead,tbody,tr,td{display:block} thead{position:absolute;left:-9999px}
  tr{background:#fff;border:1px solid var(--line);border-radius:14px;margin-bottom:.8rem;padding:.4rem .2rem}
  td{border:0;display:flex;justify-content:space-between;gap:1rem;align-items:center;padding:.5rem 1rem}
  td::before{content:attr(data-label);font-size:.72rem;text-transform:uppercase;letter-spacing:.7px;color:var(--muted);font-weight:700}
  .toolbar .btn{width:100%} .search{flex-basis:100%;min-width:0} .search .btn{width:auto;flex:none}
}
"""

JS = """
const body=document.body;
document.getElementById('burger').onclick=()=>body.classList.toggle('nav-open');
document.getElementById('scrim').onclick=()=>body.classList.remove('nav-open');

/* toast: auto-dismiss */
const toast=document.getElementById('toast');
if(toast){
  const close=()=>{toast.classList.add('hide');setTimeout(()=>toast.remove(),300)};
  toast.querySelector('button').onclick=close; setTimeout(close,6000);
  history.replaceState(null,'',location.pathname+location.search.replace(/[?&](kind|msg|detail)=[^&]*/g,'').replace(/^&/,'?'));
}

/* archive confirmation dialog */
const dlg=document.getElementById('confirmDialog');
document.querySelectorAll('form[data-confirm]').forEach(f=>{
  f.addEventListener('submit',ev=>{
    if(f.dataset.ok) return;
    ev.preventDefault();
    if(typeof dlg.showModal!=='function'){ if(confirm('Are you sure you want to archive this student record?')) f.submit(); return; }
    document.getElementById('confirmName').textContent=f.dataset.name||'';
    dlg.returnValue=''; dlg.showModal();
    dlg.addEventListener('close',()=>{ if(dlg.returnValue==='ok'){ f.dataset.ok='1'; f.submit(); } },{once:true});
  });
});
"""


def layout(active, title, subtitle, body, toast=None):
    nav = "".join(
        f'<a class="nav-item{" active" if key == active else ""}" href="{href}"><span class="ico">{ico}</span>{label}</a>'
        for key, href, ico, label in NAV)

    toast_html = ""
    if toast:
        kind, msg, detail = toast
        icon = "✅" if kind == "success" else "⚠️"
        det = f"<small>{e(detail)}</small>" if detail else ""
        toast_html = (f'<div class="toast {e(kind)}" id="toast" role="alert"><span class="ti">{icon}</span>'
                      f'<div><b>{e(msg)}</b>{det}</div><button aria-label="Close">×</button></div>')

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} · Student Record Management</title><style>{CSS}</style></head><body>
<aside class="sidebar">
  <div class="brand"><div class="logo">🎓</div><div><b>EduRecords</b><small>Student Record System</small></div></div>
  <div class="nav-label">Menu</div>{nav}
  <div class="side-foot">Form → Controller → Database → Result</div>
</aside>
<div class="scrim" id="scrim"></div>
<div class="main">
  <header class="topbar"><button class="burger" id="burger" aria-label="Menu">☰</button>
    <div><h1>{e(title)}</h1><p>{e(subtitle)}</p></div></header>
  <div class="content">{body}</div>
</div>
{toast_html}
<dialog id="confirmDialog"><form method="dialog">
  <div class="dlg-icon">🗃️</div><h3>Archive Record</h3>
  <p>Are you sure you want to archive this student record?</p><b id="confirmName"></b>
  <p style="font-size:.82rem">It will be moved to Archived Records, not deleted permanently.</p>
  <div class="dlg-actions"><button class="btn btn-ghost" value="cancel">Cancel</button>
  <button class="btn btn-danger" value="ok">Yes, Archive</button></div>
</form></dialog>
<script>{JS}</script></body></html>"""


def student_row(s):
    sid = e(s["student_id"])
    href = quote(s["student_id"], safe="")
    return f"""<tr>
      <td data-label="Student ID" class="sid">{sid}</td>
      <td data-label="Name">{e(s['name'])}</td>
      <td data-label="Program"><span class="pill">{e(s['program'])}</span></td>
      <td data-label="Actions"><div class="actions">
        <a class="btn btn-primary btn-sm" href="/students/{href}/edit">✏️ Edit</a>
        <form method="POST" action="/students/{href}/delete" data-confirm data-name="{sid} · {e(s['name'])}">
          <button class="btn btn-danger btn-sm">🗑️ Delete</button></form>
      </div></td></tr>"""


# ═════════════════════════ PAGES (VIEWS) ═════════════════════════
def counts(conn):
    active = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    archived = conn.execute("SELECT COUNT(*) FROM students_archive").fetchone()[0]
    return active, archived


def render_dashboard(toast=None):
    with db() as conn:
        active, archived = counts(conn)
        recent = conn.execute("SELECT * FROM students ORDER BY created_at DESC, rowid DESC LIMIT 5").fetchall()

    recent_html = "".join(
        f'<li><div class="avatar">{e(initials(s["name"]))}</div><div class="who"><b>{e(s["name"])}</b>'
        f'<small>{e(s["student_id"])}</small></div><span class="pill">{e(s["program"])}</span></li>'
        for s in recent) or '<li class="empty">No records yet.</li>'

    body = f"""
<section class="hero"><div><h2>Welcome to the Student Record Management System</h2>
  <p>Create, view, update and archive student records. Every action goes through a form, a controller and the database.</p></div>
  <a class="btn" href="/add">➕ Add Student</a></section>

<section class="stats">
  <div class="stat"><div class="ico">👨‍🎓</div><div><div class="num">{active + archived}</div><div class="lbl">Total Students</div></div></div>
  <div class="stat green"><div class="ico">✅</div><div><div class="num">{active}</div><div class="lbl">Active Records</div></div></div>
  <div class="stat sky"><div class="ico">🗃️</div><div><div class="num">{archived}</div><div class="lbl">Archived Records</div></div></div>
</section>

<section class="card"><h2>🔄 Application Data Flow</h2>
  <div class="flow">
    <div class="step"><div class="n">1</div><div><b>User Input</b><small>ID, Name, Program</small></div></div><span class="arrow">→</span>
    <div class="step"><div class="n">2</div><div><b>Frontend Form</b><small>&lt;form method="POST"&gt;</small></div></div><span class="arrow">→</span>
    <div class="step"><div class="n">3</div><div><b>Controller / Route</b><small>POST /students</small></div></div><span class="arrow">→</span>
    <div class="step db"><div class="n">4</div><div><b>Database INSERT</b><small>INSERT INTO students</small></div></div><span class="arrow">→</span>
    <div class="step ok"><div class="n">5</div><div><b>Success Response</b><small>Green notification</small></div></div><span class="arrow">→</span>
    <div class="step db"><div class="n">6</div><div><b>Display Records</b><small>SELECT * FROM students</small></div></div>
  </div></section>

<section class="card"><h2>🧩 CRUD Operations</h2>
  <div class="crud">
    <div class="crud-item c-post"><div class="verb">POST</div><div class="act">→ INSERT</div><code>Create a record</code></div>
    <div class="crud-item c-select"><div class="verb">SELECT</div><div class="act">→ DISPLAY</div><code>Read records</code></div>
    <div class="crud-item c-update"><div class="verb">UPDATE</div><div class="act">→ MODIFY</div><code>Edit a record</code></div>
    <div class="crud-item c-delete"><div class="verb">DELETE</div><div class="act">→ ARCHIVE</div><code>Kept, not erased</code></div>
  </div></section>

<section class="card"><h2>🕒 Recently Added</h2><ul class="recent">{recent_html}</ul></section>"""
    return layout("dashboard", "Dashboard", "Overview of your student records", body, toast)


def render_students(toast=None):
    with db() as conn:
        students = conn.execute("SELECT * FROM students ORDER BY name").fetchall()
    cards = "".join(
        f'<div class="person"><div class="avatar">{e(initials(s["name"]))}</div><b>{e(s["name"])}</b>'
        f'<small>{e(s["student_id"])}</small><span class="pill">{e(s["program"])}</span></div>'
        for s in students)
    if not cards:
        cards = '<div class="card empty" style="grid-column:1/-1"><span class="big">👨‍🎓</span>No students yet. <a href="/add" style="color:var(--blue);font-weight:600">Add the first one</a>.</div>'
    body = f'<div class="toolbar"><span class="count">{len(students)} active student{"s" if len(students) != 1 else ""}</span></div><div class="grid">{cards}</div>'
    return layout("students", "Students", "Student directory", body, toast)


def render_add(values=None, toast=None):
    v = values or {}
    body = f"""
<div class="form-wrap"><div class="card">
  <h2>Add Student Record</h2><p class="hint">Fill in the details below and save to the database.</p>
  <form method="POST" action="/students">
    <div class="field"><label for="sid">Student ID</label>
      <input id="sid" name="student_id" placeholder="e.g. 2026-003" value="{e(v.get('student_id', ''))}" maxlength="30" required></div>
    <div class="field"><label for="nm">Student Name</label>
      <input id="nm" name="name" placeholder="e.g. Ana Reyes" value="{e(v.get('name', ''))}" maxlength="120" required></div>
    <div class="field"><label for="pg">Program</label>
      <input id="pg" name="program" placeholder="e.g. BSIT" value="{e(v.get('program', ''))}" maxlength="80" required></div>
    <div class="form-actions"><button class="btn btn-primary btn-lg">💾 Save Student</button></div>
  </form></div></div>"""
    return layout("add", "Add Student", "Create a new student record", body, toast)


def render_records(q="", toast=None):
    with db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        if q:
            like = f"%{q}%"
            rows = conn.execute("""SELECT * FROM students WHERE student_id LIKE ? OR name LIKE ? OR program LIKE ?
                                   ORDER BY student_id""", (like, like, like)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM students ORDER BY student_id").fetchall()

    count = f"Showing {len(rows)} of {total} students" if q else f"{total} student{'s' if total != 1 else ''}"
    clear = '<a class="btn btn-ghost" href="/records">Clear</a>' if q else ""
    if rows:
        table = f"""<div class="table-wrap"><table><thead><tr><th>Student ID</th><th>Name</th><th>Program</th><th>Actions</th></tr></thead>
        <tbody>{"".join(student_row(s) for s in rows)}</tbody></table></div>"""
    else:
        msg = f'No records match “{e(q)}”.' if q else "No student records yet."
        table = f'<div class="empty"><span class="big">📭</span>{msg}</div>'

    body = f"""<div class="card">
  <div class="toolbar">
    <form class="search" method="GET" action="/records">
      <input type="search" name="q" value="{e(q)}" placeholder="Search by ID, name or program…" aria-label="Search">
      <button class="btn btn-primary">Search</button>{clear}</form>
    <span class="count">{count}</span>
    <a class="btn btn-success" href="/add">➕ Add Student</a>
  </div>{table}</div>"""
    return layout("records", "Student Records", "Data displayed from the database (SELECT)", body, toast)


def render_archived(toast=None):
    with db() as conn:
        rows = conn.execute("SELECT * FROM students_archive ORDER BY deleted_at DESC, archive_id DESC").fetchall()
    if rows:
        trs = "".join(f"""<tr>
          <td data-label="Student ID" class="sid">{e(a['student_id'])}</td>
          <td data-label="Name">{e(a['name'])}</td>
          <td data-label="Program"><span class="pill">{e(a['program'])}</span></td>
          <td data-label="Archived On">{e(a['deleted_at'])}</td>
          <td data-label="Actions"><form method="POST" action="/archive/{a['archive_id']}/restore">
            <button class="btn btn-success btn-sm">♻️ Restore</button></form></td></tr>""" for a in rows)
        table = f"""<div class="table-wrap"><table><thead><tr><th>Student ID</th><th>Name</th><th>Program</th><th>Archived On</th><th>Actions</th></tr></thead>
        <tbody>{trs}</tbody></table></div>"""
    else:
        table = '<div class="empty"><span class="big">🗃️</span>The archive is empty. Deleted records will appear here.</div>'
    body = f"""<div class="card"><div class="toolbar"><span class="count">{len(rows)} archived</span></div>{table}</div>"""
    return layout("archived", "Archived Records", "Deleted records are kept safely and can be restored", body, toast)


def render_edit(student, toast=None):
    body = f"""
<div class="form-wrap"><div class="card">
  <h2>Edit Student Record</h2><p class="hint">Update the details and save your changes.</p>
  <form method="POST" action="/students/{quote(student['student_id'], safe='')}/update">
    <div class="field"><label>Student ID</label><input value="{e(student['student_id'])}" disabled></div>
    <div class="field"><label for="nm">Student Name</label><input id="nm" name="name" value="{e(student['name'])}" maxlength="120" required></div>
    <div class="field"><label for="pg">Program</label><input id="pg" name="program" value="{e(student['program'])}" maxlength="80" required></div>
    <div class="form-actions"><a class="btn btn-ghost" href="/records">Cancel</a>
      <button class="btn btn-primary" style="flex:1">💾 Update Student</button></div>
  </form></div></div>"""
    return layout("records", "Edit Student", "Modify an existing record (UPDATE)", body, toast)


# ═════════════════════════ CONTROLLERS ═════════════════════════
# Each returns (ok: bool, message: str, detail: str)
def create_student(form):
    sid = form.get("student_id", "").strip()
    name = form.get("name", "").strip()
    program = form.get("program", "").strip()
    if not sid or not name or not program:
        return False, MSG_CREATE_ERROR, "All three fields are required."
    try:
        with db() as conn:
            conn.execute("INSERT INTO students (student_id, name, program) VALUES (?,?,?)", (sid, name, program))
        return True, MSG_CREATED, ""
    except sqlite3.IntegrityError:
        return False, MSG_CREATE_ERROR, f"Student ID {sid} already exists."


def update_student(sid, form):
    name = form.get("name", "").strip()
    program = form.get("program", "").strip()
    if not name or not program:
        return False, "Unable to update student record. Please check your input.", "Name and Program cannot be empty."
    with db() as conn:
        cur = conn.execute("UPDATE students SET name=?, program=? WHERE student_id=?", (name, program, sid))
    if cur.rowcount == 0:
        return False, "Student record not found.", ""
    return True, "Student record successfully updated!", ""


def delete_student(sid):
    """Soft delete: copy to archive table, then remove from live table (single transaction)."""
    with db() as conn:
        row = conn.execute("SELECT * FROM students WHERE student_id=?", (sid,)).fetchone()
        if not row:
            return False, "Student record not found.", ""
        conn.execute("INSERT INTO students_archive (student_id, name, program, created_at) VALUES (?,?,?,?)",
                     (row["student_id"], row["name"], row["program"], row["created_at"]))
        conn.execute("DELETE FROM students WHERE student_id=?", (sid,))
    return True, "Student record archived successfully!", f"{sid} can be restored from Archived Records."


def restore_student(archive_id):
    with db() as conn:
        a = conn.execute("SELECT * FROM students_archive WHERE archive_id=?", (archive_id,)).fetchone()
        if not a:
            return False, "Archived record not found.", ""
        try:
            conn.execute("INSERT INTO students (student_id, name, program, created_at) VALUES (?,?,?,?)",
                         (a["student_id"], a["name"], a["program"], a["created_at"]))
        except sqlite3.IntegrityError:
            return False, "Unable to restore student record.", f"Student ID {a['student_id']} already exists."
        conn.execute("DELETE FROM students_archive WHERE archive_id=?", (archive_id,))
    return True, "Student record restored successfully!", ""


# ═════════════════════════ ROUTER ═════════════════════════
class Handler(BaseHTTPRequestHandler):
    def _send(self, code, content):
        data = content.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _redirect(self, path, result):
        """Post/Redirect/Get so refreshing never re-submits the form."""
        ok, msg, detail = result
        qs = urlencode({"kind": "success" if ok else "error", "msg": msg, "detail": detail})
        self.send_response(303)
        self.send_header("Location", f"{path}?{qs}")
        self.end_headers()

    def log_message(self, fmt, *args):
        print(f"{self.command} {self.path.split('?')[0]} → {args[1] if len(args) > 1 else ''}")

    def do_GET(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        toast = None
        if q.get("msg"):
            toast = (q.get("kind", ["success"])[0], q["msg"][0], q.get("detail", [""])[0])

        if url.path == "/":
            return self._send(200, render_dashboard(toast))
        if url.path == "/students":
            return self._send(200, render_students(toast))
        if url.path == "/add":
            return self._send(200, render_add(toast=toast))
        if url.path == "/records":
            return self._send(200, render_records(q.get("q", [""])[0].strip(), toast))
        if url.path == "/archived":
            return self._send(200, render_archived(toast))

        m = re.fullmatch(r"/students/([^/]+)/edit", url.path)
        if m:
            with db() as conn:
                s = conn.execute("SELECT * FROM students WHERE student_id=?", (unquote(m.group(1)),)).fetchone()
            if not s:
                return self._redirect("/records", (False, "Student record not found.", ""))
            return self._send(200, render_edit(s, toast))

        self._send(404, layout("dashboard", "Page not found", "404",
                               '<div class="card empty"><span class="big">🧭</span>That page does not exist. '
                               '<a href="/" style="color:var(--blue);font-weight:600">Back to Dashboard</a></div>'))

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        form = {k: v[0] for k, v in parse_qs(self.rfile.read(length).decode("utf-8")).items()}
        path = urlparse(self.path).path

        if path == "/students":
            result = create_student(form)
            if result[0]:
                return self._redirect("/records", result)
            # on error, re-render the form with the user's input kept
            return self._send(400, render_add(form, ("error", result[1], result[2])))

        m = re.fullmatch(r"/students/([^/]+)/update", path)
        if m:
            sid = unquote(m.group(1))
            result = update_student(sid, form)
            if result[0]:
                return self._redirect("/records", result)
            return self._redirect(f"/students/{quote(sid, safe='')}/edit", result)

        m = re.fullmatch(r"/students/([^/]+)/delete", path)
        if m:
            return self._redirect("/records", delete_student(unquote(m.group(1))))

        m = re.fullmatch(r"/archive/(\d+)/restore", path)
        if m:
            return self._redirect("/archived", restore_student(int(m.group(1))))

        self._send(404, layout("dashboard", "Page not found", "404", '<div class="card empty">Not found.</div>'))


if __name__ == "__main__":
    init_db()
    print(f"Running at http://localhost:{PORT}  (Ctrl+C to stop)")
    HTTPServer(("", PORT), Handler).serve_forever()
