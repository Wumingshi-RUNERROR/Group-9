from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Flask, flash, g, redirect, render_template, request, url_for


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "last_resort.db"
CREATE_SQL = BASE_DIR / "Group9_milestone2_create.sql"
INSERT_SQL = BASE_DIR / "Group9_milestone2_insert.sql"


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "last-resort-dev-secret")
    app.config["DB_PATH"] = str(DB_PATH)
    register_routes(app)
    return app


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        g.db = conn
    return g.db


def close_db(_: Any = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(force_reset: bool = False) -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    with closing(conn.cursor()) as cur:
        if force_reset:
            cur.executescript(
                """
                DROP TABLE IF EXISTS maintenance_ticket;
                DROP TABLE IF EXISTS charge;
                DROP TABLE IF EXISTS service_type;
                DROP TABLE IF EXISTS event_room;
                DROP TABLE IF EXISTS event;
                DROP TABLE IF EXISTS stay;
                DROP TABLE IF EXISTS room_assignment;
                DROP TABLE IF EXISTS reservation;
                DROP TABLE IF EXISTS billing_account;
                DROP TABLE IF EXISTS guest_group;
                DROP TABLE IF EXISTS party;
                DROP TABLE IF EXISTS room_adjacency;
                DROP TABLE IF EXISTS room_has_bed;
                DROP TABLE IF EXISTS bed_type;
                DROP TABLE IF EXISTS room_function;
                DROP TABLE IF EXISTS function;
                DROP TABLE IF EXISTS room;
                DROP TABLE IF EXISTS floor;
                DROP TABLE IF EXISTS wing;
                DROP TABLE IF EXISTS building;
                DROP TABLE IF EXISTS hotel;
                """
            )
            conn.commit()

        has_tables = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='hotel'"
        ).fetchone()
        if not has_tables:
            cur.executescript(CREATE_SQL.read_text(encoding="utf-8"))
            cur.executescript(INSERT_SQL.read_text(encoding="utf-8"))
            conn.commit()
    conn.close()


def rowmax(db: sqlite3.Connection, table: str, column: str) -> int:
    row = db.execute(f"SELECT COALESCE(MAX({column}), 0) + 1 AS nid FROM {table}").fetchone()
    return int(row["nid"])


def parse_bool_flag(value: str | None) -> int:
    return 1 if value in {"1", "on", "true", "True"} else 0


def sync_maintenance_room_status(db: sqlite3.Connection, room_id: str | None = None) -> None:
    if room_id:
        db.execute(
            """
            UPDATE room
            SET currentStatus = 'Maintenance'
            WHERE roomId = ?
              AND EXISTS (
                  SELECT 1
                  FROM maintenance_ticket mt
                  WHERE mt.roomId = room.roomId
                    AND LOWER(mt.status) <> 'resolved'
              )
            """,
            (room_id,),
        )
    else:
        db.execute(
            """
            UPDATE room
            SET currentStatus = 'Maintenance'
            WHERE EXISTS (
                SELECT 1
                FROM maintenance_ticket mt
                WHERE mt.roomId = room.roomId
                  AND LOWER(mt.status) <> 'resolved'
            )
            """
        )


def register_routes(app: Flask) -> None:
    app.teardown_appcontext(close_db)

    @app.route("/")
    def home():
        return redirect(url_for("dashboard"))

    @app.route("/init-db")
    def init_db_route():
        force = request.args.get("force", "0") == "1"
        init_db(force_reset=force)
        flash("Database initialized from schema and seed data.", "success")
        return redirect(url_for("dashboard"))

    @app.route("/dashboard")
    def dashboard():
        db = get_db()
        sync_maintenance_room_status(db)
        db.commit()
        date_from   = request.args.get("date_from",   "")
        date_to     = request.args.get("date_to",     "")
        building_id = request.args.get("building_id", "")
        wing_code   = request.args.get("wing_code",   "")
        party_type  = request.args.get("party_type",  "")

        # Reusable EXISTS snippet – filters a reservation's rooms by building/wing.
        # Always included (with empty-string guards) so all KPIs use the same counting path,
        # guaranteeing Wing A + Wing B == Total when no other filter differs.
        _room_scope_sql = """
            EXISTS (
                SELECT 1 FROM room_assignment _ra
                JOIN room     _rm ON _rm.roomId    = _ra.roomId
                JOIN floor    _fl ON _fl.floorId   = _rm.floorId
                JOIN wing     _w  ON _w.wingId     = _fl.wingId
                JOIN building _b  ON _b.buildingId = _w.buildingId
                WHERE _ra.reservationId = r.reservationId
                  AND (? = '' OR _b.buildingId = ?)
                  AND (? = '' OR _w.wingCode   = ?)
            )"""
        _rs_params = [building_id, building_id, wing_code, wing_code]

        # ── Total Revenue ──────────────────────────────────────────────────────
        rev_f: list[str] = [_room_scope_sql]
        rev_p: list[Any] = list(_rs_params)
        if date_from:
            rev_f.append("c.dateIncurred >= ?"); rev_p.append(date_from)
        if date_to:
            rev_f.append("c.dateIncurred <= ?"); rev_p.append(date_to)
        if party_type:
            rev_f.append("p.partyType = ?"); rev_p.append(party_type)

        revenue = db.execute(
            f"""
            SELECT COALESCE(SUM(c.chargeAmount), 0) AS total_revenue
            FROM charge c
            JOIN stay s        ON s.stayId        = c.stayId
            JOIN reservation r ON r.reservationId = s.reservationId
            JOIN party p       ON p.partyId       = r.partyId
            WHERE {' AND '.join(rev_f)}
            """,
            rev_p,
        ).fetchone()["total_revenue"]

        # ── Total Events ───────────────────────────────────────────────────────
        evt_f: list[str] = []
        evt_p: list[Any] = []
        if date_from:
            evt_f.append("date(e.startTime) >= date(?)"); evt_p.append(date_from)
        if date_to:
            evt_f.append("date(e.endTime) <= date(?)"); evt_p.append(date_to)
        if party_type:
            evt_f.append("p.partyType = ?"); evt_p.append(party_type)
        if building_id or wing_code:
            evt_f.append("""
                EXISTS (
                    SELECT 1 FROM event_room _er
                    JOIN room     _rm ON _rm.roomId    = _er.roomId
                    JOIN floor    _fl ON _fl.floorId   = _rm.floorId
                    JOIN wing     _w  ON _w.wingId     = _fl.wingId
                    JOIN building _b  ON _b.buildingId = _w.buildingId
                    WHERE _er.eventId = e.eventId
                      AND (? = '' OR _b.buildingId = ?)
                      AND (? = '' OR _w.wingCode   = ?)
                )""")
            evt_p.extend(_rs_params)
        evt_where = f"WHERE {' AND '.join(evt_f)}" if evt_f else ""

        total_events = db.execute(
            f"""
            SELECT COUNT(DISTINCT e.eventId) AS total_events
            FROM event e
            JOIN party p ON p.partyId = e.hostPartyId
            {evt_where}
            """,
            evt_p,
        ).fetchone()["total_events"]

        # ── Average Stay Duration ──────────────────────────────────────────────
        stay_f: list[str] = ["s.checkoutTime IS NOT NULL", _room_scope_sql]
        stay_p: list[Any] = list(_rs_params)
        if date_from:
            stay_f.append("date(s.checkinTime) >= date(?)"); stay_p.append(date_from)
        if date_to:
            stay_f.append("date(s.checkoutTime) <= date(?)"); stay_p.append(date_to)
        if party_type:
            stay_f.append("p.partyType = ?"); stay_p.append(party_type)

        avg_stay_days = db.execute(
            f"""
            SELECT COALESCE(ROUND(AVG(julianday(s.checkoutTime) - julianday(s.checkinTime)), 2), 0) AS avg_days
            FROM stay s
            JOIN reservation r ON r.reservationId = s.reservationId
            JOIN party p       ON p.partyId       = r.partyId
            WHERE {' AND '.join(stay_f)}
            """,
            stay_p,
        ).fetchone()["avg_days"]

        # ── Active Assignments ─────────────────────────────────────────────────
        active_assignments = db.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM room_assignment ra
            JOIN room     rm ON rm.roomId    = ra.roomId
            JOIN floor    fl ON fl.floorId   = rm.floorId
            JOIN wing     w  ON w.wingId     = fl.wingId
            JOIN building b  ON b.buildingId = w.buildingId
            JOIN reservation r ON r.reservationId = ra.reservationId
            JOIN party p ON p.partyId = r.partyId
            LEFT JOIN (
                SELECT reservationId, MAX(stayId) AS latest_stay
                FROM stay GROUP BY reservationId
            ) ls ON ls.reservationId = ra.reservationId
            LEFT JOIN stay s ON s.stayId = ls.latest_stay
            WHERE (s.checkoutTime IS NULL OR s.stayId IS NULL)
              AND (? = '' OR b.buildingId = ?)
              AND (? = '' OR w.wingCode   = ?)
              AND (? = '' OR p.partyType  = ?)
            """,
            [building_id, building_id, wing_code, wing_code, party_type, party_type],
        ).fetchone()["cnt"]

        # ── Open Maintenance Tickets ───────────────────────────────────────────
        open_tickets = db.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM maintenance_ticket mt
            JOIN room     rm ON rm.roomId    = mt.roomId
            JOIN floor    fl ON fl.floorId   = rm.floorId
            JOIN wing     w  ON w.wingId     = fl.wingId
            JOIN building b  ON b.buildingId = w.buildingId
            WHERE lower(mt.status) <> 'resolved'
              AND (? = '' OR b.buildingId = ?)
              AND (? = '' OR w.wingCode   = ?)
            """,
            [building_id, building_id, wing_code, wing_code],
        ).fetchone()["cnt"]

        occupancy = db.execute(
            """
            SELECT
                b.buildingName,
                SUM(CASE WHEN lower(r.currentStatus) = 'occupied'    THEN 1 ELSE 0 END) AS occupied,
                SUM(CASE WHEN lower(r.currentStatus) = 'available'   THEN 1 ELSE 0 END) AS available,
                SUM(CASE WHEN lower(r.currentStatus) = 'maintenance' THEN 1 ELSE 0 END) AS maintenance
            FROM room r
            JOIN floor f ON f.floorId = r.floorId
            JOIN wing w ON w.wingId = f.wingId
            JOIN building b ON b.buildingId = w.buildingId
            WHERE (? = '' OR b.buildingId = ?) AND (? = '' OR w.wingCode = ?)
            GROUP BY b.buildingId, b.buildingName
            ORDER BY b.buildingName
            """,
            (building_id, building_id, wing_code, wing_code),
        ).fetchall()

        buildings = db.execute("SELECT buildingId, buildingName FROM building ORDER BY buildingName").fetchall()

        # Distinct wing codes, each carrying a JSON list of buildingIds that have it
        import json as _json
        wing_rows = db.execute(
            "SELECT wingCode, GROUP_CONCAT(buildingId) AS bids FROM wing GROUP BY wingCode ORDER BY wingCode"
        ).fetchall()
        wings = [
            {"wingCode": r["wingCode"], "buildingIds": [int(x) for x in r["bids"].split(",")]}
            for r in wing_rows
        ]
        wings_json = _json.dumps(wings)

        party_types = db.execute("SELECT DISTINCT partyType FROM party ORDER BY partyType").fetchall()

        return render_template(
            "dashboard.html",
            revenue=revenue,
            total_events=total_events,
            avg_stay_days=avg_stay_days,
            active_assignments=active_assignments,
            open_tickets=open_tickets,
            occupancy=occupancy,
            buildings=buildings,
            wings=wings,
            wings_json=wings_json,
            party_types=party_types,
            filters={
                "date_from": date_from,
                "date_to": date_to,
                "building_id": building_id,
                "wing_code": wing_code,
                "party_type": party_type,
            },
        )

    @app.route("/inventory", methods=["GET", "POST"])
    def inventory():
        db = get_db()
        if request.method == "POST":
            action = request.form.get("action")
            try:
                if action == "update_room":
                    db.execute(
                        "UPDATE room SET baseRate = ?, maxCapacity = ?, currentStatus = ? WHERE roomId = ?",
                        (request.form["baseRate"], request.form["maxCapacity"], request.form["currentStatus"], request.form["roomId"]),
                    )
                    sync_maintenance_room_status(db, request.form["roomId"])
                elif action == "add_room_function":
                    db.execute(
                        "INSERT INTO room_function (roomId, functionCode, activeness) VALUES (?, ?, ?)",
                        (request.form["roomId"], request.form["functionCode"], request.form.get("activeness", "Active")),
                    )
                elif action == "add_room_bed":
                    db.execute(
                        "INSERT INTO room_has_bed (roomId, bedTypeId, quantity, isFoldable) VALUES (?, ?, ?, ?)",
                        (request.form["roomId"], request.form["bedTypeId"], request.form["quantity"], parse_bool_flag(request.form.get("isFoldable"))),
                    )
                # 删除了 add_adjacency 的处理逻辑
                db.commit()
                flash("Inventory updated successfully.", "success")
            except sqlite3.IntegrityError as exc:
                flash(f"Inventory action failed: {exc}", "error")
            return redirect(url_for("inventory"))

        # --- 获取筛选参数 (GET) ---
        sync_maintenance_room_status(db)
        db.commit()

        search_room_id = request.args.get("search_room_id", "").strip()
        filter_status = request.args.get("filter_status", "").strip()
        filter_function = request.args.get("filter_function", "").strip()
        filter_bed_type = request.args.get("filter_bed_type", "").strip()
        filter_max_rate = request.args.get("filter_max_rate", "").strip()

        # --- 构建动态 SQL 查询 ---
        query = """
            SELECT r.roomId, r.roomId AS roomLabel, r.roomNumber, r.baseRate, r.maxCapacity, r.currentStatus,
                f.floorNumber, f.nonSmokingFloor, w.wingCode, b.buildingName
            FROM room r
            JOIN floor f ON f.floorId = r.floorId
            JOIN wing w ON w.wingId = f.wingId
            JOIN building b ON b.buildingId = w.buildingId
            WHERE 1=1
        """
        params = []

        if search_room_id:
            query += " AND r.roomId LIKE ?"
            params.append(f"%{search_room_id}%")
        if filter_status:
            query += " AND r.currentStatus = ?"
            params.append(filter_status)
        if filter_max_rate:
            max_rate = max(0.0, float(filter_max_rate))
            query += " AND r.baseRate <= ?"
            params.append(max_rate)
        if filter_function:
            query += " AND EXISTS (SELECT 1 FROM room_function rf WHERE rf.roomId = r.roomId AND rf.functionCode = ?)"
            params.append(filter_function)
        if filter_bed_type:
            query += " AND EXISTS (SELECT 1 FROM room_has_bed rb WHERE rb.roomId = r.roomId AND rb.bedTypeId = ?)"
            params.append(filter_bed_type)

        query += " ORDER BY b.buildingName, w.wingCode, f.floorNumber, r.roomNumber"
        rooms = db.execute(query, params).fetchall()

        # 其他数据展示
        room_functions = db.execute(
            """
            SELECT rf.roomId, rf.roomId AS roomLabel, rf.functionCode, fn.functionName, rf.activeness
            FROM room_function rf
            JOIN function fn ON fn.functionCode = rf.functionCode
            ORDER BY rf.roomId
            """
        ).fetchall()
        room_beds = db.execute(
            """
            SELECT rb.roomId, rb.roomId AS roomLabel, bt.name AS bedType, rb.quantity, rb.isFoldable
            FROM room_has_bed rb
            JOIN bed_type bt ON bt.bedTypeId = rb.bedTypeId
            ORDER BY rb.roomId
            """
        ).fetchall()
        adjacency = db.execute(
            """
            SELECT roomId1, roomId1 AS roomLabel1, roomId2, roomId2 AS roomLabel2, connectionType
            FROM room_adjacency
            ORDER BY roomId1
            """
        ).fetchall()
        
        # 供下拉菜单使用的原始数据
        functions_list = db.execute("SELECT functionCode, functionName FROM function ORDER BY functionName").fetchall()
        bed_types_list = db.execute("SELECT bedTypeId, name FROM bed_type ORDER BY name").fetchall()

        return render_template(
            "inventory.html",
            rooms=rooms,
            room_functions=room_functions,
            room_beds=room_beds,
            adjacency=adjacency,
            functions=functions_list,
            bed_types=bed_types_list,
            filters={ # 将当前筛选值传回前端，保持搜索状态
                "search_room_id": search_room_id,
                "filter_status": filter_status,
                "filter_function": filter_function,
                "filter_bed_type": filter_bed_type,
                "filter_max_rate": filter_max_rate
            }
        )

    @app.route("/parties", methods=["GET", "POST"])
    def parties():
        db = get_db()
        if request.method == "POST":
            action = request.form.get("action")
            try:
                if action == "create_party":
                    party_id = rowmax(db, "party", "partyId")
                    db.execute(
                        """
                        INSERT INTO party (partyId, email, phone, partyType, contactPersonName)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            party_id,
                            request.form["email"],
                            request.form["phone"],
                            request.form["partyType"],
                            request.form["contactPersonName"],
                        ),
                    )
                elif action == "add_guest":
                    party_id = int(request.form["partyId"])
                    guest_id = rowmax(
                        db,
                        "guest_group",
                        "guestId",
                    )
                    db.execute(
                        """
                        INSERT INTO guest_group (partyId, guestId, guestName)
                        VALUES (?, ?, ?)
                        """,
                        (party_id, guest_id, request.form["guestName"]),
                    )
                db.commit()
                flash("Party data saved.", "success")
            except sqlite3.IntegrityError as exc:
                flash(f"Party action failed: {exc}", "error")
            return redirect(url_for("parties"))

        keyword = request.args.get("q", "").strip()
        party_type = request.args.get("party_type", "").strip()
        filters = []
        params: list[Any] = []
        if keyword:
            filters.append("(p.contactPersonName LIKE ? OR p.email LIKE ? OR p.phone LIKE ?)")
            kw = f"%{keyword}%"
            params.extend([kw, kw, kw])
        if party_type:
            filters.append("p.partyType = ?")
            params.append(party_type)
        where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""

        parties_data = db.execute(
            f"""
            SELECT p.partyId, p.partyType, p.contactPersonName, p.email, p.phone,
                   ba.accountId, ba.status AS accountStatus, ba.creditLimit
            FROM party p
            LEFT JOIN billing_account ba ON ba.partyId = p.partyId
            {where_sql}
            ORDER BY p.partyId DESC
            """,
            params,
        ).fetchall()
        guests = db.execute(
            "SELECT partyId, guestId, guestName FROM guest_group ORDER BY partyId, guestId"
        ).fetchall()
        party_types = db.execute("SELECT DISTINCT partyType FROM party ORDER BY partyType").fetchall()

        return render_template(
            "parties.html",
            parties=parties_data,
            guests=guests,
            party_types=party_types,
            filters={"q": keyword, "party_type": party_type},
        )

    @app.route("/reservations", methods=["GET", "POST"])
    def reservations():
        db = get_db()
        
        view = request.args.get("view", "view")
        step = request.args.get("step", "party")
        current_party_id = request.args.get("current_party_id")

        if request.method == "POST":
            action = request.form.get("action")
            try:
                if action == "create_party":
                    party_id = rowmax(db, "party", "partyId")
                    db.execute(
                        "INSERT INTO party (partyId, email, phone, partyType, contactPersonName) VALUES (?, ?, ?, ?, ?)",
                        (party_id, request.form["email"], request.form["phone"], request.form["partyType"], request.form["contactPersonName"]),
                    )
                    db.commit()
                    return redirect(url_for("reservations", view="create", step="guests", current_party_id=party_id))

                elif action == "add_guest":
                    p_id = request.form["partyId"]
                    guest_id = rowmax(db, "guest_group", "guestId")
                    db.execute("INSERT INTO guest_group (partyId, guestId, guestName) VALUES (?, ?, ?)",
                            (p_id, guest_id, request.form["guestName"]))
                    db.commit()
                    return redirect(url_for("reservations", view="create", step="guests", current_party_id=p_id))

                elif action == "create_reservation":
                    res_id = rowmax(db, "reservation", "reservationId")
                    db.execute(
                        """INSERT INTO reservation (reservationId, partyId, dateCreated, startDate, endDate, status, depositRequired, depositAmount)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (res_id, request.form["partyId"], request.form["dateCreated"], request.form["startDate"], request.form["endDate"], 
                        request.form["status"], 1 if request.form.get("depositAmount") else 0, float(request.form.get("depositAmount") or 0)),
                    )
                    db.commit()
                    flash("Reservation created!", "success")
                    return redirect(url_for("reservations", view="view"))

                # --- 恢复并优化：更新预订状态 ---
                elif action == "update_status":
                    db.execute("UPDATE reservation SET status = ? WHERE reservationId = ?", 
                            (request.form["status"], request.form["reservationId"]))
                    db.commit()
                    flash(f"Reservation #{request.form['reservationId']} updated.", "success")
                    return redirect(url_for("reservations", view="view", res_q=request.form.get("res_q", "")))

            except sqlite3.IntegrityError as exc:
                flash(f"Error: {exc}", "error")

        # --- GET 逻辑：数据获取与搜索 ---
        
        # 1. Party & Guest 搜索联动
        party_q = request.args.get("q", "").strip()
        p_params = []
        p_sql = "SELECT * FROM party"
        if party_q:
            p_sql += " WHERE contactPersonName LIKE ? OR email LIKE ? OR phone LIKE ?"
            p_params.extend([f"%{party_q}%"] * 3)
        p_sql += " ORDER BY partyId DESC"
        parties_data = db.execute(p_sql, p_params).fetchall()

        # 只获取当前搜索结果中 Party 对应的 Guest
        if party_q:
            p_ids = [p["partyId"] for p in parties_data]
            if p_ids:
                placeholders = ','.join(['?'] * len(p_ids))
                guests = db.execute(f"SELECT * FROM guest_group WHERE partyId IN ({placeholders})", p_ids).fetchall()
            else:
                guests = []
        elif step == "guests" and current_party_id:
            guests = db.execute("SELECT * FROM guest_group WHERE partyId = ?", (current_party_id,)).fetchall()
        else:
            # 默认显示最新添加的 20 个成员（避免列表过长）
            guests = db.execute("SELECT * FROM guest_group ORDER BY partyId DESC LIMIT 20").fetchall()

        # 2. Reservation 搜索
        res_q = request.args.get("res_q", "").strip()
        res_params = []
        res_sql = """
            SELECT r.*, p.contactPersonName, p.partyType 
            FROM reservation r JOIN party p ON p.partyId = r.partyId 
        """
        if res_q:
            res_sql += " WHERE p.contactPersonName LIKE ?"
            res_params.append(f"%{res_q}%")
        res_sql += " ORDER BY r.startDate DESC"
        res_rows = db.execute(res_sql, res_params).fetchall()

        return render_template(
            "reservations.html",
            reservations=res_rows,
            parties=parties_data,
            guests=guests,
            view=view, step=step, current_party_id=current_party_id,
            filters={"q": party_q, "res_q": res_q}
        )

    @app.route("/assignments", methods=["GET", "POST"])
    def assignments():
        db = get_db()
        
        if request.method == "POST":
            action = request.form.get("action")
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            try:
                # --- 分配/重新分配房间 ---
                if action == "assign_room":
                    res_id = request.form["reservationId"]
                    new_room_id = request.form["roomId"]
                    
                    # 检查该预订是否已经分配过房间
                    existing = db.execute("SELECT roomId FROM room_assignment WHERE reservationId = ?", (res_id,)).fetchone()
                    
                    if existing:
                        # 如果有，先释放旧房间
                        db.execute("UPDATE room SET currentStatus = 'Available' WHERE roomId = ?", (existing["roomId"],))
                        # 更新分配记录
                        db.execute("UPDATE room_assignment SET roomId = ?, assignmentDate = date('now') WHERE reservationId = ?", (new_room_id, res_id))
                        flash(f"Room reassigned for Reservation #{res_id}.", "success")
                    else:
                        # 如果没有，创建新分配记录
                        a_id = rowmax(db, "room_assignment", "assignmentId")
                        db.execute("INSERT INTO room_assignment (assignmentId, reservationId, roomId, assignmentDate) VALUES (?, ?, ?, date('now'))", 
                                (a_id, res_id, new_room_id))
                        flash(f"Room assigned for Reservation #{res_id}.", "success")
                    
                    # 将新房间状态设为 Occupied
                    db.execute("UPDATE room SET currentStatus = 'Occupied' WHERE roomId = ?", (new_room_id,))
                    db.commit()

                # --- 办理入住 (Check-In) ---
                elif action == "checkin":
                    res_id = request.form["reservationId"]
                    # 防御性检查：确保没有重复 Check-in
                    if not db.execute("SELECT stayId FROM stay WHERE reservationId = ?", (res_id,)).fetchone():
                        s_id = rowmax(db, "stay", "stayId")
                        db.execute("INSERT INTO stay (stayId, reservationId, checkinTime) VALUES (?, ?, ?)", (s_id, res_id, now_str))
                        db.commit()
                        flash(f"Check-in completed for Reservation #{res_id} at {now_str}.", "success")
                    else:
                        flash("Already checked in!", "error")

                # --- 办理退房 (Check-Out) ---
                elif action == "checkout":
                    stay_id = request.form["stayId"]
                    stay_record = db.execute("SELECT checkoutTime, reservationId FROM stay WHERE stayId = ?", (stay_id,)).fetchone()
                    
                    # 防御性检查：确保没有重复 Check-out
                    if stay_record and stay_record["checkoutTime"] is None:
                        res_id = stay_record["reservationId"]
                        # 记录退房时间
                        db.execute("UPDATE stay SET checkoutTime = ? WHERE stayId = ?", (now_str, stay_id))
                        
                        # 查找对应的房间并将其释放回 Available
                        room_record = db.execute("SELECT roomId FROM room_assignment WHERE reservationId = ?", (res_id,)).fetchone()
                        if room_record:
                            db.execute("UPDATE room SET currentStatus = 'Available' WHERE roomId = ?", (room_record["roomId"],))
                        
                        db.commit()
                        flash(f"Check-out completed for Stay #{stay_id}.", "success")
                    else:
                        flash("Already checked out or stay not found!", "error")

            except sqlite3.IntegrityError as exc:
                flash(f"Action failed: {exc}", "error")
                
            return redirect(url_for("assignments"))

        # --- GET 请求数据获取 ---
        
        # 1. 获取需要处理的预订（未退房的 Confirmed/Pending 预订）
        actionable_reservations = db.execute("""
            SELECT r.reservationId, r.startDate, r.endDate, p.contactPersonName,
                a.assignmentId, rm.roomNumber, a.roomId AS roomLabel,
                s.stayId, s.checkinTime
            FROM reservation r
            JOIN party p ON r.partyId = p.partyId
            LEFT JOIN room_assignment a ON r.reservationId = a.reservationId
            LEFT JOIN room rm ON a.roomId = rm.roomId
            LEFT JOIN stay s ON r.reservationId = s.reservationId
            WHERE r.status IN ('Confirmed', 'Pending')
            AND s.checkoutTime IS NULL
            ORDER BY r.startDate ASC
        """).fetchall()

        # 2. 仅获取 Available 的房间供分配
        available_rooms = db.execute(
            "SELECT roomId, roomId AS roomLabel, currentStatus FROM room WHERE currentStatus = 'Available' ORDER BY roomId"
        ).fetchall()

        # 3. 历史分配和入住记录
        assignments_list = db.execute("""
            SELECT a.assignmentId, a.reservationId, a.assignmentDate, p.contactPersonName,
                a.roomId, a.roomId AS roomLabel, rm.currentStatus
            FROM room_assignment a
            JOIN reservation r ON a.reservationId = r.reservationId
            JOIN party p ON r.partyId = p.partyId
            JOIN room rm ON a.roomId = rm.roomId
            ORDER BY a.assignmentId DESC
        """).fetchall()

        stays_list = db.execute("""
            SELECT s.stayId, s.reservationId, s.checkinTime, s.checkoutTime, p.contactPersonName
            FROM stay s
            JOIN reservation r ON s.reservationId = r.reservationId
            JOIN party p ON r.partyId = p.partyId
            ORDER BY s.checkinTime DESC
        """).fetchall()

        # 检查是否有正在分配的特定 Reservation ID
        assign_res_id = request.args.get("assign_res_id")
        assign_res_name = request.args.get("assign_res_name")

        return render_template(
            "assignments.html",
            actionable_reservations=actionable_reservations,
            rooms=available_rooms,
            assignments=assignments_list,
            stays=stays_list,
            assign_res_id=assign_res_id,
            assign_res_name=assign_res_name
        )

    @app.route("/events", methods=["GET", "POST"])
    def events():
        db = get_db()
        if request.method == "POST":
            action = request.form.get("action")
            try:
                if action == "create_event":
                    event_id = rowmax(db, "event", "eventId")
                    db.execute(
                        """
                        INSERT INTO event (eventId, hostPartyId, eventType, startTime, endTime, estimatedGuestCount)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            event_id,
                            request.form["hostPartyId"],
                            request.form["eventType"],
                            request.form["startTime"],
                            request.form["endTime"],
                            request.form.get("estimatedGuestCount") or None,
                        ),
                    )
                elif action == "add_event_room":
                    event_id = request.form["eventId"]
                    room_id = request.form["roomId"]
                    
                    # 1. 检查房间是否 Available
                    room_status = db.execute("SELECT currentStatus FROM room WHERE roomId = ?", (room_id,)).fetchone()
                    if not room_status or room_status["currentStatus"].lower() != "available":
                        flash("Error: The selected room is not Available.", "error")
                        return redirect(url_for("events"))

                    # 2. 检查 Event 是否已经有房间，如果有则更新，没有则插入
                    existing = db.execute("SELECT roomId FROM event_room WHERE eventId = ?", (event_id,)).fetchone()
                    if existing:
                        db.execute("UPDATE event_room SET roomId = ? WHERE eventId = ?", (room_id, event_id))
                        flash("Event room reassigned successfully.", "success")
                    else:
                        db.execute("INSERT INTO event_room (eventId, roomId) VALUES (?, ?)", (event_id, room_id))
                        flash("Room assigned to event successfully.", "success")
                        
                db.commit()
            except sqlite3.IntegrityError as exc:
                flash(f"Event action failed: {exc}", "error")
            return redirect(url_for("events"))

        # ... (保留原有的 GET 逻辑) ...
        event_rows = db.execute(
            """
            SELECT e.*, p.contactPersonName
            FROM event e
            JOIN party p ON p.partyId = e.hostPartyId
            ORDER BY e.startTime DESC
            """
        ).fetchall()
        event_rooms = db.execute(
            """
            SELECT er.eventId, er.roomId, er.roomId AS roomLabel, r.roomNumber
            FROM event_room er
            JOIN room r ON r.roomId = er.roomId
            ORDER BY er.eventId, er.roomId
            """
        ).fetchall()
        parties_data = db.execute("SELECT partyId, contactPersonName FROM party ORDER BY contactPersonName").fetchall()
        event_types = db.execute(
            "SELECT DISTINCT eventType FROM event ORDER BY eventType"
        ).fetchall()

        # 仅向前端传递 Available 的房间供分配
        rooms = db.execute(
            "SELECT roomId, roomId AS roomLabel, currentStatus FROM room WHERE currentStatus = 'Available' ORDER BY roomId"
        ).fetchall()
        
        return render_template(
            "events.html",
            events=event_rows,
            event_rooms=event_rooms,
            parties=parties_data,
            event_types=event_types,
            rooms=rooms,
        )

    @app.route("/billing", methods=["GET", "POST"])
    def billing():
        db = get_db()
        if request.method == "POST":
            action = request.form.get("action")
            # 记住当前操作的 account_id 以便跳转回来
            redirect_account_id = request.form.get("accountId", "") 
            try:
                if action == "create_account":
                    account_id = rowmax(db, "billing_account", "accountId")
                    db.execute(
                        "INSERT INTO billing_account (accountId, partyId, status, creditLimit) VALUES (?, ?, ?, ?)",
                        (account_id, request.form["partyId"], request.form["status"], request.form.get("creditLimit") or None),
                    )
                    redirect_account_id = account_id
                elif action == "add_charge":
                    charge_id = rowmax(db, "charge", "chargeId")
                    db.execute(
                        "INSERT INTO charge (chargeId, accountId, stayId, serviceCode, chargeAmount, dateIncurred) VALUES (?, ?, ?, ?, ?, ?)",
                        (charge_id, request.form["accountId"], request.form.get("stayId") or None, 
                         request.form["serviceCode"], request.form["chargeAmount"], request.form["dateIncurred"]),
                    )
                db.commit()
                flash("Billing action completed.", "success")
            except sqlite3.IntegrityError as exc:
                flash(f"Billing action failed: {exc}", "error")
            
            return redirect(url_for("billing", account_id=redirect_account_id))

        # --- GET 逻辑 ---
        accounts = db.execute(
            """
            SELECT ba.accountId, ba.partyId, ba.status, ba.creditLimit, p.contactPersonName, p.partyType
            FROM billing_account ba
            JOIN party p ON p.partyId = ba.partyId
            ORDER BY ba.accountId DESC
            """
        ).fetchall()
        parties_data = db.execute("SELECT partyId, contactPersonName FROM party ORDER BY contactPersonName").fetchall()
        services = db.execute("SELECT serviceCode, serviceType, baseRate FROM service_type ORDER BY serviceCode").fetchall()

        # 选中的账户逻辑
        account_id = request.args.get("account_id")
        selected_account = None
        room_charges = []
        event_charges = []
        other_charges = []
        account_stays = []
        total_due = 0.0

        if account_id:
            selected_account = db.execute(
                "SELECT ba.*, p.contactPersonName, p.partyType FROM billing_account ba JOIN party p ON p.partyId = ba.partyId WHERE ba.accountId = ?", 
                (account_id,)
            ).fetchone()

            if selected_account:
                p_id = selected_account["partyId"]

                # 1. 自动计算 Room Charges (获取该 Party 所有 Reservation 对应的 Stay)
                account_stays = db.execute(
                    """
                    SELECT stayId, reservationId, checkinTime, checkoutTime,
                           roomNumber, baseRate, roomLabel,
                           CAST(
                               MAX(
                                   1,
                                   CAST(stay_days AS INTEGER)
                                   + CASE
                                       WHEN stay_days > CAST(stay_days AS INTEGER) THEN 1
                                       ELSE 0
                                     END
                               ) AS INTEGER
                           ) AS days
                    FROM (
                        SELECT s.stayId, s.reservationId, s.checkinTime, s.checkoutTime,
                               rm.roomNumber, rm.baseRate, ra.roomId AS roomLabel,
                               julianday(COALESCE(s.checkoutTime, datetime('now'))) - julianday(s.checkinTime) AS stay_days
                        FROM stay s
                        JOIN reservation r ON r.reservationId = s.reservationId
                        JOIN room_assignment ra ON ra.reservationId = r.reservationId
                        JOIN room rm ON rm.roomId = ra.roomId
                        WHERE r.partyId = ?
                    )
                    """, (p_id,)
                ).fetchall()

                for s in account_stays:
                    cost = s["days"] * s["baseRate"]
                    room_charges.append({"desc": f"Stay #{s['stayId']} ({s['roomLabel']}) - {s['days']} days", "amount": cost})
                    total_due += cost

                # 2. 自动计算 Event Charges
                events = db.execute("SELECT eventId, eventType FROM event WHERE hostPartyId = ?", (p_id,)).fetchall()
                for e in events:
                    event_cost = 500.0  # 假设一个默认场地费为 $500
                    event_charges.append({"desc": f"Event #{e['eventId']} ({e['eventType']}) Base Fee", "amount": event_cost})
                    total_due += event_cost

                # 3. 其他杂项费用 (Others)
                other_charges = db.execute(
                    """
                    SELECT c.chargeId, c.stayId, st.serviceType, c.chargeAmount, c.dateIncurred
                    FROM charge c
                    JOIN service_type st ON st.serviceCode = c.serviceCode
                    WHERE c.accountId = ?
                    ORDER BY c.dateIncurred DESC
                    """, (account_id,)
                ).fetchall()
                for oc in other_charges:
                    total_due += oc["chargeAmount"]

        return render_template(
            "billing.html",
            accounts=accounts,
            selected_account=selected_account,
            room_charges=room_charges,
            event_charges=event_charges,
            other_charges=other_charges,
            account_stays=account_stays,
            total_due=total_due,
            parties=parties_data,
            services=services,
            today=datetime.now().strftime("%Y-%m-%d"),
        )

    @app.route("/maintenance", methods=["GET", "POST"])
    def maintenance():
        db = get_db()
        if request.method == "POST":
            action = request.form.get("action")
            try:
                if action == "create_ticket":
                    ticket_id = rowmax(db, "maintenance_ticket", "ticketId")
                    status = "Open"
                    db.execute(
                        """
                        INSERT INTO maintenance_ticket (ticketId, roomId, issueDescription, status, dateCreated, dateResolved)
                        VALUES (?, ?, ?, ?, ?, NULL)
                        """,
                        (
                            ticket_id,
                            request.form["roomId"],
                            request.form["issueDescription"],
                            status,
                            request.form["dateCreated"],
                        ),
                    )
                    db.execute(
                        "UPDATE room SET currentStatus = 'Maintenance' WHERE roomId = ?",
                        (request.form["roomId"],),
                    )
                elif action == "update_ticket_status":
                    ticket_id = request.form["ticketId"]
                    status = request.form["status"]
                    if status not in {"Open", "In Progress", "Resolved"}:
                        raise ValueError("Invalid maintenance status.")
                    resolved_on = request.form.get("dateResolved") if status == "Resolved" else None
                    db.execute(
                        """
                        UPDATE maintenance_ticket
                        SET status = ?, dateResolved = ?
                        WHERE ticketId = ? AND LOWER(status) <> 'resolved'
                        """,
                        (status, resolved_on, ticket_id),
                    )
                    ticket = db.execute(
                        "SELECT roomId FROM maintenance_ticket WHERE ticketId = ?", (ticket_id,)
                    ).fetchone()
                    if ticket:
                        if status == "Resolved":
                            open_room_tickets = db.execute(
                                """
                                SELECT COUNT(*) AS cnt
                                FROM maintenance_ticket
                                WHERE roomId = ? AND LOWER(status) <> 'resolved'
                                """,
                                (ticket["roomId"],),
                            ).fetchone()["cnt"]
                            if open_room_tickets == 0:
                                db.execute(
                                    "UPDATE room SET currentStatus = 'Available' WHERE roomId = ?",
                                    (ticket["roomId"],),
                                )
                        else:
                            db.execute(
                                "UPDATE room SET currentStatus = 'Maintenance' WHERE roomId = ?",
                                (ticket["roomId"],),
                            )
                sync_maintenance_room_status(db)
                db.commit()
                flash("Maintenance action completed.", "success")
            except (sqlite3.IntegrityError, ValueError) as exc:
                flash(f"Maintenance action failed: {exc}", "error")
            return redirect(url_for("maintenance"))

        sync_maintenance_room_status(db)
        db.commit()

        tickets = db.execute(
            """
            SELECT mt.ticketId, mt.roomId, mt.roomId AS roomLabel,
                   mt.issueDescription, mt.status, mt.dateCreated, mt.dateResolved
            FROM maintenance_ticket mt
            ORDER BY mt.dateCreated DESC
            """
        ).fetchall()
        unresolved_tickets = db.execute(
            """
            SELECT mt.ticketId, mt.roomId, mt.roomId AS roomLabel,
                   mt.issueDescription, mt.status, mt.dateCreated, mt.dateResolved
            FROM maintenance_ticket mt
            WHERE LOWER(mt.status) <> 'resolved'
            ORDER BY mt.dateCreated DESC
            """
        ).fetchall()
        rooms = db.execute(
            "SELECT roomId, roomId AS roomLabel, currentStatus FROM room ORDER BY roomId"
        ).fetchall()
        return render_template(
            "maintenance.html",
            tickets=tickets,
            unresolved_tickets=unresolved_tickets,
            rooms=rooms,
            today=datetime.now().strftime("%Y-%m-%d"),
        )


app = create_app()


if __name__ == "__main__":
    init_db()
    print("\n  Last Resort: open http://127.0.0.1:5000/  (Flask uses port 5000, not 80)\n")
    app.run(debug=True)
