#!/usr/bin/env python3
"""
NZD Structural Studio Planner — Backend Server
Pure stdlib: sqlite3 + http.server + json  (no pip installs needed)
Usage:  python3 server.py
Opens:  http://localhost:8000
"""

import sqlite3, json, os, sys, threading, webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

DB_PATH  = Path(__file__).parent / "nzd_planner.db"
HTML_PATH = Path(__file__).parent / "index.html"
PORT = 8000

# ═══════════════════════════════════════════════════════════
#  DATABASE SETUP
# ═══════════════════════════════════════════════════════════

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS teams (
            key       TEXT PRIMARY KEY,
            label     TEXT NOT NULL,
            color     TEXT DEFAULT '#4aa3f5',
            spoc      TEXT DEFAULT '',
            lead      TEXT DEFAULT '',
            focus     TEXT DEFAULT 'JOB'
        );

        CREATE TABLE IF NOT EXISTS team_members_map (
            team_key    TEXT REFERENCES teams(key) ON DELETE CASCADE,
            member_name TEXT,
            PRIMARY KEY (team_key, member_name)
        );

        CREATE TABLE IF NOT EXISTS members (
            id      TEXT PRIMARY KEY,
            name    TEXT NOT NULL,
            role    TEXT DEFAULT '',
            dept    TEXT DEFAULT 'Structural Design',
            lim     INTEGER DEFAULT 5,
            used    INTEGER DEFAULT 0,
            color   TEXT DEFAULT '#4aa3f5'
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            num       TEXT DEFAULT '',
            name      TEXT NOT NULL,
            stage     TEXT DEFAULT 'JOB',
            team      TEXT DEFAULT '',
            person    TEXT DEFAULT '',
            priority  TEXT DEFAULT '',
            start     TEXT DEFAULT '',
            end       TEXT DEFAULT '',
            rev       TEXT DEFAULT '',
            framecad  INTEGER DEFAULT 0,
            detailer  INTEGER DEFAULT 0,
            permit    INTEGER DEFAULT 0,
            rfy       INTEGER DEFAULT 0,
            gfc       INTEGER DEFAULT 0,
            boq       INTEGER DEFAULT 0,
            status    TEXT DEFAULT '',
            remarks   TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS quotes (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            rfq       TEXT DEFAULT '',
            name      TEXT NOT NULL,
            team      TEXT DEFAULT '',
            person    TEXT DEFAULT '',
            priority  TEXT DEFAULT '',
            start     TEXT DEFAULT '',
            end       TEXT DEFAULT '',
            ppt       INTEGER DEFAULT 0,
            fc        INTEGER DEFAULT 0,
            est       INTEGER DEFAULT 0,
            status    TEXT DEFAULT '',
            remarks   TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS change_orders (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            num       TEXT DEFAULT '',
            name      TEXT NOT NULL,
            team      TEXT DEFAULT '',
            status    TEXT DEFAULT 'NOT STARTED'
        );

        CREATE TABLE IF NOT EXISTS mail_tasks (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT NOT NULL,
            stage     TEXT DEFAULT 'Production',
            permit    INTEGER DEFAULT 0,
            remarks   TEXT DEFAULT '',
            struct    TEXT DEFAULT '',
            assigned  TEXT DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS completed (
            id        TEXT PRIMARY KEY,
            name      TEXT NOT NULL,
            stage     TEXT DEFAULT '',
            team      TEXT DEFAULT ''
        );
        """)
        seed_if_empty(db)
        db.commit()

def seed_if_empty(db):
    if db.execute("SELECT COUNT(*) FROM teams").fetchone()[0] > 0:
        return   # already seeded

    # Teams
    teams = [
        ('N1','N1 – Quote','#4aa3f5','Swetha Makkena','Sai Teja','QUOTE'),
        ('N2','N2 – Job',  '#f0a000','Yogeshwar Kulkarni','Amit','JOB'),
        ('N3','N3 – Job',  '#a78bfa','Ashita Alex','Sanath','JOB'),
    ]
    db.executemany("INSERT INTO teams VALUES(?,?,?,?,?,?)", teams)

    team_mem = [
        ('N1','Manjunath B'),('N1','Sai Teja'),('N1','Siddhesh J'),('N1','Chandrakala'),
        ('N2','Manjunath J'),('N2','Amit'),('N2','Praveen'),('N2','Naveen'),
        ('N3','Shyam'),('N3','Sanath Poojary'),('N3','Basavraj B'),('N3','Indrajeet Patil'),
    ]
    db.executemany("INSERT INTO team_members_map VALUES(?,?)", team_mem)

    # Members
    members = [
        ('MMB','Manjunath B','Studio Head','Structural Design',5,9,'#f0a000'),
        ('GST','Sai Teja','Structural Engineer','Structural Design',5,3,'#4aa3f5'),
        ('SP', 'Sanath Poojary','Structural Engineer','Structural Design',5,0,'#a78bfa'),
        ('AD', 'Amit Devar','Structural Engineer','Structural Design',5,0,'#2ec27e'),
        ('IP', 'Indrajeet Patil','FrameCAD Engineer','FrameCAD',2,1,'#e84040'),
        ('NC', 'Naveen Chary','FrameCAD Engineer','FrameCAD',2,1,'#f857a6'),
        ('SA', 'Shyam Ambhore','Sr FrameCAD Designer','FrameCAD',2,0,'#38d9f5'),
        ('MJ', 'Manjunath J','Sr FrameCAD Design Eng','FrameCAD',2,1,'#a8eb12'),
        ('CM', 'Chandrakala','FrameCAD Design Eng','FrameCAD',2,0,'#ff9f43'),
        ('BSB','Basavraj B','Detailing Engineer','Detailing',3,3,'#e84040'),
        ('SJ', 'Siddhesh J','Detailing Engineer','Detailing',3,0,'#6c63ff'),
        ('DP', 'Dasari Praveen','Detailing Engineer','Detailing',3,0,'#4aa3f5'),
    ]
    db.executemany("INSERT INTO members VALUES(?,?,?,?,?,?,?)", members)

    # Jobs
    jobs = [
        ('PN-26-001','2717 KENTUCKY DERBY, BARTONVILLE, TX (Ramki)','PRODUCTION','N2','Amit','High','2026-01-01','2026-01-05','R5',80,50,100,90,0,0,'ON TRACK',''),
        ('','GARVIN RANCH BOSQUE COUNTY TEXAS','PRODUCTION','N2','Amit','High','2026-01-05','2026-01-10','',0,0,0,0,0,0,'','As Built awaiting + 8" Stud section discussion'),
        ('','PAI RESIDENCE (Main Building+Pavilion)','PRODUCTION','N3','Sanath','Medium','2026-01-05','2026-01-10','',0,0,0,0,0,0,'ON TRACK','Production Priority (contract Pending)'),
        ('','Wylie_COMMERCIAL BLOCK','JOB','N2','Amit','','','','',0,0,0,0,0,0,'NOT STARTED','Dwg sent to RCS'),
        ('','S-25-134-609 Victoria Falls, Anna, TX','JOB','N3','Sanath','High','','','',0,0,0,0,0,0,'DELAYED','DAN and Leo Working - Present Status'),
        ('','1321 STACY ROAD FAIRVIEW TX_ANDY THIND','JOB','N2','Amit','','','','',0,0,0,0,0,0,'DELAYED','Change Orders to be finalized with ANDY'),
        ('','415 E ALTADENA DR ALTADENA CA 91001','JOB','N2','Amit','','','','',0,0,100,0,0,0,'','Production Priority'),
        ('','429 E ALTADENA DR ALTADENA CA 91001','JOB','N2','Amit','','','','',0,0,100,0,0,0,'','Production Priority'),
        ('','2076 Glen Ave','JOB','N2','Amit','','','','',0,0,100,0,0,0,'','Production Priority'),
        ('','2317 Maiden Lane','JOB','N2','Amit','','','','',0,0,0,0,0,0,'','CAD drawing sent to client, final quote needed'),
        ('','S-25-063-Anvaya Capital LLC_Frisco_TX','JOB','N2','Amit','','','','',0,0,0,0,0,0,'','Kevin handling, LGSS production clarity needed'),
        ('','S-25-067-3980 STARLING DRIVE FRISCO TX','PRODUCTION','N2','Amit','','','','',0,50,10,30,0,0,'','6" Production rev.20 walls sent to Dan'),
    ]
    db.executemany("""INSERT INTO jobs(num,name,stage,team,person,priority,start,end,rev,
        framecad,detailer,permit,rfy,gfc,boq,status,remarks) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", jobs)

    # Quotes
    quotes = [
        ('','S-25-152-1311 Oak Drive, Flower Mound','N1','Sai Teja','','','',0,0,0,'','High pitch truss 8/12 slope - Need to revise roof slope'),
        ('','S-25-153-Sobha Realty Texas Villa','N1','Sai Teja','','','',0,0,0,'','Need to send Quote and PPT'),
        ('','S-25-154-TELFAIR FOOD HALL, SugarLand TX','N1','Sai Teja','','','',0,0,0,'','SJ is working'),
        ('','S-25-151-Martin_TX','N1','Sai Teja','','','',0,0,0,'','Need to revise roof slope (High Pitch)'),
        ('','S-25-150-MULTI-TENANT SHELL BUILDING LEWISVILLE TX','N1','Sai Teja','','','',0,0,0,'','LEO and DAN need to work on this'),
        ('','S-25-149-Chandler House','N1','Sai Teja','','','',0,0,0,'','High Pitch Truss - Hold'),
        ('','S-25-148-Walden Pond Amenity Center TX','N1','Sai Teja','','','',0,0,0,'',''),
        ('','S-25-147-Blue Horizon Residence Lago Vista TX','N1','Sai Teja','','','',0,0,0,'','Released'),
        ('','S-25-146-Sikh Temple Turlock','N1','Sai Teja','','','',0,0,0,'','67 ft long truss design R&D - Working'),
        ('','S-25-145-3534 Fairmount','N1','Sai Teja','','','',0,0,0,'','1 unit Quote released'),
        ('','S-25-144-Yellow Door Storage Celina TX','N2','Amit','','','',0,0,0,'','Working'),
        ('','S-25-143-FATE RETAIL CENTER FATE TEXAS','N1','Sai Teja','','','',0,0,0,'','Previous Structural steel required'),
        ('','S-25-142-21500 Calle Del Barco','N1','Sai Teja','','','',0,0,0,'','Released'),
        ('','S-25-141-WILLOW CREEK RETAIL OFFICE','N1','Sai Teja','','','',0,0,0,'','Rough estimate released'),
        ('','S-25-140-LILYBROOK AT LEGACY HILLS AMENITY CENTER','N1','Sai Teja','','','',0,0,0,'',''),
        ('','S-25-139-Celina Square TX','N2','Amit','','','',0,0,0,'','CFS quote released, value engineering from Kevin needed'),
        ('','S-25-155-419 W 10th Street Dallas','N1','Sai Teja','','','',0,0,0,'','Leo reviewed'),
        ('','S-25-156-601 Pilgrim Lane SE Palm Bay FL','N1','Sai Teja','','','',0,0,0,'','Queries sent'),
        ('','S-25-157-Plaza in Arlington','N3','Sanath','','','',0,0,0,'',''),
    ]
    db.executemany("""INSERT INTO quotes(rfq,name,team,person,priority,start,end,ppt,fc,est,status,remarks)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", quotes)

    # Mail tasks
    mail = [
        ('Ramki Project','Production',100,'Working for Production','Ceiling Added in Team is working on QA/QC','["NC","GST"]'),
        ('GARVIN RANCH BOSQUE COUNTY TEXAS','JOB',0,'As Built awaiting + 8" Stud section discussion','Team is working on Design Stage','["SA","AD"]'),
        ('609 Victoria Falls, Anna TX','JOB',0,'DAN and Leo Working - Present Status','','[]'),
        ('PAI RESIDENCE (Main Building+Pavilion)','JOB',0,'Production Priority (contract Pending)','','[]'),
        ('429/415 E ALTADENA DR ALTADENA CA','JOB',100,'Production Priority - Arch Signoff','Team is working on QA/QC','["GST","IP","CM"]'),
        ('2076 Glen Ave','JOB',100,'Production Priority - Arch Signoff','Team is working on QA/QC','["GST","SJ","CM"]'),
        ('3980 STARLING DRIVE FRISCO TX','Production',10,'6" Production rev.20 walls sent to Dan','6" - ALL walls sent to Leo/Dan','["MJ"]'),
        ('1321 STACY ROAD FAIRVIEW TX_ANDY THIND','Production',100,'Change Orders to be finalized with ANDY','','[]'),
        ('2317 Maiden Lane','JOB',0,'CAD drawing sent to client, final Quote required','','[]'),
    ]
    db.executemany("INSERT INTO mail_tasks(name,stage,permit,remarks,struct,assigned) VALUES(?,?,?,?,?,?)", mail)

    # Completed
    done = [
        ('PN-25-001','S-25-005-1321 STACY ROAD FAIRVIEW TX_ANDY THIND','PRODUCTION','N2'),
        ('PN-25-002','S-25-019-Brighton Abbey Storage Building, Aubrey TX','JOB','N2'),
        ('PN-25-003','S-25-018-10000 INWOOD ROAD 5517 TR 25 DALLAS TX','JOB','N2'),
        ('PN-25-004','S-25-048-1812 RIVIERA Southlake TX','JOB','N2'),
        ('PN-25-005','S-25-055-RAMSEY RESIDENCE COLLEYVILLE TEXAS','JOB','N2'),
        ('PN-25-006','S-25-131-Naval Facilities MAIN GATE GUARD SHACK','JOB','N3'),
    ]
    db.executemany("INSERT INTO completed VALUES(?,?,?,?)", done)


# ═══════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════

def rows_to_list(cursor):
    return [dict(r) for r in cursor.fetchall()]

def json_resp(handler, data, status=200):
    body = json.dumps(data, default=str).encode()
    handler.send_response(status)
    handler.send_header("Content-Type","application/json")
    handler.send_header("Content-Length", len(body))
    handler.send_header("Access-Control-Allow-Origin","*")
    handler.end_headers()
    handler.wfile.write(body)

def read_body(handler):
    length = int(handler.headers.get("Content-Length",0))
    return json.loads(handler.rfile.read(length)) if length else {}

def get_teams_full(db):
    teams = rows_to_list(db.execute("SELECT * FROM teams"))
    for t in teams:
        rows = db.execute("SELECT member_name FROM team_members_map WHERE team_key=?", (t['key'],)).fetchall()
        t['members'] = [r[0] for r in rows]
    return teams

# ═══════════════════════════════════════════════════════════
#  REQUEST HANDLER
# ═══════════════════════════════════════════════════════════

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"  {self.address_string()} {fmt%args}")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Methods","GET,POST,PUT,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers","Content-Type")
        self.end_headers()

    def do_GET(self):
        p = urlparse(self.path).path.rstrip("/")

        # Serve the frontend HTML
        if p in ("", "/", "/index.html"):
            body = HTML_PATH.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type","text/html; charset=utf-8")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
            return

        with get_db() as db:
            if p == "/api/teams":
                json_resp(self, get_teams_full(db))
            elif p == "/api/members":
                json_resp(self, rows_to_list(db.execute("SELECT * FROM members")))
            elif p == "/api/jobs":
                json_resp(self, rows_to_list(db.execute("SELECT * FROM jobs ORDER BY id")))
            elif p == "/api/quotes":
                json_resp(self, rows_to_list(db.execute("SELECT * FROM quotes ORDER BY id")))
            elif p == "/api/change_orders":
                json_resp(self, rows_to_list(db.execute("SELECT * FROM change_orders ORDER BY id")))
            elif p == "/api/mail_tasks":
                rows = rows_to_list(db.execute("SELECT * FROM mail_tasks ORDER BY id"))
                for r in rows:
                    try: r['assigned'] = json.loads(r['assigned'])
                    except: r['assigned'] = []
                json_resp(self, rows)
            elif p == "/api/completed":
                json_resp(self, rows_to_list(db.execute("SELECT * FROM completed")))
            elif p == "/api/all":
                rows = rows_to_list(db.execute("SELECT * FROM mail_tasks"))
                for r in rows:
                    try: r['assigned'] = json.loads(r['assigned'])
                    except: r['assigned'] = []
                json_resp(self, {
                    "teams":    get_teams_full(db),
                    "members":  rows_to_list(db.execute("SELECT * FROM members")),
                    "jobs":     rows_to_list(db.execute("SELECT * FROM jobs ORDER BY id")),
                    "quotes":   rows_to_list(db.execute("SELECT * FROM quotes ORDER BY id")),
                    "change_orders": rows_to_list(db.execute("SELECT * FROM change_orders ORDER BY id")),
                    "mail_tasks": rows,
                    "completed": rows_to_list(db.execute("SELECT * FROM completed")),
                })
            else:
                json_resp(self, {"error":"not found"}, 404)

    def do_POST(self):
        p = urlparse(self.path).path.rstrip("/")
        body = read_body(self)
        with get_db() as db:
            # ── JOBS ──
            if p == "/api/jobs":
                cur = db.execute("""INSERT INTO jobs(num,name,stage,team,person,priority,start,end,rev,
                    framecad,detailer,permit,rfy,gfc,boq,status,remarks) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (body.get('num',''), body['name'], body.get('stage','JOB'), body.get('team',''),
                     body.get('person',''), body.get('priority',''), body.get('start',''), body.get('end',''),
                     body.get('rev',''), body.get('framecad',0), body.get('detailer',0), body.get('permit',0),
                     body.get('rfy',0), body.get('gfc',0), body.get('boq',0),
                     body.get('status',''), body.get('remarks','')))
                db.commit()
                json_resp(self, {"id": cur.lastrowid}, 201)
            # ── QUOTES ──
            elif p == "/api/quotes":
                cur = db.execute("""INSERT INTO quotes(rfq,name,team,person,priority,start,end,ppt,fc,est,status,remarks)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (body.get('rfq',''), body['name'], body.get('team',''), body.get('person',''),
                     body.get('priority',''), body.get('start',''), body.get('end',''),
                     body.get('ppt',0), body.get('fc',0), body.get('est',0),
                     body.get('status',''), body.get('remarks','')))
                db.commit()
                json_resp(self, {"id": cur.lastrowid}, 201)
            # ── CHANGE ORDERS ──
            elif p == "/api/change_orders":
                cur = db.execute("INSERT INTO change_orders(num,name,team,status) VALUES(?,?,?,?)",
                    (body.get('num',''), body['name'], body.get('team','N2'), body.get('status','NOT STARTED')))
                db.commit()
                json_resp(self, {"id": cur.lastrowid}, 201)
            # ── MAIL TASKS ──
            elif p == "/api/mail_tasks":
                cur = db.execute("INSERT INTO mail_tasks(name,stage,permit,remarks,struct,assigned) VALUES(?,?,?,?,?,?)",
                    (body['name'], body.get('stage','Production'), body.get('permit',0),
                     body.get('remarks',''), body.get('struct',''), json.dumps(body.get('assigned',[]))))
                db.commit()
                json_resp(self, {"id": cur.lastrowid}, 201)
            # ── MEMBERS ──
            elif p == "/api/members":
                db.execute("INSERT INTO members(id,name,role,dept,lim,used,color) VALUES(?,?,?,?,?,?,?)",
                    (body['id'], body['name'], body.get('role',''), body.get('dept','Structural Design'),
                     body.get('lim', body.get('limit',5)), body.get('used',0), body.get('color','#4aa3f5')))
                if body.get('team'):
                    db.execute("INSERT OR IGNORE INTO team_members_map VALUES(?,?)",(body['team'], body['name']))
                db.commit()
                json_resp(self, {"id": body['id']}, 201)
            # ── COMPLETED ──
            elif p == "/api/completed":
                db.execute("INSERT OR REPLACE INTO completed VALUES(?,?,?,?)",
                    (body['id'], body['name'], body.get('stage',''), body.get('team','')))
                db.commit()
                json_resp(self, {"ok": True}, 201)
            # ── TEAMS ──
            elif p == "/api/teams":
                db.execute("INSERT INTO teams VALUES(?,?,?,?,?,?)",
                    (body['key'], body['label'], body.get('color','#4aa3f5'),
                     body.get('spoc',''), body.get('lead',''), body.get('focus','JOB')))
                for m in body.get('members',[]):
                    db.execute("INSERT OR IGNORE INTO team_members_map VALUES(?,?)",(body['key'],m))
                db.commit()
                json_resp(self, {"key": body['key']}, 201)
            else:
                json_resp(self, {"error":"not found"}, 404)

    def do_PUT(self):
        p = urlparse(self.path).path.rstrip("/")
        body = read_body(self)
        parts = p.split("/")   # ['','api','resource','id']
        with get_db() as db:
            if len(parts) == 4 and parts[1] == "api":
                res, rid = parts[2], parts[3]
                if res == "jobs":
                    db.execute("""UPDATE jobs SET num=?,name=?,stage=?,team=?,person=?,priority=?,start=?,end=?,
                        rev=?,framecad=?,detailer=?,permit=?,rfy=?,gfc=?,boq=?,status=?,remarks=? WHERE id=?""",
                        (body.get('num',''), body['name'], body.get('stage','JOB'), body.get('team',''),
                         body.get('person',''), body.get('priority',''), body.get('start',''), body.get('end',''),
                         body.get('rev',''), body.get('framecad',0), body.get('detailer',0), body.get('permit',0),
                         body.get('rfy',0), body.get('gfc',0), body.get('boq',0),
                         body.get('status',''), body.get('remarks',''), rid))
                    db.commit(); json_resp(self, {"ok":True})
                elif res == "quotes":
                    db.execute("""UPDATE quotes SET rfq=?,name=?,team=?,person=?,priority=?,start=?,end=?,
                        ppt=?,fc=?,est=?,status=?,remarks=? WHERE id=?""",
                        (body.get('rfq',''), body['name'], body.get('team',''), body.get('person',''),
                         body.get('priority',''), body.get('start',''), body.get('end',''),
                         body.get('ppt',0), body.get('fc',0), body.get('est',0),
                         body.get('status',''), body.get('remarks',''), rid))
                    db.commit(); json_resp(self, {"ok":True})
                elif res == "change_orders":
                    db.execute("UPDATE change_orders SET num=?,name=?,team=?,status=? WHERE id=?",
                        (body.get('num',''), body['name'], body.get('team',''), body.get('status','NOT STARTED'), rid))
                    db.commit(); json_resp(self, {"ok":True})
                elif res == "mail_tasks":
                    db.execute("UPDATE mail_tasks SET name=?,stage=?,permit=?,remarks=?,struct=?,assigned=? WHERE id=?",
                        (body['name'], body.get('stage','Production'), body.get('permit',0),
                         body.get('remarks',''), body.get('struct',''), json.dumps(body.get('assigned',[])), rid))
                    db.commit(); json_resp(self, {"ok":True})
                elif res == "members":
                    db.execute("UPDATE members SET name=?,role=?,dept=?,lim=?,used=?,color=? WHERE id=?",
                        (body['name'], body.get('role',''), body.get('dept','Structural Design'),
                         body.get('lim', body.get('limit',5)), body.get('used',0), body.get('color','#4aa3f5'), rid))
                    # Update team membership
                    db.execute("DELETE FROM team_members_map WHERE member_name=?", (body['name'],))
                    if body.get('team'):
                        db.execute("INSERT OR IGNORE INTO team_members_map VALUES(?,?)",(body['team'], body['name']))
                    db.commit(); json_resp(self, {"ok":True})
                elif res == "teams":
                    db.execute("UPDATE teams SET label=?,color=?,spoc=?,lead=?,focus=? WHERE key=?",
                        (body['label'], body.get('color','#4aa3f5'), body.get('spoc',''),
                         body.get('lead',''), body.get('focus','JOB'), rid))
                    db.execute("DELETE FROM team_members_map WHERE team_key=?", (rid,))
                    for m in body.get('members',[]):
                        db.execute("INSERT OR IGNORE INTO team_members_map VALUES(?,?)",(rid, m))
                    db.commit(); json_resp(self, {"ok":True})
                else:
                    json_resp(self, {"error":"not found"}, 404)
            else:
                json_resp(self, {"error":"bad path"}, 400)

    def do_DELETE(self):
        p = urlparse(self.path).path.rstrip("/")
        parts = p.split("/")
        with get_db() as db:
            if len(parts) == 4 and parts[1] == "api":
                res, rid = parts[2], parts[3]
                table_map = {
                    "jobs":"jobs", "quotes":"quotes",
                    "change_orders":"change_orders", "mail_tasks":"mail_tasks",
                    "completed":"completed"
                }
                if res in table_map:
                    pk = "id" if res != "completed" else "id"
                    db.execute(f"DELETE FROM {table_map[res]} WHERE {pk}=?", (rid,))
                    db.commit(); json_resp(self, {"ok":True})
                elif res == "members":
                    row = db.execute("SELECT name FROM members WHERE id=?", (rid,)).fetchone()
                    if row:
                        db.execute("DELETE FROM team_members_map WHERE member_name=?", (row['name'],))
                    db.execute("DELETE FROM members WHERE id=?", (rid,))
                    db.commit(); json_resp(self, {"ok":True})
                elif res == "teams":
                    db.execute("DELETE FROM teams WHERE key=?", (rid,))
                    db.commit(); json_resp(self, {"ok":True})
                else:
                    json_resp(self, {"error":"not found"}, 404)
            else:
                json_resp(self, {"error":"bad path"}, 400)


# ═══════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    if not HTML_PATH.exists():
        print(f"ERROR: index.html not found at {HTML_PATH}")
        print("Place the NZD Planner HTML file next to server.py and rename it to index.html")
        sys.exit(1)

    print("Initialising database…")
    init_db()
    print(f"Database ready: {DB_PATH}")

    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"\n{'═'*50}")
    print(f"  NZD Studio Planner — Backend Server")
    print(f"  http://localhost:{PORT}")
    print(f"  Press Ctrl+C to stop")
    print(f"{'═'*50}\n")

    def open_browser():
        import time; time.sleep(0.8)
        webbrowser.open(f"http://localhost:{PORT}")
    threading.Thread(target=open_browser, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
