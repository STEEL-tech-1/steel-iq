# NZD Structural Studio Planner — Backend

## What's included

| File | Purpose |
|---|---|
| `server.py` | Python backend: HTTP server + SQLite REST API |
| `index.html` | Frontend UI (served by server.py) |
| `nzd_planner.db` | SQLite database (auto-created on first run) |

---

## Requirements

- **Python 3.7+** — no pip installs needed (uses only stdlib)
- Any modern web browser

---

## How to run

```bash
# 1. Put server.py and index.html in the same folder
# 2. Open a terminal in that folder
python3 server.py

# Windows:
python server.py
```

The server will:
1. Create `nzd_planner.db` on first run with all seed data
2. Start listening on **http://localhost:8000**
3. Open your browser automatically

---

## REST API

All endpoints return JSON. Base URL: `http://localhost:8000`

### Bulk load (used by frontend on startup)
```
GET  /api/all           — all data in one request
```

### Jobs
```
GET    /api/jobs
POST   /api/jobs        — body: { name, stage, team, person, priority, start, end, rev, framecad, detailer, permit, rfy, gfc, boq, status, remarks }
PUT    /api/jobs/:id    — same body
DELETE /api/jobs/:id
```

### Quotes
```
GET    /api/quotes
POST   /api/quotes      — body: { name, rfq, team, person, priority, start, end, ppt, fc, est, status, remarks }
PUT    /api/quotes/:id
DELETE /api/quotes/:id
```

### Team Members
```
GET    /api/members
POST   /api/members     — body: { id, name, role, dept, lim, used, color, team }
PUT    /api/members/:id — same body
DELETE /api/members/:id
```

### Teams
```
GET    /api/teams
POST   /api/teams       — body: { key, label, color, spoc, lead, focus, members[] }
PUT    /api/teams/:key  — same body
DELETE /api/teams/:key
```

### Change Orders
```
GET    /api/change_orders
POST   /api/change_orders  — body: { name, team, status }
PUT    /api/change_orders/:id
DELETE /api/change_orders/:id
```

### Mail Tasks
```
GET    /api/mail_tasks
POST   /api/mail_tasks  — body: { name, stage, permit, remarks, struct, assigned[] }
PUT    /api/mail_tasks/:id
DELETE /api/mail_tasks/:id
```

### Completed
```
GET    /api/completed
POST   /api/completed   — body: { id, name, stage, team }
DELETE /api/completed/:id
```

---

## Database

SQLite file `nzd_planner.db` is created automatically. To reset to seed data:

```bash
rm nzd_planner.db
python3 server.py
```

---

## Multi-user / Network access

To let others on the same network open the app, find your local IP and share it:

```bash
# The server already binds to 0.0.0.0 (all interfaces)
# Find your IP:
#   Mac/Linux: ifconfig | grep "inet "
#   Windows:   ipconfig

# Others open:  http://YOUR_LOCAL_IP:8000
```

For production use, put Nginx or Caddy in front of server.py.
