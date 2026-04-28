-- migrate_room_ids.sql
-- Converts room.roomId (and all FK columns) from INTEGER to TEXT labels like "OT-A-101".
-- New ID = <building-initials>-<wingCode>-<roomNumber>
-- Run once against an existing last_resort.db that still has integer roomIds.
--
--   sqlite3 last_resort.db < migrate_room_ids.sql
--
-- Safe to run whether or not insert.sql has been applied (rooms 11-16 are handled).
PRAGMA foreign_keys = OFF;
BEGIN;

-- ────────────────────────────────────────────────────────────────────
-- Helper view: compute new TEXT roomId from building/wing/room data
-- ────────────────────────────────────────────────────────────────────
CREATE TEMPORARY VIEW _room_label AS
SELECT
    r.roomId AS old_id,
    CASE
        WHEN b.buildingName = 'Ocean Tower'    THEN 'OT'
        WHEN b.buildingName = 'Garden Lodge'   THEN 'GL'
        WHEN b.buildingName = 'Main House'     THEN 'MH'
        WHEN b.buildingName = 'Lakeside Annex' THEN 'LA'
        ELSE UPPER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
             REPLACE(REPLACE(REPLACE(REPLACE(b.buildingName,
             'a',''),'e',''),'i',''),'o',''),'u',''),
             'A',''),'E',''),'I',''),'O',''))
    END || '-' || w.wingCode || '-' || r.roomNumber AS new_id
FROM room r
JOIN floor  f ON f.floorId    = r.floorId
JOIN wing   w ON w.wingId     = f.wingId
JOIN building b ON b.buildingId = w.buildingId;

-- ────────────────────────────────────────────────────────────────────
-- 1. room  (TEXT PK)
-- ────────────────────────────────────────────────────────────────────
CREATE TABLE room_v2 (
    roomId        TEXT NOT NULL PRIMARY KEY,
    floorId       INTEGER NOT NULL,
    roomNumber    TEXT NOT NULL,
    baseRate      REAL NOT NULL,
    maxCapacity   INTEGER NOT NULL,
    currentStatus TEXT NOT NULL,
    FOREIGN KEY (floorId) REFERENCES floor(floorId),
    UNIQUE (floorId, roomNumber)
);
INSERT INTO room_v2
SELECT m.new_id, r.floorId, r.roomNumber, r.baseRate, r.maxCapacity, r.currentStatus
FROM room r
JOIN _room_label m ON m.old_id = r.roomId;

-- ────────────────────────────────────────────────────────────────────
-- 2. room_function
-- ────────────────────────────────────────────────────────────────────
CREATE TABLE room_function_v2 (
    roomId       TEXT NOT NULL,
    functionCode TEXT NOT NULL,
    activeness   TEXT,
    PRIMARY KEY (roomId, functionCode),
    FOREIGN KEY (roomId)       REFERENCES room(roomId),
    FOREIGN KEY (functionCode) REFERENCES function(functionCode)
);
INSERT INTO room_function_v2
SELECT m.new_id, rf.functionCode, rf.activeness
FROM room_function rf
JOIN _room_label m ON m.old_id = rf.roomId;

-- ────────────────────────────────────────────────────────────────────
-- 3. room_has_bed
-- ────────────────────────────────────────────────────────────────────
CREATE TABLE room_has_bed_v2 (
    roomId    TEXT NOT NULL,
    bedTypeId INTEGER NOT NULL,
    quantity  INTEGER NOT NULL CHECK (quantity >= 0),
    isFoldable INTEGER NOT NULL CHECK (isFoldable IN (0,1)),
    PRIMARY KEY (roomId, bedTypeId),
    FOREIGN KEY (roomId)    REFERENCES room(roomId),
    FOREIGN KEY (bedTypeId) REFERENCES bed_type(bedTypeId)
);
INSERT INTO room_has_bed_v2
SELECT m.new_id, rb.bedTypeId, rb.quantity, rb.isFoldable
FROM room_has_bed rb
JOIN _room_label m ON m.old_id = rb.roomId;

-- ────────────────────────────────────────────────────────────────────
-- 4. room_adjacency
-- ────────────────────────────────────────────────────────────────────
CREATE TABLE room_adjacency_v2 (
    roomId1        TEXT NOT NULL,
    roomId2        TEXT NOT NULL,
    connectionType TEXT NOT NULL,
    PRIMARY KEY (roomId1, roomId2),
    FOREIGN KEY (roomId1) REFERENCES room(roomId),
    FOREIGN KEY (roomId2) REFERENCES room(roomId),
    CHECK (roomId1 <> roomId2)
);
INSERT INTO room_adjacency_v2
SELECT m1.new_id, m2.new_id, ra.connectionType
FROM room_adjacency ra
JOIN _room_label m1 ON m1.old_id = ra.roomId1
JOIN _room_label m2 ON m2.old_id = ra.roomId2;

-- ────────────────────────────────────────────────────────────────────
-- 5. room_assignment
-- ────────────────────────────────────────────────────────────────────
CREATE TABLE room_assignment_v2 (
    assignmentId   INTEGER PRIMARY KEY,
    reservationId  INTEGER NOT NULL,
    roomId         TEXT NOT NULL,
    assignmentDate TEXT NOT NULL,
    FOREIGN KEY (reservationId) REFERENCES reservation(reservationId),
    FOREIGN KEY (roomId)        REFERENCES room(roomId)
);
INSERT INTO room_assignment_v2
SELECT ra.assignmentId, ra.reservationId, m.new_id, ra.assignmentDate
FROM room_assignment ra
JOIN _room_label m ON m.old_id = ra.roomId;

-- ────────────────────────────────────────────────────────────────────
-- 6. event_room
-- ────────────────────────────────────────────────────────────────────
CREATE TABLE event_room_v2 (
    eventId INTEGER NOT NULL,
    roomId  TEXT NOT NULL,
    PRIMARY KEY (eventId, roomId),
    FOREIGN KEY (eventId) REFERENCES event(eventId),
    FOREIGN KEY (roomId)  REFERENCES room(roomId)
);
INSERT INTO event_room_v2
SELECT er.eventId, m.new_id
FROM event_room er
JOIN _room_label m ON m.old_id = er.roomId;

-- ────────────────────────────────────────────────────────────────────
-- 7. maintenance_ticket
-- ────────────────────────────────────────────────────────────────────
CREATE TABLE maintenance_ticket_v2 (
    ticketId         INTEGER PRIMARY KEY,
    roomId           TEXT NOT NULL,
    issueDescription TEXT NOT NULL,
    status           TEXT NOT NULL,
    dateCreated      TEXT NOT NULL,
    dateResolved     TEXT,
    FOREIGN KEY (roomId) REFERENCES room(roomId),
    CHECK (dateResolved IS NULL OR julianday(dateResolved) >= julianday(dateCreated))
);
INSERT INTO maintenance_ticket_v2
SELECT mt.ticketId, m.new_id, mt.issueDescription, mt.status, mt.dateCreated, mt.dateResolved
FROM maintenance_ticket mt
JOIN _room_label m ON m.old_id = mt.roomId;

-- ────────────────────────────────────────────────────────────────────
-- Drop old tables, rename new ones
-- ────────────────────────────────────────────────────────────────────
DROP TABLE maintenance_ticket;
DROP TABLE event_room;
DROP TABLE room_assignment;
DROP TABLE room_adjacency;
DROP TABLE room_has_bed;
DROP TABLE room_function;
DROP TABLE room;

ALTER TABLE room_v2              RENAME TO room;
ALTER TABLE room_function_v2     RENAME TO room_function;
ALTER TABLE room_has_bed_v2      RENAME TO room_has_bed;
ALTER TABLE room_adjacency_v2    RENAME TO room_adjacency;
ALTER TABLE room_assignment_v2   RENAME TO room_assignment;
ALTER TABLE event_room_v2        RENAME TO event_room;
ALTER TABLE maintenance_ticket_v2 RENAME TO maintenance_ticket;

COMMIT;
PRAGMA foreign_keys = ON;

-- Verify
SELECT 'room rows'              , COUNT(*) FROM room;
SELECT 'room_function rows'     , COUNT(*) FROM room_function;
SELECT 'room_has_bed rows'      , COUNT(*) FROM room_has_bed;
SELECT 'room_adjacency rows'    , COUNT(*) FROM room_adjacency;
SELECT 'room_assignment rows'   , COUNT(*) FROM room_assignment;
SELECT 'event_room rows'        , COUNT(*) FROM event_room;
SELECT 'maintenance_ticket rows', COUNT(*) FROM maintenance_ticket;
SELECT 'sample roomIds', roomId FROM room ORDER BY roomId;
