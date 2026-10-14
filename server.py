"""Local evidence-first tax workpaper demo. Bind only to loopback; demo roles are not identity auth."""
from __future__ import annotations

import copy
import base64
import hashlib
import hmac
import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
PACKET_PATH = ROOT / "okafor_lindqvist_2025_packet.json"
REDACTED_PACKET_PATH = ROOT / ".demo-data" / "packet.json"
DB_PATH = Path(os.environ.get("WORKPAPER_DB", ROOT.parent / "work" / "workpaper-data.sqlite"))
ISSUES = [
    {"id":"meridian-detail","title":"Corrected 1099-B page 32 lot is missing from extracted return detail","kind":"confirmed-source-omission","severity":"high","status":"open","description":"Confirmed source omission: D31 page 32 prints M18, a short-term noncovered lot with $250 proceeds and $310 basis. It has no extracted-value IDs and no M18 F8949 line in v3. Adding it reconciles D31 summary proceeds ($71,965) to detail ($71,715 + $250); the statement summary itself is not inconsistent. The omitted lot is a $60 loss. Using v3 stcg rates, estimated tax change if included is −$20.88 federal and −$2.04 California (about $22.92 combined); small-change estimate only, and California sourcing should be reviewed. A return engine recomputation is needed.","refs":["D30","D31","D31#page10","D31#page32","ev-0703","F8949.D.M17","SchD.7","SchD.16","F1040.7","SchCA540NR.7.D","SchCA540NR.7.E"],"affected":["F8949 · missing M18","SchD.7","SchD.16","F1040.7","SchCA540NR.7.D","SchCA540NR.7.E"]},
    {"id":"sales-answer","title":"Organizer answer conflicts with disposal records","kind":"completeness","severity":"high","status":"open","description":"Questionnaire qa-14 reports no investments sold; supplied diagnostic reports 282 brokerage sales and 12 digital asset dispositions. Confirm the client's understanding and completeness; the conflict alone does not establish a tax error.","refs":["qa-14","D30","D34","D35"],"affected":["F8949","SchD"]},
    {"id":"crypto-c6","title":"Coinhaven C6 basis lacks primary support","kind":"basis","severity":"high","status":"open","description":"The engine used zero basis for C6. Later msg-07 reports a $3,050 2021 purchase but only a bank statement line is available. Potential basis error; request corroboration before accepting an adjustment.","refs":["ev-0879","ev-0881","ev-0882","ev-0918","ev-0919","msg-07","D35"],"affected":["F8949","SchD.16","F1040.7"]},
    {"id":"scorp-basis","title":"Late 2023 K-1 changed S corporation basis","kind":"basis","severity":"high","status":"open","description":"The late D40 K-1 changed F7203 basis from $8,200 (v2) to $2,300 (v3), increasing excess distribution from $15,315 to $21,215. The missing 2023 basis history remains a separate open judgment.","refs":["D39","D40","F7203.1","F7203.5","F7203.excess","F8949.F.SCORP"],"affected":["F7203.1","F7203.excess","F8949.F.SCORP","SchD.10","F1040.7"]},
    {"id":"contractor-1099","title":"Contractor information returns not filed","kind":"compliance","severity":"high","status":"open","description":"Engine diagnostic says two contractors received $600 or more and Forms 1099-NEC were not filed. Client asked what to do; document follow-up and disposition.","refs":["D27","call-01","SchC.I","SchC.J"],"affected":["SchC.I","SchC.J"]},
    {"id":"ca-amt","title":"California AMT not computed","kind":"calculation-gap","severity":"high","status":"open","description":"The packet explicitly says California AMT is not computed; ISO exercise has a California-source allocation. This is an unresolved calculation scope gap, not an independently quantified tax error.","refs":["D12","F6251.2i"],"affected":["F6251.2i","F540NR"]},
    {"id":"fbar-scope","title":"FBAR is outside the engagement scope","kind":"completeness","severity":"medium","status":"open","description":"Engine diagnostic identifies a foreign account maximum over $10,000 and a separate FinCEN Form 114 filing. Record the responsible filer and obtain confirmation; not part of this income-tax return.","refs":["D36","F8938.1.max"],"affected":["F8938.1.max"]},
    {"id":"donation-receipt","title":"Handwritten donation read was low confidence","kind":"evidence","severity":"medium","status":"resolved","description":"ev-1049 was initially read at 0.41 confidence. msg-08 later reports phone confirmation of $1,500 and bank check #2207. Link that confirmation and bank evidence to the final documented decision.","refs":["ev-1049","msg-08","D64"],"affected":["SchA.11","F8283"]},
    {"id":"efile-reject","title":"Federal e-file rejection followed by corrected acceptance","kind":"filing","severity":"high","status":"resolved","description":"Initial federal e-file was rejected for Theo's name/TIN mismatch. D71 arrived after the rejection; federal and California were subsequently accepted. Preserve the rejection, correction, and acceptance chain.","refs":["D71","agency:/efile","tl-21","tl-22","tl-23","tl-24"],"affected":["F1040 dependent details"]},
    {"id":"exam-2028","title":"IRS Letter 566 examination response due February 19, 2028","kind":"notice","severity":"high","status":"open","description":"Examination requests noncash contribution acknowledgments/valuation and Schedule C gross-receipts reconciliation to Forms 1099-NEC ($142,000) and 1099-K ($12,400). Create a self-contained response record linked to filed evidence.","refs":["D72","N-2025-L566","SchC.I","SchA.12"],"affected":["SchC.I","SchA.12","F8283"]},
]
LOCK = threading.RLock()


class ClosingConnection(sqlite3.Connection):
    """SQLite context manager that also closes, so concurrent local requests release handles."""
    def __exit__(self, exc_type, exc, tb):
        try:
            return super().__exit__(exc_type, exc, tb)
        finally:
            self.close()


def load_packet(path: Path | None = None) -> dict:
    if path is None:
        # Prefer the packet delivered for the exercise when present. The tracked
        # redacted copy keeps a fresh GitHub checkout runnable without publishing it.
        path = PACKET_PATH if PACKET_PATH.is_file() else REDACTED_PACKET_PATH
    with path.open(encoding="utf-8") as f:
        packet = json.load(f)
    if not isinstance(packet.get("documents"), list) or not isinstance(packet.get("extracted_values"), list) or not isinstance(packet.get("return_versions"), list):
        raise ValueError("Packet is missing required collections")
    return packet


def validate_packet(packet: dict) -> dict:
    def duplicate_count(items, key):
        values = [x.get(key) for x in items if x.get(key) is not None]
        return len(values) - len(set(values))
    docs = packet["documents"]
    values = packet["extracted_values"]
    versions = packet["return_versions"]
    doc_ids = {d.get("id") for d in docs}
    val_ids = {v.get("id") for v in values}
    line_ids = {l.get("key") for ver in versions for l in ver.get("lines", [])}
    broken_doc_refs = sum(1 for v in values if v.get("document_id") not in doc_ids)
    broken_line_sources = []
    for ver in versions:
        for line in ver.get("lines", []):
            for ref in line.get("sources") or []:
                if isinstance(ref, str) and ref.startswith("ev-") and ref not in val_ids:
                    broken_line_sources.append((ver.get("version"), line.get("key"), ref))
    return {"packet_name":packet.get("packet",{}).get("name"),"documents":len(docs),"extracted_values":len(values),"versions":len(versions),"return_lines_by_version":[{"version":v.get("version"),"lines":len(v.get("lines",[]))} for v in versions],"duplicate_document_ids":duplicate_count(docs,"id"),"duplicate_value_ids":duplicate_count(values,"id"),"duplicate_line_ids_per_version":{v.get("version"):duplicate_count(v.get("lines",[]),"key") for v in versions},"extracted_values_missing_document":broken_doc_refs,"line_sources_missing_extracted_value":broken_line_sources,"sha256":hashlib.sha256(json.dumps(packet,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()}


def db_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=10, factory=ClosingConnection)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.executescript("""
    CREATE TABLE IF NOT EXISTS app_state (key TEXT PRIMARY KEY, value TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS audit (id TEXT PRIMARY KEY, actor TEXT NOT NULL, action TEXT NOT NULL, target TEXT NOT NULL, before_json TEXT, after_json TEXT, reason TEXT NOT NULL, created_at TEXT NOT NULL, reverted_by TEXT);
    CREATE TABLE IF NOT EXISTS review_notes (id TEXT PRIMARY KEY, actor TEXT NOT NULL, target TEXT NOT NULL, note TEXT NOT NULL, blocking INTEGER NOT NULL, status TEXT NOT NULL, version TEXT NOT NULL, created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS questions (id TEXT PRIMARY KEY, actor TEXT NOT NULL, recipient TEXT NOT NULL, prompt TEXT NOT NULL, refs TEXT NOT NULL, status TEXT NOT NULL, response TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS signoffs (id TEXT PRIMARY KEY, actor TEXT NOT NULL, scope TEXT NOT NULL, version TEXT NOT NULL, dependency_hash TEXT NOT NULL, status TEXT NOT NULL, note TEXT, created_at TEXT NOT NULL, stale_reason TEXT);
    CREATE TABLE IF NOT EXISTS scenarios (id TEXT PRIMARY KEY, actor TEXT NOT NULL, base_version TEXT NOT NULL, title TEXT NOT NULL, changes TEXT NOT NULL, hypothetical INTEGER NOT NULL, created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, actor TEXT NOT NULL, assignee TEXT NOT NULL, title TEXT NOT NULL, due_date TEXT, status TEXT NOT NULL, created_at TEXT NOT NULL, refs TEXT NOT NULL DEFAULT '[]');
    CREATE TABLE IF NOT EXISTS time_entries (id TEXT PRIMARY KEY, actor TEXT NOT NULL, area TEXT NOT NULL, minutes INTEGER NOT NULL, note TEXT, created_at TEXT NOT NULL);
    """)
    task_columns={r["name"] for r in c.execute("PRAGMA table_info(tasks)").fetchall()}
    if "refs" not in task_columns:
        c.execute("ALTER TABLE tasks ADD COLUMN refs TEXT NOT NULL DEFAULT '[]'")
    c.commit()
    return c


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def state_load(c):
    row = c.execute("SELECT value FROM app_state WHERE key='workpaper'").fetchone()
    if row:
        return json.loads(row["value"])
    state = {"decisions":{},"decision_notes":{},"work_values":{},"exam_note":"","client_copy_status":"not recorded"}
    c.execute("INSERT INTO app_state(key,value) VALUES('workpaper',?)",(json.dumps(state),))
    c.commit()
    return state


def audit(c, actor, action, target, before, after, reason):
    event_id = str(uuid.uuid4())
    c.execute("INSERT INTO audit VALUES(?,?,?,?,?,?,?,?,NULL)",(event_id,actor,action,target,json.dumps(before,ensure_ascii=False),json.dumps(after,ensure_ascii=False),reason,now()))
    return event_id


def roles_allowed(actor, allowed):
    if actor not in {"Preparer","Reviewer","Partner","Client","Firm administrator","Examiner"}:
        raise PermissionError("Unknown demonstration role")
    if actor not in allowed:
        raise PermissionError(f"{actor} cannot perform this action")


def state_json(c, actor="Preparer"):
    result = state_load(c)
    result.update({"review_notes":[dict(r) for r in c.execute("SELECT * FROM review_notes ORDER BY created_at DESC")],"questions":[dict(r) for r in c.execute("SELECT * FROM questions ORDER BY created_at DESC")],"signoffs":[dict(r) for r in c.execute("SELECT * FROM signoffs ORDER BY created_at DESC")],"scenarios":[dict(r) for r in c.execute("SELECT * FROM scenarios ORDER BY created_at DESC")],"tasks":[dict(r) for r in c.execute("SELECT * FROM tasks ORDER BY created_at DESC")],"time_entries":[dict(r) for r in c.execute("SELECT * FROM time_entries ORDER BY created_at DESC")],"audit":[dict(r) for r in c.execute("SELECT * FROM audit ORDER BY created_at DESC LIMIT 150") ]})
    for q in result["questions"]: q["refs"] = json.loads(q["refs"])
    for s in result["scenarios"]: s["changes"] = json.loads(s["changes"])
    for t in result["tasks"]: t["refs"] = json.loads(t["refs"])
    if actor == "Client":
        result["review_notes"]=[]; result["signoffs"]=[]; result["scenarios"]=[]; result["tasks"]=[]; result["time_entries"]=[]; result["audit"]=[]
        result["questions"]=[q for q in result["questions"] if q["recipient"].lower()=="client"]
        result["decisions"]={}; result["decision_notes"]={}; result["work_values"]={}; result["exam_note"]=""
    elif actor == "Examiner":
        result["review_notes"]=[]; result["questions"]=[]; result["scenarios"]=[]; result["tasks"]=[]; result["time_entries"]=[]; result["signoffs"]=[]; result["decisions"]={}; result["decision_notes"]={}; result["work_values"]={}; result["exam_note"]=""
    return result


def scrub_client(packet):
    v = packet["return_versions"][-1]
    allowed_questions = [q for q in packet.get("client",{}).get("questionnaire",[]) if q.get("answered_by") in {p.get("name") for p in packet["household"].get("people",[])}]
    return {"packet":packet["packet"],"household":{"filing_status":packet["household"].get("filing_status"),"tax_year":packet["household"].get("tax_year")},"summary":v["summary"],"version":v["version"],"questions":allowed_questions,"filing":{"efile":packet.get("tax_agency_records",{}).get("efile",[])}}


def scrub_examiner(packet):
    v=packet["return_versions"][-1]
    return {"packet":packet["packet"],"household":{"filing_status":packet["household"].get("filing_status"),"tax_year":packet["household"].get("tax_year")},"summary":v["summary"],"version":v["version"],"lines":[l for l in v.get("lines",[]) if l.get("key") in {"F1040.7","F1040.8","F1040.11","F1040.15","SchC.I","SchA.12","F8283.1"}],"notices":packet.get("tax_agency_records",{}).get("notices",[]),"efile":packet.get("tax_agency_records",{}).get("efile",[])}


class Handler(BaseHTTPRequestHandler):
    server_version = "FieldnoteDemo/1.0"
    def log_message(self, *_):
        return
    @property
    def actor(self): return self.headers.get("X-Demo-Role","Preparer")
    def send_json(self, data, code=200):
        body=json.dumps(data,ensure_ascii=False).encode("utf-8")
        self.send_response(code); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(body))); self.send_header("Cache-Control","no-store"); self.end_headers(); self.wfile.write(body)
    def read_json(self):
        n=int(self.headers.get("Content-Length","0"))
        if n>1_000_000: raise ValueError("Request body too large")
        return json.loads(self.rfile.read(n) or b"{}")
    def require_demo_auth(self):
        username=os.environ.get("WORKPAPER_USERNAME","")
        password=os.environ.get("WORKPAPER_PASSWORD","")
        if not username or not password:
            return True
        supplied=self.headers.get("Authorization","")
        try:
            scheme,token=supplied.split(" ",1)
            decoded=base64.b64decode(token,validate=True).decode("utf-8")
            user,secret=decoded.split(":",1)
        except (ValueError,UnicodeDecodeError):
            user=secret=""
            scheme=""
        if scheme.lower()=="basic" and hmac.compare_digest(user,username) and hmac.compare_digest(secret,password):
            return True
        self.send_response(401)
        self.send_header("WWW-Authenticate",'Basic realm="Tax workpaper demo", charset="UTF-8"')
        self.send_header("Content-Length","0")
        self.end_headers()
        return False
    def do_GET(self):
        if not self.require_demo_auth(): return
        path=urlparse(self.path).path
        if path=="/api/packet":
            packet=load_packet()
            self.send_json(scrub_client(packet) if self.actor=="Client" else scrub_examiner(packet) if self.actor=="Examiner" else packet); return
        if path=="/api/validation": self.send_json(validate_packet(load_packet())); return
        if path=="/api/issues": self.send_json([] if self.actor in {"Client","Examiner"} else ISSUES); return
        if path=="/api/state":
            with LOCK, db_conn() as c: self.send_json(state_json(c,self.actor))
            return
        if path=="/api/health": self.send_json({"ok":True,"mode":"local-demo","database":str(DB_PATH.name)}); return
        if path=="/" or path=="/index.html": path="/workpaper.html"
        candidate=(ROOT/path.lstrip("/")).resolve()
        if ROOT not in candidate.parents or not candidate.is_file(): self.send_error(404); return
        if candidate in {PACKET_PATH, REDACTED_PACKET_PATH} or candidate.is_relative_to(ROOT / ".demo-data") or candidate.suffix in {".sqlite",".db"}: self.send_error(403); return
        content_type="text/html; charset=utf-8" if candidate.suffix==".html" else "text/javascript; charset=utf-8" if candidate.suffix==".js" else "text/css; charset=utf-8" if candidate.suffix==".css" else "application/json; charset=utf-8" if candidate.suffix==".json" else "application/octet-stream"
        try: data=candidate.read_bytes()
        except OSError: self.send_error(404); return
        self.send_response(200); self.send_header("Content-Type",content_type); self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_POST(self):
        if not self.require_demo_auth(): return
        path=urlparse(self.path).path
        try:
            body=self.read_json()
            with LOCK, db_conn() as c:
                state=state_load(c)
                if path=="/api/decision":
                    roles_allowed(self.actor,{"Preparer","Reviewer","Partner","Firm administrator"})
                    issue_id=body.get("issue_id"); issue=next((x for x in ISSUES if x["id"]==issue_id),None)
                    if not issue: raise KeyError("Unknown issue")
                    status=body.get("status"); reason=(body.get("reason") or "").strip()
                    if status not in {"open","in_review","resolved","deferred"} or len(reason)<4: raise ValueError("Choose a valid status and enter a resolution or status reason (at least 4 characters)")
                    before={"status":state["decisions"].get(issue_id,issue["status"]),"note":state["decision_notes"].get(issue_id,"")}; after={"status":status,"note":reason}
                    state["decisions"][issue_id]=status; state["decision_notes"][issue_id]=reason
                    c.execute("UPDATE app_state SET value=? WHERE key='workpaper'",(json.dumps(state,ensure_ascii=False),)); event=audit(c,self.actor,"issue_decision",issue_id,before,after,reason)
                    c.commit(); self.send_json({"ok":True,"event_id":event,"state":state_json(c,self.actor)}); return
                if path=="/api/work-value":
                    roles_allowed(self.actor,{"Preparer","Reviewer","Partner"})
                    key=body.get("line_key"); line=next((x for x in load_packet()["return_versions"][-1]["lines"] if x.get("key")==key),None)
                    if not line or not isinstance(line.get("value"),(int,float)) or isinstance(line.get("value"),bool): raise ValueError("Choose an existing numeric return line")
                    reason=(body.get("reason") or "").strip(); refs=body.get("refs",[]); value=body.get("value")
                    if not reason or not isinstance(value,(int,float)) or isinstance(value,bool): raise ValueError("A numeric draft value and reason are required")
                    before=state["work_values"].get(key,{"value":line["value"],"reason":"Imported engine value"}); after={"value":value,"reason":reason,"refs":refs,"actor":self.actor,"at":now(),"status":"proposed workpaper value; recomputation required"}
                    state["work_values"][key]=after; c.execute("UPDATE app_state SET value=? WHERE key='workpaper'",(json.dumps(state,ensure_ascii=False),)); event=audit(c,self.actor,"work_value_proposed",key,before,after,reason)
                    c.execute("UPDATE signoffs SET status='stale',stale_reason=? WHERE status='approved' AND (scope=? OR scope='return')",("Relevant line changed after approval: "+key,key))
                    c.commit(); self.send_json({"ok":True,"event_id":event,"state":state_json(c,self.actor)}); return
                if path=="/api/undo":
                    roles_allowed(self.actor,{"Preparer","Reviewer","Partner","Firm administrator"})
                    event=c.execute("SELECT * FROM audit WHERE id=? AND reverted_by IS NULL",(body.get("event_id"),)).fetchone()
                    if not event or event["action"] not in {"issue_decision","work_value_proposed"}: raise KeyError("Undoable change not found")
                    prev=json.loads(event["before_json"])
                    if event["action"]=="issue_decision":
                        state["decisions"][event["target"]]=prev["status"]; state["decision_notes"][event["target"]]=prev["note"]
                    elif prev.get("reason")=="Imported engine value": state["work_values"].pop(event["target"],None)
                    else: state["work_values"][event["target"]]=prev
                    c.execute("UPDATE app_state SET value=? WHERE key='workpaper'",(json.dumps(state,ensure_ascii=False),)); reverse=audit(c,self.actor,"undo_"+event["action"],event["target"],json.loads(event["after_json"]),prev,"Undo of "+event["id"]); c.execute("UPDATE audit SET reverted_by=? WHERE id=?",(reverse,event["id"])); c.commit(); self.send_json({"ok":True,"event_id":reverse,"state":state_json(c,self.actor)}); return
                if path=="/api/review-note":
                    roles_allowed(self.actor,{"Reviewer","Partner"})
                    note=(body.get("note") or "").strip(); target=(body.get("target") or "").strip()
                    if not note or not target: raise ValueError("Target and note are required")
                    row_id=str(uuid.uuid4()); blocking=int(bool(body.get("blocking"))); c.execute("INSERT INTO review_notes VALUES(?,?,?,?,?,?,?,?)",(row_id,self.actor,target,note,blocking,"open",str(body.get("version","v3")),now())); audit(c,self.actor,"review_note_created",target,None,{"note_id":row_id,"blocking":bool(blocking)},"Review note")
                    if blocking: c.execute("UPDATE signoffs SET status='stale',stale_reason=? WHERE status='approved' AND (scope=? OR scope='return')",("Blocking note added for: "+target,target))
                    c.commit(); self.send_json({"ok":True,"state":state_json(c,self.actor)}); return
                if path=="/api/review-note-status":
                    roles_allowed(self.actor,{"Reviewer","Partner"})
                    note=c.execute("SELECT * FROM review_notes WHERE id=?",(body.get("id"),)).fetchone()
                    reason=(body.get("reason") or "").strip()
                    if not note or body.get("status") not in {"open","resolved"} or len(reason)<4: raise ValueError("Choose an existing note, valid status, and reason")
                    c.execute("UPDATE review_notes SET status=? WHERE id=?",(body["status"],body["id"])); audit(c,self.actor,"review_note_"+body["status"],note["target"],{"status":note["status"]},{"status":body["status"],"note_id":note["id"]},reason); c.commit(); self.send_json({"ok":True,"state":state_json(c,self.actor)}); return
                if path=="/api/question":
                    status=body.get("operation","create")
                    if status=="create":
                        roles_allowed(self.actor,{"Preparer","Reviewer","Partner"})
                        prompt=(body.get("prompt") or "").strip(); recipient=(body.get("recipient") or "client").strip()
                        if not prompt: raise ValueError("Question text is required")
                        qid=str(uuid.uuid4()); stamp=now(); refs=json.dumps(body.get("refs",[])); c.execute("INSERT INTO questions VALUES(?,?,?,?,?,?,?,?,?)",(qid,self.actor,recipient,prompt,refs,"sent",None,stamp,stamp)); audit(c,self.actor,"client_question_created",qid,None,{"recipient":recipient,"prompt":prompt,"refs":json.loads(refs)},"Client request"); c.commit(); self.send_json({"ok":True,"state":state_json(c,self.actor)}); return
                    roles_allowed(self.actor,{"Client"})
                    q=c.execute("SELECT * FROM questions WHERE id=?",(body.get("id"),)).fetchone()
                    if not q: raise KeyError("Question not found")
                    response=(body.get("response") or "").strip()
                    if not response: raise ValueError("Response is required")
                    c.execute("UPDATE questions SET status='answered',response=?,updated_at=? WHERE id=?",(response,now(),q["id"])); audit(c,self.actor,"client_response",q["id"],{"status":q["status"]},{"status":"answered","response":response},"Client response"); c.commit(); self.send_json({"ok":True,"state":state_json(c,self.actor)}); return
                if path=="/api/signoff":
                    roles_allowed(self.actor,{"Reviewer","Partner"})
                    scope=(body.get("scope") or "").strip(); version=str(body.get("version","v3")); decision=body.get("decision")
                    if decision not in {"approve","request_changes"} or not scope: raise ValueError("Scope and decision are required")
                    blocking=c.execute("SELECT COUNT(*) AS n FROM review_notes WHERE status='open' AND blocking=1 AND (target=? OR target='return')",(scope,)).fetchone()["n"]
                    if decision=="approve" and blocking: raise ValueError("Blocking review notes must be resolved before sign-off")
                    digest=hashlib.sha256(f"{scope}|{version}|{json.dumps(state['work_values'],sort_keys=True)}".encode()).hexdigest(); sid=str(uuid.uuid4()); c.execute("INSERT INTO signoffs VALUES(?,?,?,?,?,?,?,?,NULL)",(sid,self.actor,scope,version,digest,"approved" if decision=="approve" else "changes_requested",body.get("note"),now())); audit(c,self.actor,"signoff_"+decision,scope,None,{"version":version,"dependency_hash":digest},body.get("note") or decision); c.commit(); self.send_json({"ok":True,"state":state_json(c,self.actor)}); return
                if path=="/api/scenario":
                    roles_allowed(self.actor,{"Preparer","Reviewer","Partner"})
                    title=(body.get("title") or "").strip(); changes=body.get("changes",[])
                    if not title: raise ValueError("Scenario title is required")
                    sid=str(uuid.uuid4()); c.execute("INSERT INTO scenarios VALUES(?,?,?,?,?,?,?)",(sid,self.actor,str(body.get("base_version","v3")),title,json.dumps(changes),1,now())); audit(c,self.actor,"scenario_created",sid,None,{"title":title,"changes":changes,"hypothetical":True},"Hypothetical only"); c.commit(); self.send_json({"ok":True,"state":state_json(c,self.actor)}); return
                if path=="/api/task":
                    roles_allowed(self.actor,{"Preparer","Partner","Firm administrator"})
                    title=(body.get("title") or "").strip(); assignee=(body.get("assignee") or "").strip()
                    if not title or not assignee: raise ValueError("Task title and assignee are required")
                    refs=body.get("refs",[])
                    if not isinstance(refs,list) or any(x not in {i["id"] for i in ISSUES} for x in refs): raise ValueError("Task issue references must use known issue IDs")
                    tid=str(uuid.uuid4()); c.execute("INSERT INTO tasks(id,actor,assignee,title,due_date,status,created_at,refs) VALUES(?,?,?,?,?,?,?,?)",(tid,self.actor,assignee,title,body.get("due_date"),"open",now(),json.dumps(refs))); audit(c,self.actor,"task_assigned",tid,None,{**body,"refs":refs},"Assignment"); c.commit(); self.send_json({"ok":True,"state":state_json(c,self.actor)}); return
                if path=="/api/time":
                    roles_allowed(self.actor,{"Preparer","Reviewer","Partner","Firm administrator"})
                    mins=int(body.get("minutes",0)); area=(body.get("area") or "").strip()
                    if mins<1 or mins>1440 or not area: raise ValueError("Enter a work area and minutes from 1 to 1440")
                    tid=str(uuid.uuid4()); c.execute("INSERT INTO time_entries VALUES(?,?,?,?,?,?)",(tid,self.actor,area,mins,body.get("note"),now())); audit(c,self.actor,"time_recorded",tid,None,body,"Time entry"); c.commit(); self.send_json({"ok":True,"state":state_json(c,self.actor)}); return
                if path=="/api/exam-note":
                    roles_allowed(self.actor,{"Preparer","Reviewer","Partner"})
                    text=(body.get("text") or ""); before=state.get("exam_note",""); state["exam_note"]=text; c.execute("UPDATE app_state SET value=? WHERE key='workpaper'",(json.dumps(state,ensure_ascii=False),)); audit(c,self.actor,"exam_note_updated","N-2025-L566",before,text,"Notice response workspace note"); c.commit(); self.send_json({"ok":True,"state":state_json(c,self.actor)}); return
                if path=="/api/filing-action":
                    roles_allowed(self.actor,{"Preparer","Partner"})
                    action=body.get("action")
                    if action not in {"mark_client_copy_sent","create_amendment_draft"}: raise ValueError("Unsupported filing action")
                    if action=="mark_client_copy_sent":
                        before=state.get("client_copy_status"); state["client_copy_status"]="recorded as sent"; c.execute("UPDATE app_state SET value=? WHERE key='workpaper'",(json.dumps(state),)); audit(c,self.actor,action,"v3",before,state["client_copy_status"],body.get("reason","Recorded by user"))
                    else:
                        aid=str(uuid.uuid4()); c.execute("INSERT INTO tasks(id,actor,assignee,title,due_date,status,created_at,refs) VALUES(?,?,?,?,?,?,?,?)",(aid,self.actor,self.actor,"Prepare amendment from filed v3",None,"open",now(),"[]")); audit(c,self.actor,action,aid,None,{"based_on":"v3","external_filing":False},body.get("reason","Amendment draft initiated"))
                    c.commit(); self.send_json({"ok":True,"state":state_json(c,self.actor)}); return
                self.send_json({"error":"Not found"},404)
        except PermissionError as e: self.send_json({"error":str(e)},403)
        except KeyError as e: self.send_json({"error":str(e)},404)
        except (ValueError,TypeError,json.JSONDecodeError) as e: self.send_json({"error":str(e)},400)
        except Exception as e: self.send_json({"error":"Request failed: "+str(e)},500)


def main():
    packet=load_packet(); summary=validate_packet(packet)
    print(f"Loaded {summary['documents']} documents, {summary['extracted_values']} extracted values, {summary['versions']} return versions")
    print(f"Validation: duplicate docs={summary['duplicate_document_ids']}, duplicate values={summary['duplicate_value_ids']}, values without documents={summary['extracted_values_missing_document']}, unresolved source refs={len(summary['line_sources_missing_extracted_value'])}")
    print("Demo role switching is not authentication. Do not load real taxpayer data.")
    with db_conn() as c: state_load(c)
    port=int(os.environ.get("PORT","8765"))
    host=os.environ.get("HOST","0.0.0.0" if "PORT" in os.environ else "127.0.0.1")
    server=ThreadingHTTPServer((host,port),Handler)
    print(f"Serving on {host}:{port}; local default is loopback only. Demo role switching is not authentication.")
    server.serve_forever()

if __name__=="__main__": main()
