-- migrate_wing_codes.sql
-- Makes each building's wings start from A:
--   Garden Lodge:   C→A, D→B  (roomIds GL-C-* → GL-A-*, GL-D-* → GL-B-*)
--   Main House:     E→A        (roomIds MH-E-* → MH-A-*)
--   Lakeside Annex: F→A        (roomIds LA-F-* → LA-A-*)
-- Also adds Wing B for Main House and Lakeside Annex, each with a floor and sample rooms.
--
--   sqlite3 last_resort.db < migrate_wing_codes.sql

PRAGMA foreign_keys = OFF;
BEGIN;

-- ── 1. Fix wing codes ─────────────────────────────────────────────────────────
UPDATE wing SET wingCode = 'A' WHERE wingId = 3;   -- Garden Lodge C → A
UPDATE wing SET wingCode = 'B' WHERE wingId = 4;   -- Garden Lodge D → B
UPDATE wing SET wingCode = 'A' WHERE wingId = 5;   -- Main House   E → A
UPDATE wing SET wingCode = 'A' WHERE wingId = 6;   -- Lakeside Annex F → A

-- ── 2. Add Wing B for Main House and Lakeside Annex ──────────────────────────
INSERT OR IGNORE INTO wing (wingId, buildingId, wingCode, nearPool, nearParking, handicapAccess) VALUES
(7, 3, 'B', 0, 1, 1),   -- Main House Wing B
(8, 4, 'B', 1, 0, 0);   -- Lakeside Annex Wing B

-- ── 3. Add floors for new wings ───────────────────────────────────────────────
INSERT OR IGNORE INTO floor (floorId, wingId, floorNumber, nonSmokingFloor) VALUES
(10, 7, 1, 1),   -- MH-B, Floor 1
(11, 8, 1, 0);   -- LA-B, Floor 1

-- ── 4. Rename room IDs ────────────────────────────────────────────────────────
UPDATE room SET roomId = 'GL-A-101' WHERE roomId = 'GL-C-101';
UPDATE room SET roomId = 'GL-A-102' WHERE roomId = 'GL-C-102';
UPDATE room SET roomId = 'GL-B-101' WHERE roomId = 'GL-D-101';
UPDATE room SET roomId = 'GL-B-102' WHERE roomId = 'GL-D-102';
UPDATE room SET roomId = 'MH-A-201' WHERE roomId = 'MH-E-201';
UPDATE room SET roomId = 'MH-A-202' WHERE roomId = 'MH-E-202';
UPDATE room SET roomId = 'MH-A-301' WHERE roomId = 'MH-E-301';
UPDATE room SET roomId = 'LA-A-101' WHERE roomId = 'LA-F-101';

-- ── 5. Add new rooms in the new wings ─────────────────────────────────────────
INSERT OR IGNORE INTO room (roomId, floorId, roomNumber, baseRate, maxCapacity, currentStatus) VALUES
('MH-B-101', 10, '101', 160.00, 2, 'Available'),
('MH-B-102', 10, '102', 170.00, 3, 'Available'),
('LA-B-101', 11, '101', 145.00, 2, 'Available'),
('LA-B-102', 11, '102', 155.00, 2, 'Available');

-- ── 6. Cascade room ID rename to all FK tables ────────────────────────────────

-- room_function
UPDATE room_function SET roomId = 'GL-A-101' WHERE roomId = 'GL-C-101';
UPDATE room_function SET roomId = 'GL-A-102' WHERE roomId = 'GL-C-102';
UPDATE room_function SET roomId = 'GL-B-101' WHERE roomId = 'GL-D-101';
UPDATE room_function SET roomId = 'GL-B-102' WHERE roomId = 'GL-D-102';
UPDATE room_function SET roomId = 'MH-A-201' WHERE roomId = 'MH-E-201';
UPDATE room_function SET roomId = 'MH-A-202' WHERE roomId = 'MH-E-202';
UPDATE room_function SET roomId = 'MH-A-301' WHERE roomId = 'MH-E-301';
UPDATE room_function SET roomId = 'LA-A-101' WHERE roomId = 'LA-F-101';

-- room_has_bed
UPDATE room_has_bed SET roomId = 'GL-A-101' WHERE roomId = 'GL-C-101';
UPDATE room_has_bed SET roomId = 'GL-A-102' WHERE roomId = 'GL-C-102';
UPDATE room_has_bed SET roomId = 'GL-B-101' WHERE roomId = 'GL-D-101';
UPDATE room_has_bed SET roomId = 'GL-B-102' WHERE roomId = 'GL-D-102';
UPDATE room_has_bed SET roomId = 'MH-A-201' WHERE roomId = 'MH-E-201';
UPDATE room_has_bed SET roomId = 'MH-A-202' WHERE roomId = 'MH-E-202';
UPDATE room_has_bed SET roomId = 'MH-A-301' WHERE roomId = 'MH-E-301';
UPDATE room_has_bed SET roomId = 'LA-A-101' WHERE roomId = 'LA-F-101';

-- room_adjacency (two FK columns)
UPDATE room_adjacency SET roomId1 = 'GL-A-101' WHERE roomId1 = 'GL-C-101';
UPDATE room_adjacency SET roomId1 = 'GL-A-102' WHERE roomId1 = 'GL-C-102';
UPDATE room_adjacency SET roomId1 = 'GL-B-101' WHERE roomId1 = 'GL-D-101';
UPDATE room_adjacency SET roomId1 = 'GL-B-102' WHERE roomId1 = 'GL-D-102';
UPDATE room_adjacency SET roomId1 = 'MH-A-201' WHERE roomId1 = 'MH-E-201';
UPDATE room_adjacency SET roomId1 = 'MH-A-202' WHERE roomId1 = 'MH-E-202';
UPDATE room_adjacency SET roomId1 = 'MH-A-301' WHERE roomId1 = 'MH-E-301';
UPDATE room_adjacency SET roomId1 = 'LA-A-101' WHERE roomId1 = 'LA-F-101';

UPDATE room_adjacency SET roomId2 = 'GL-A-101' WHERE roomId2 = 'GL-C-101';
UPDATE room_adjacency SET roomId2 = 'GL-A-102' WHERE roomId2 = 'GL-C-102';
UPDATE room_adjacency SET roomId2 = 'GL-B-101' WHERE roomId2 = 'GL-D-101';
UPDATE room_adjacency SET roomId2 = 'GL-B-102' WHERE roomId2 = 'GL-D-102';
UPDATE room_adjacency SET roomId2 = 'MH-A-201' WHERE roomId2 = 'MH-E-201';
UPDATE room_adjacency SET roomId2 = 'MH-A-202' WHERE roomId2 = 'MH-E-202';
UPDATE room_adjacency SET roomId2 = 'MH-A-301' WHERE roomId2 = 'MH-E-301';
UPDATE room_adjacency SET roomId2 = 'LA-A-101' WHERE roomId2 = 'LA-F-101';

-- room_assignment
UPDATE room_assignment SET roomId = 'GL-A-101' WHERE roomId = 'GL-C-101';
UPDATE room_assignment SET roomId = 'GL-A-102' WHERE roomId = 'GL-C-102';
UPDATE room_assignment SET roomId = 'GL-B-101' WHERE roomId = 'GL-D-101';
UPDATE room_assignment SET roomId = 'GL-B-102' WHERE roomId = 'GL-D-102';
UPDATE room_assignment SET roomId = 'MH-A-201' WHERE roomId = 'MH-E-201';
UPDATE room_assignment SET roomId = 'MH-A-202' WHERE roomId = 'MH-E-202';
UPDATE room_assignment SET roomId = 'MH-A-301' WHERE roomId = 'MH-E-301';
UPDATE room_assignment SET roomId = 'LA-A-101' WHERE roomId = 'LA-F-101';

-- event_room
UPDATE event_room SET roomId = 'GL-A-101' WHERE roomId = 'GL-C-101';
UPDATE event_room SET roomId = 'GL-A-102' WHERE roomId = 'GL-C-102';
UPDATE event_room SET roomId = 'GL-B-101' WHERE roomId = 'GL-D-101';
UPDATE event_room SET roomId = 'GL-B-102' WHERE roomId = 'GL-D-102';
UPDATE event_room SET roomId = 'MH-A-201' WHERE roomId = 'MH-E-201';
UPDATE event_room SET roomId = 'MH-A-202' WHERE roomId = 'MH-E-202';
UPDATE event_room SET roomId = 'MH-A-301' WHERE roomId = 'MH-E-301';
UPDATE event_room SET roomId = 'LA-A-101' WHERE roomId = 'LA-F-101';

-- maintenance_ticket
UPDATE maintenance_ticket SET roomId = 'GL-A-101' WHERE roomId = 'GL-C-101';
UPDATE maintenance_ticket SET roomId = 'GL-A-102' WHERE roomId = 'GL-C-102';
UPDATE maintenance_ticket SET roomId = 'GL-B-101' WHERE roomId = 'GL-D-101';
UPDATE maintenance_ticket SET roomId = 'GL-B-102' WHERE roomId = 'GL-D-102';
UPDATE maintenance_ticket SET roomId = 'MH-A-201' WHERE roomId = 'MH-E-201';
UPDATE maintenance_ticket SET roomId = 'MH-A-202' WHERE roomId = 'MH-E-202';
UPDATE maintenance_ticket SET roomId = 'MH-A-301' WHERE roomId = 'MH-E-301';
UPDATE maintenance_ticket SET roomId = 'LA-A-101' WHERE roomId = 'LA-F-101';

-- ── 7. Functions and beds for new rooms ───────────────────────────────────────
INSERT OR IGNORE INTO room_function (roomId, functionCode, activeness) VALUES
('MH-B-101', 'SLP', 'Active'),
('MH-B-102', 'SLP', 'Active'),
('LA-B-101', 'SLP', 'Active'),
('LA-B-102', 'SLP', 'Active');

INSERT OR IGNORE INTO room_has_bed (roomId, bedTypeId, quantity, isFoldable) VALUES
('MH-B-101', 1, 1, 0),
('MH-B-102', 1, 2, 0),
('LA-B-101', 2, 1, 0),
('LA-B-102', 1, 1, 0);

INSERT OR IGNORE INTO room_adjacency (roomId1, roomId2, connectionType) VALUES
('MH-B-101', 'MH-B-102', 'Connecting Door'),
('LA-B-101', 'LA-B-102', 'Adjacent');

COMMIT;
PRAGMA foreign_keys = ON;

-- Verify
SELECT 'wings after rename' AS info, wingId, buildingId, wingCode FROM wing ORDER BY buildingId, wingCode;
SELECT 'sample room IDs'   AS info, roomId FROM room ORDER BY roomId;
