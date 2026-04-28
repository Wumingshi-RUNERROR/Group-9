-- Supplementary seed data. Run after Group9_milestone2_create.sql + Group9_milestone2_insert.sql
-- so primary keys do not collide with milestone rows.
PRAGMA foreign_keys = ON;
-- INSERT OR IGNORE: safe to re-run if these rows already exist.

INSERT OR IGNORE INTO hotel (hotelId, hotelName) VALUES
(2, 'Sunset Bay Inn');

INSERT OR IGNORE INTO building (buildingId, hotelId, buildingName) VALUES
(3, 2, 'Main House'),
(4, 2, 'Lakeside Annex');

INSERT OR IGNORE INTO wing (wingId, buildingId, wingCode, nearPool, nearParking, handicapAccess) VALUES
(5, 3, 'E', 1, 1, 1),
(6, 4, 'F', 0, 1, 1);

INSERT OR IGNORE INTO floor (floorId, wingId, floorNumber, nonSmokingFloor) VALUES
(7, 5, 1, 1),
(8, 5, 2, 1),
(9, 6, 1, 0);

INSERT OR IGNORE INTO room (roomId, floorId, roomNumber, baseRate, maxCapacity, currentStatus) VALUES
(11, 7, '201', 175.00, 2, 'Available'),
(12, 7, '202', 185.00, 2, 'Occupied'),
(13, 8, '301', 265.00, 4, 'Available'),
(14, 9, '101', 155.00, 2, 'Available'),
(15, 1, '103', 205.00, 3, 'Available'),
(16, 4, '202', 295.00, 4, 'Maintenance');

INSERT OR IGNORE INTO function (functionCode, functionName) VALUES
('BRK', 'Breakfast Room'),
('GYM', 'Fitness Studio');

INSERT OR IGNORE INTO room_function (roomId, functionCode, activeness) VALUES
(11, 'SLP', 'Active'),
(12, 'SLP', 'Active'),
(13, 'STE', 'Active'),
(13, 'SLP', 'Active'),
(14, 'SLP', 'Active'),
(15, 'SLP', 'Active'),
(16, 'SLP', 'Inactive');

INSERT OR IGNORE INTO bed_type (bedTypeId, name, capacity) VALUES
(5, 'California King', 2),
(6, 'Bunk Bed', 1);

INSERT OR IGNORE INTO room_has_bed (roomId, bedTypeId, quantity, isFoldable) VALUES
(11, 1, 1, 0),
(12, 3, 2, 0),
(13, 2, 1, 0),
(13, 4, 1, 1),
(14, 1, 2, 0),
(15, 2, 1, 0),
(16, 5, 1, 0);

INSERT OR IGNORE INTO room_adjacency (roomId1, roomId2, connectionType) VALUES
(11, 12, 'Connecting Door'),
(13, 14, 'Adjacent'),
(3, 16, 'Staff Corridor');

INSERT OR IGNORE INTO party (partyId, email, phone, partyType, contactPersonName) VALUES
(7, 'grace@travel.org', '555-4001', 'Organization', 'Grace Patel'),
(8, 'henry@example.com', '555-4002', 'Guest', 'Henry O''Neil'),
(9, 'iris@startup.io', '555-4003', 'Organization', 'Iris Kim'),
(10, 'jack@example.com', '555-4004', 'Guest', 'Jack Murphy');

INSERT OR IGNORE INTO guest_group (partyId, guestId, guestName) VALUES
(7, 1, 'Grace Patel'),
(7, 2, 'Sam Patel'),
(8, 1, 'Henry O''Neil'),
(9, 1, 'Iris Kim'),
(9, 2, 'Noah Park'),
(10, 1, 'Jack Murphy'),
(10, 2, 'Kate Murphy');

INSERT OR IGNORE INTO billing_account (accountId, partyId, status, creditLimit) VALUES
(7, 7, 'Open', 3500.00),
(8, 8, 'Open', 1200.00),
(9, 9, 'Open', 6000.00),
(10, 10, 'Open', 900.00);

INSERT OR IGNORE INTO reservation (reservationId, partyId, dateCreated, startDate, endDate, status, depositRequired, depositAmount) VALUES
(9, 7, '2026-04-01', '2026-04-10', '2026-04-12', 'Confirmed', 1, 200.00),
(10, 8, '2026-04-02', '2026-04-15', '2026-04-17', 'Confirmed', 0, 0.00),
(11, 9, '2026-04-05', '2026-04-20', '2026-04-23', 'Confirmed', 1, 400.00),
(12, 10, '2026-04-08', '2026-05-01', '2026-05-04', 'Confirmed', 0, 0.00),
(13, 1, '2026-04-12', '2026-05-10', '2026-05-12', 'Confirmed', 0, 0.00);

INSERT OR IGNORE INTO room_assignment (assignmentId, reservationId, roomId, assignmentDate) VALUES
(11, 9, 11, '2026-04-09'),
(12, 9, 12, '2026-04-09'),
(13, 10, 14, '2026-04-14'),
(14, 11, 13, '2026-04-18'),
(15, 12, 15, '2026-04-30'),
(16, 13, 1, '2026-05-09');

INSERT OR IGNORE INTO stay (stayId, reservationId, checkinTime, checkoutTime) VALUES
(9, 9, '2026-04-10 15:00:00', '2026-04-12 11:00:00'),
(10, 10, '2026-04-15 16:00:00', NULL),
(11, 11, '2026-04-20 14:00:00', '2026-04-23 10:00:00'),
(12, 12, '2026-05-01 17:00:00', NULL),
(13, 13, '2026-05-10 15:30:00', NULL);

INSERT OR IGNORE INTO event (eventId, hostPartyId, eventType, startTime, endTime, estimatedGuestCount, usageTime) VALUES
(5, 7, 'Retreat', '2026-04-11 09:00:00', '2026-04-11 17:00:00', 40, 'Full day'),
(6, 9, 'Product Launch', '2026-04-21 10:00:00', '2026-04-21 16:00:00', 60, 'Morning');

INSERT OR IGNORE INTO event_room (eventId, roomId) VALUES
(5, 11),
(5, 12),
(6, 13);

INSERT OR IGNORE INTO service_type (serviceCode, serviceType, baseRate) VALUES
(7, 'Parking', 18.00),
(8, 'Room Service', 35.00);

INSERT OR IGNORE INTO charge (chargeId, accountId, stayId, serviceCode, chargeAmount, dateIncurred) VALUES
(23, 7, 9, 1, 370.00, '2026-04-10'),
(24, 7, 9, 8, 62.00, '2026-04-11'),
(25, 8, 10, 1, 310.00, '2026-04-15'),
(26, 8, 10, 7, 36.00, '2026-04-16'),
(27, 9, 11, 2, 795.00, '2026-04-20'),
(28, 9, 11, 3, 140.00, '2026-04-21'),
(29, 10, 12, 1, 615.00, '2026-05-01'),
(30, 1, 13, 1, 360.00, '2026-05-10'),
(31, 1, 13, 5, 40.00, '2026-05-11');

INSERT OR IGNORE INTO maintenance_ticket (ticketId, roomId, issueDescription, status, dateCreated, dateResolved) VALUES
(6, 11, 'Window seal draft', 'Open', '2026-04-08', NULL),
(7, 14, 'Smoke detector battery', 'Resolved', '2026-04-03', '2026-04-04'),
(8, 16, 'HVAC noise (follow-up)', 'Open', '2026-04-20', NULL);
