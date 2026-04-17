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
        date_from = request.args.get("date_from", "")
        date_to = request.args.get("date_to", "")
        building_id = request.args.get("building_id", "")
        wing_id = request.args.get("wing_id", "")
        party_type = request.args.get("party_type", "")

        where_clauses = []
        params: list[Any] = []
        if date_from:
            where_clauses.append("c.dateIncurred >= ?")
            params.append(date_from)
        if date_to:
            where_clauses.append("c.dateIncurred <= ?")
            params.append(date_to)
        charge_where = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        revenue = db.execute(
            f"SELECT COALESCE(SUM(c.chargeAmount), 0) AS total_revenue FROM charge c {charge_where}",
            params,
        ).fetchone()["total_revenue"]

        event_filters = []
        event_params: list[Any] = []
        if date_from:
            event_filters.append("date(e.startTime) >= date(?)")
            event_params.append(date_from)
        if date_to:
            event_filters.append("date(e.endTime) <= date(?)")
            event_params.append(date_to)
        if party_type:
            event_filters.append("p.partyType = ?")
            event_params.append(party_type)
        event_where = f"WHERE {' AND '.join(event_filters)}" if event_filters else ""
        total_events = db.execute(
            f"""
            SELECT COUNT(DISTINCT e.eventId) AS total_events
            FROM event e
            JOIN party p ON p.partyId = e.hostPartyId
            {event_where}
            """,
            event_params,
        ).fetchone()["total_events"]

        stay_filters = ["s.checkoutTime IS NOT NULL"]
        stay_params: list[Any] = []
        if date_from:
            stay_filters.append("date(s.checkinTime) >= date(?)")
            stay_params.append(date_from)
        if date_to:
            stay_filters.append("date(s.checkoutTime) <= date(?)")
            stay_params.append(date_to)
        if party_type:
            stay_filters.append("p.partyType = ?")
            stay_params.append(party_type)
        avg_stay_days = db.execute(
            f"""
            SELECT COALESCE(ROUND(AVG(julianday(s.checkoutTime) - julianday(s.checkinTime)), 2), 0) AS avg_days
            FROM stay s
            JOIN reservation r ON r.reservationId = s.reservationId
            JOIN party p ON p.partyId = r.partyId
            WHERE {' AND '.join(stay_filters)}
            """,
            stay_params,
        ).fetchone()["avg_days"]

        active_assignments = db.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM room_assignment ra
            LEFT JOIN (
                SELECT reservationId, MAX(stayId) AS latest_stay
                FROM stay
                GROUP BY reservationId
            ) ls ON ls.reservationId = ra.reservationId
            LEFT JOIN stay s ON s.stayId = ls.latest_stay
            WHERE s.checkoutTime IS NULL OR s.stayId IS NULL
            """
        ).fetchone()["cnt"]

        open_tickets = db.execute(
            "SELECT COUNT(*) AS cnt FROM maintenance_ticket WHERE lower(status) <> 'resolved'"
        ).fetchone()["cnt"]

        occupancy = db.execute(
            """
            SELECT
                b.buildingName,
                SUM(CASE WHEN lower(r.currentStatus) = 'occupied' THEN 1 ELSE 0 END) AS occupied,
                SUM(CASE WHEN lower(r.currentStatus) <> 'occupied' THEN 1 ELSE 0 END) AS available_or_other
            FROM room r
            JOIN floor f ON f.floorId = r.floorId
            JOIN wing w ON w.wingId = f.wingId
            JOIN building b ON b.buildingId = w.buildingId
            WHERE (? = '' OR b.buildingId = ?) AND (? = '' OR w.wingId = ?)
            GROUP BY b.buildingId, b.buildingName
            ORDER BY b.buildingName
            """,
            (building_id, building_id, wing_id, wing_id),
        ).fetchall()

        buildings = db.execute("SELECT buildingId, buildingName FROM building ORDER BY buildingName").fetchall()
        wings = db.execute("SELECT wingId, wingCode, buildingId FROM wing ORDER BY wingCode").fetchall()
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
            party_types=party_types,
            filters={
                "date_from": date_from,
                "date_to": date_to,
                "building_id": building_id,
                "wing_id": wing_id,
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
                        """
                        UPDATE room
                        SET baseRate = ?, maxCapacity = ?, currentStatus = ?
                        WHERE roomId = ?
                        """,
                        (
                            request.form["baseRate"],
                            request.form["maxCapacity"],
                            request.form["currentStatus"],
                            request.form["roomId"],
                        ),
                    )
                elif action == "add_room_function":
                    db.execute(
                        """
                        INSERT INTO room_function (roomId, functionCode, activeness)
                        VALUES (?, ?, ?)
                        """,
                        (
                            request.form["roomId"],
                            request.form["functionCode"],
                            request.form.get("activeness", "Active"),
                        ),
                    )
                elif action == "add_room_bed":
                    db.execute(
                        """
                        INSERT INTO room_has_bed (roomId, bedTypeId, quantity, isFoldable)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            request.form["roomId"],
                            request.form["bedTypeId"],
                            request.form["quantity"],
                            parse_bool_flag(request.form.get("isFoldable")),
                        ),
                    )
                elif action == "add_adjacency":
                    db.execute(
                        """
                        INSERT INTO room_adjacency (roomId1, roomId2, connectionType)
                        VALUES (?, ?, ?)
                        """,
                        (
                            request.form["roomId1"],
                            request.form["roomId2"],
                            request.form["connectionType"],
                        ),
                    )
                db.commit()
                flash("Inventory updated.", "success")
            except sqlite3.IntegrityError as exc:
                flash(f"Inventory update failed: {exc}", "error")
            return redirect(url_for("inventory"))

        rooms = db.execute(
            """
            SELECT r.roomId, r.roomNumber, r.baseRate, r.maxCapacity, r.currentStatus,
                   f.floorNumber, f.nonSmokingFloor, w.wingCode, b.buildingName
            FROM room r
            JOIN floor f ON f.floorId = r.floorId
            JOIN wing w ON w.wingId = f.wingId
            JOIN building b ON b.buildingId = w.buildingId
            ORDER BY b.buildingName, w.wingCode, f.floorNumber, r.roomNumber
            """
        ).fetchall()
        room_functions = db.execute(
            """
            SELECT rf.roomId, rf.functionCode, fn.functionName, rf.activeness
            FROM room_function rf
            JOIN function fn ON fn.functionCode = rf.functionCode
            ORDER BY rf.roomId, rf.functionCode
            """
        ).fetchall()
        room_beds = db.execute(
            """
            SELECT rb.roomId, bt.name AS bedType, rb.quantity, rb.isFoldable
            FROM room_has_bed rb
            JOIN bed_type bt ON bt.bedTypeId = rb.bedTypeId
            ORDER BY rb.roomId, bt.name
            """
        ).fetchall()
        adjacency = db.execute(
            "SELECT roomId1, roomId2, connectionType FROM room_adjacency ORDER BY roomId1, roomId2"
        ).fetchall()
        functions = db.execute("SELECT functionCode, functionName FROM function ORDER BY functionName").fetchall()
        bed_types = db.execute("SELECT bedTypeId, name FROM bed_type ORDER BY name").fetchall()

        return render_template(
            "inventory.html",
            rooms=rooms,
            room_functions=room_functions,
            room_beds=room_beds,
            adjacency=adjacency,
            functions=functions,
            bed_types=bed_types,
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
        if request.method == "POST":
            action = request.form.get("action")
            try:
                if action == "create_reservation":
                    reservation_id = rowmax(db, "reservation", "reservationId")
                    deposit_required = parse_bool_flag(request.form.get("depositRequired"))
                    deposit_amount = float(request.form.get("depositAmount", "0") or "0")
                    if not deposit_required:
                        deposit_amount = 0.0
                    db.execute(
                        """
                        INSERT INTO reservation
                        (reservationId, partyId, dateCreated, startDate, endDate, status, depositRequired, depositAmount)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            reservation_id,
                            request.form["partyId"],
                            request.form["dateCreated"],
                            request.form["startDate"],
                            request.form["endDate"],
                            request.form["status"],
                            deposit_required,
                            deposit_amount,
                        ),
                    )
                elif action == "update_status":
                    db.execute(
                        "UPDATE reservation SET status = ? WHERE reservationId = ?",
                        (request.form["status"], request.form["reservationId"]),
                    )
                db.commit()
                flash("Reservation saved.", "success")
            except sqlite3.IntegrityError as exc:
                flash(f"Reservation action failed: {exc}", "error")
            return redirect(url_for("reservations"))

        rows = db.execute(
            """
            SELECT r.*, p.contactPersonName, p.partyType,
                   CASE
                       WHEN julianday(r.startDate) - julianday(r.dateCreated) < 7 THEN 'Under 7 days'
                       WHEN julianday(r.startDate) - julianday(r.dateCreated) < 30 THEN '7-29 days'
                       WHEN julianday(r.startDate) - julianday(r.dateCreated) < 90 THEN '30-89 days'
                       ELSE '90+ days'
                   END AS leadTimeGroup
            FROM reservation r
            JOIN party p ON p.partyId = r.partyId
            ORDER BY r.startDate DESC
            """
        ).fetchall()
        parties_data = db.execute(
            "SELECT partyId, contactPersonName, partyType FROM party ORDER BY contactPersonName"
        ).fetchall()
        return render_template("reservations.html", reservations=rows, parties=parties_data)

    @app.route("/assignments", methods=["GET", "POST"])
    def assignments():
        db = get_db()
        if request.method == "POST":
            action = request.form.get("action")
            try:
                if action == "assign_room":
                    room = db.execute(
                        "SELECT currentStatus FROM room WHERE roomId = ?", (request.form["roomId"],)
                    ).fetchone()
                    if room and room["currentStatus"].lower() == "maintenance":
                        flash("Cannot assign room currently under maintenance.", "error")
                        return redirect(url_for("assignments"))

                    assignment_id = rowmax(db, "room_assignment", "assignmentId")
                    db.execute(
                        """
                        INSERT INTO room_assignment (assignmentId, reservationId, roomId, assignmentDate)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            assignment_id,
                            request.form["reservationId"],
                            request.form["roomId"],
                            request.form["assignmentDate"],
                        ),
                    )
                elif action == "checkin":
                    stay_id = rowmax(db, "stay", "stayId")
                    db.execute(
                        "INSERT INTO stay (stayId, reservationId, checkinTime) VALUES (?, ?, ?)",
                        (stay_id, request.form["reservationId"], request.form["checkinTime"]),
                    )
                elif action == "checkout":
                    db.execute(
                        "UPDATE stay SET checkoutTime = ? WHERE stayId = ?",
                        (request.form["checkoutTime"], request.form["stayId"]),
                    )
                db.commit()
                flash("Assignment/Stay action completed.", "success")
            except sqlite3.IntegrityError as exc:
                flash(f"Assignment/Stay action failed: {exc}", "error")
            return redirect(url_for("assignments"))

        assignments_data = db.execute(
            """
            SELECT ra.assignmentId, ra.reservationId, ra.roomId, ra.assignmentDate,
                   rm.roomNumber, rm.currentStatus, p.contactPersonName
            FROM room_assignment ra
            JOIN room rm ON rm.roomId = ra.roomId
            JOIN reservation r ON r.reservationId = ra.reservationId
            JOIN party p ON p.partyId = r.partyId
            ORDER BY ra.assignmentDate DESC
            """
        ).fetchall()
        stays = db.execute(
            """
            SELECT s.stayId, s.reservationId, s.checkinTime, s.checkoutTime,
                   p.contactPersonName
            FROM stay s
            JOIN reservation r ON r.reservationId = s.reservationId
            JOIN party p ON p.partyId = r.partyId
            ORDER BY s.checkinTime DESC
            """
        ).fetchall()
        reservations_data = db.execute(
            """
            SELECT r.reservationId, p.contactPersonName, r.startDate, r.endDate
            FROM reservation r
            JOIN party p ON p.partyId = r.partyId
            ORDER BY r.startDate DESC
            """
        ).fetchall()
        rooms = db.execute(
            "SELECT roomId, roomNumber, currentStatus FROM room ORDER BY roomId"
        ).fetchall()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return render_template(
            "assignments.html",
            assignments=assignments_data,
            stays=stays,
            reservations=reservations_data,
            rooms=rooms,
            now=now,
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
                        INSERT INTO event (eventId, hostPartyId, eventType, startTime, endTime, estimatedGuestCount, usageTime)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            event_id,
                            request.form["hostPartyId"],
                            request.form["eventType"],
                            request.form["startTime"],
                            request.form["endTime"],
                            request.form.get("estimatedGuestCount") or None,
                            request.form.get("usageTime") or None,
                        ),
                    )
                elif action == "add_event_room":
                    db.execute(
                        "INSERT INTO event_room (eventId, roomId) VALUES (?, ?)",
                        (request.form["eventId"], request.form["roomId"]),
                    )
                db.commit()
                flash("Event action completed.", "success")
            except sqlite3.IntegrityError as exc:
                flash(f"Event action failed: {exc}", "error")
            return redirect(url_for("events"))

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
            SELECT er.eventId, er.roomId, r.roomNumber
            FROM event_room er
            JOIN room r ON r.roomId = er.roomId
            ORDER BY er.eventId, er.roomId
            """
        ).fetchall()
        parties_data = db.execute(
            "SELECT partyId, contactPersonName FROM party ORDER BY contactPersonName"
        ).fetchall()
        rooms = db.execute("SELECT roomId, roomNumber FROM room ORDER BY roomNumber").fetchall()
        return render_template(
            "events.html",
            events=event_rows,
            event_rooms=event_rooms,
            parties=parties_data,
            rooms=rooms,
        )

    @app.route("/billing", methods=["GET", "POST"])
    def billing():
        db = get_db()
        if request.method == "POST":
            action = request.form.get("action")
            try:
                if action == "create_account":
                    account_id = rowmax(db, "billing_account", "accountId")
                    db.execute(
                        """
                        INSERT INTO billing_account (accountId, partyId, status, creditLimit)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            account_id,
                            request.form["partyId"],
                            request.form["status"],
                            request.form.get("creditLimit") or None,
                        ),
                    )
                elif action == "add_charge":
                    charge_id = rowmax(db, "charge", "chargeId")
                    db.execute(
                        """
                        INSERT INTO charge (chargeId, accountId, stayId, serviceCode, chargeAmount, dateIncurred)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            charge_id,
                            request.form["accountId"],
                            request.form.get("stayId") or None,
                            request.form["serviceCode"],
                            request.form["chargeAmount"],
                            request.form["dateIncurred"],
                        ),
                    )
                db.commit()
                flash("Billing action completed.", "success")
            except sqlite3.IntegrityError as exc:
                flash(f"Billing action failed: {exc}", "error")
            return redirect(url_for("billing"))

        accounts = db.execute(
            """
            SELECT ba.accountId, ba.partyId, ba.status, ba.creditLimit, p.contactPersonName, p.partyType,
                   COALESCE(SUM(c.chargeAmount), 0) AS totalBilled
            FROM billing_account ba
            JOIN party p ON p.partyId = ba.partyId
            LEFT JOIN charge c ON c.accountId = ba.accountId
            GROUP BY ba.accountId, ba.partyId, ba.status, ba.creditLimit, p.contactPersonName, p.partyType
            ORDER BY ba.accountId DESC
            """
        ).fetchall()
        charges = db.execute(
            """
            SELECT c.chargeId, c.accountId, c.stayId, c.serviceCode, c.chargeAmount, c.dateIncurred,
                   st.serviceType
            FROM charge c
            JOIN service_type st ON st.serviceCode = c.serviceCode
            ORDER BY c.dateIncurred DESC, c.chargeId DESC
            """
        ).fetchall()
        parties_data = db.execute(
            "SELECT partyId, contactPersonName FROM party ORDER BY contactPersonName"
        ).fetchall()
        services = db.execute(
            "SELECT serviceCode, serviceType, baseRate FROM service_type ORDER BY serviceCode"
        ).fetchall()
        stays = db.execute("SELECT stayId, reservationId FROM stay ORDER BY stayId DESC").fetchall()
        return render_template(
            "billing.html",
            accounts=accounts,
            charges=charges,
            parties=parties_data,
            services=services,
            stays=stays,
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
                    db.execute(
                        """
                        INSERT INTO maintenance_ticket (ticketId, roomId, issueDescription, status, dateCreated, dateResolved)
                        VALUES (?, ?, ?, ?, ?, NULL)
                        """,
                        (
                            ticket_id,
                            request.form["roomId"],
                            request.form["issueDescription"],
                            request.form["status"],
                            request.form["dateCreated"],
                        ),
                    )
                    if request.form["status"].lower() == "open":
                        db.execute(
                            "UPDATE room SET currentStatus = 'Maintenance' WHERE roomId = ?",
                            (request.form["roomId"],),
                        )
                elif action == "resolve_ticket":
                    ticket_id = request.form["ticketId"]
                    resolved_on = request.form["dateResolved"]
                    db.execute(
                        """
                        UPDATE maintenance_ticket
                        SET status = 'Resolved', dateResolved = ?
                        WHERE ticketId = ?
                        """,
                        (resolved_on, ticket_id),
                    )
                    ticket = db.execute(
                        "SELECT roomId FROM maintenance_ticket WHERE ticketId = ?", (ticket_id,)
                    ).fetchone()
                    if ticket:
                        db.execute(
                            "UPDATE room SET currentStatus = 'Available' WHERE roomId = ?",
                            (ticket["roomId"],),
                        )
                db.commit()
                flash("Maintenance action completed.", "success")
            except sqlite3.IntegrityError as exc:
                flash(f"Maintenance action failed: {exc}", "error")
            return redirect(url_for("maintenance"))

        tickets = db.execute(
            """
            SELECT mt.ticketId, mt.roomId, mt.issueDescription, mt.status, mt.dateCreated, mt.dateResolved,
                   r.roomNumber, w.wingCode, b.buildingName
            FROM maintenance_ticket mt
            JOIN room r ON r.roomId = mt.roomId
            JOIN floor f ON f.floorId = r.floorId
            JOIN wing w ON w.wingId = f.wingId
            JOIN building b ON b.buildingId = w.buildingId
            ORDER BY mt.dateCreated DESC
            """
        ).fetchall()
        rooms = db.execute("SELECT roomId, roomNumber, currentStatus FROM room ORDER BY roomNumber").fetchall()
        return render_template(
            "maintenance.html",
            tickets=tickets,
            rooms=rooms,
            today=datetime.now().strftime("%Y-%m-%d"),
        )


app = create_app()


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
