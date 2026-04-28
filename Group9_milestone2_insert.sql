PRAGMA foreign_keys = ON;
-- INSERT OR IGNORE: safe to re-run when last_resort.db already has seed rows (avoids UNIQUE/PK errors).

INSERT OR IGNORE INTO hotel (hotelId, hotelName) VALUES
(1, 'Last Resort Hotel');

INSERT OR IGNORE INTO building (buildingId, hotelId, buildingName) VALUES
(1, 1, 'Ocean Tower'),
(2, 1, 'Garden Lodge');

INSERT OR IGNORE INTO wing (wingId, buildingId, wingCode, nearPool, nearParking, handicapAccess) VALUES
(1, 1, 'A', 1, 1, 1),
(2, 1, 'B', 0, 1, 1),
(3, 2, 'A', 1, 0, 1),
(4, 2, 'B', 0, 1, 0);

INSERT OR IGNORE INTO floor (floorId, wingId, floorNumber, nonSmokingFloor) VALUES
(1, 1, 1, 1),
(2, 1, 2, 1),
(3, 2, 1, 0),
(4, 2, 2, 1),
(5, 3, 1, 1),
(6, 4, 1, 0);

INSERT OR IGNORE INTO room (roomId, floorId, roomNumber, baseRate, maxCapacity, currentStatus) VALUES
('OT-A-101', 1, '101', 180.00, 2, 'Available'),
('OT-A-102', 1, '102', 220.00, 4, 'Occupied'),
('OT-A-201', 2, '201', 250.00, 3, 'Available'),
('OT-B-101', 3, '101', 300.00, 6, 'Available'),
('OT-B-102', 3, '102', 320.00, 8, 'Maintenance'),
('OT-B-201', 4, '201', 280.00, 4, 'Occupied'),
('GL-A-101', 5, '101', 190.00, 2, 'Available'),
('GL-A-102', 5, '102', 210.00, 3, 'Occupied'),
('GL-B-101', 6, '101', 400.00, 10, 'Available'),
('GL-B-102', 6, '102', 450.00, 12, 'Available');

INSERT OR IGNORE INTO function (functionCode, functionName) VALUES
('SLP', 'Sleeping Room'),
('MTG', 'Meeting Room'),
('STE', 'Suite');

INSERT OR IGNORE INTO room_function (roomId, functionCode, activeness) VALUES
('OT-A-101', 'SLP', 'Active'),
('OT-A-102', 'SLP', 'Active'),
('OT-A-201', 'SLP', 'Active'),
('OT-A-201', 'STE', 'Active'),
('OT-B-101', 'MTG', 'Active'),
('OT-B-102', 'MTG', 'Inactive'),
('OT-B-201', 'SLP', 'Active'),
('GL-A-101', 'SLP', 'Active'),
('GL-A-102', 'SLP', 'Active'),
('GL-B-101', 'MTG', 'Active'),
('GL-B-102', 'MTG', 'Active');

INSERT OR IGNORE INTO bed_type (bedTypeId, name, capacity) VALUES
(1, 'Queen', 2),
(2, 'King', 2),
(3, 'Twin', 1),
(4, 'Sofa Bed', 1);

INSERT OR IGNORE INTO room_has_bed (roomId, bedTypeId, quantity, isFoldable) VALUES
('OT-A-101', 1, 1, 0),
('OT-A-102', 1, 2, 0),
('OT-A-201', 2, 1, 0),
('OT-A-201', 4, 1, 1),
('OT-B-201', 3, 2, 0),
('GL-A-101', 1, 1, 0),
('GL-A-102', 2, 1, 0),
('GL-A-102', 4, 1, 1);

INSERT OR IGNORE INTO room_adjacency (roomId1, roomId2, connectionType) VALUES
('OT-A-101', 'OT-A-102', 'Connecting Door'),
('OT-A-102', 'OT-A-201', 'Adjacent'),
('OT-B-101', 'OT-B-102', 'Movable Wall'),
('GL-B-101', 'GL-B-102', 'Partition');

INSERT OR IGNORE INTO party (partyId, email, phone, partyType, contactPersonName) VALUES
(1, 'alice@example.com', '555-1001', 'Guest', 'Alice Chen'),
(2, 'bob@example.com', '555-1002', 'Guest', 'Bob Li'),
(3, 'carol@acme.com', '555-2001', 'Organization', 'Carol Wong'),
(4, 'david@globex.com', '555-2002', 'Organization', 'David Smith'),
(5, 'eva@example.com', '555-1003', 'Guest', 'Eva Zhang'),
(6, 'frank@eventco.com', '555-3001', 'Organization', 'Frank Brown');

INSERT OR IGNORE INTO guest_group (partyId, guestId, guestName) VALUES
(1, 1, 'Alice Chen'),
(2, 1, 'Bob Li'),
(3, 1, 'Carol Wong'),
(3, 2, 'Jason Wong'),
(4, 1, 'David Smith'),
(4, 2, 'Helen Smith'),
(5, 1, 'Eva Zhang'),
(6, 1, 'Frank Brown'),
(6, 2, 'Mia Brown'),
(6, 3, 'Lucas Brown');

INSERT OR IGNORE INTO billing_account (accountId, partyId, status, creditLimit) VALUES
(1, 1, 'Open', 1000.00),
(2, 2, 'Open', 1500.00),
(3, 3, 'Open', 5000.00),
(4, 4, 'Open', 7000.00),
(5, 5, 'Closed', 800.00),
(6, 6, 'Open', 9000.00);

INSERT OR IGNORE INTO reservation (reservationId, partyId, dateCreated, startDate, endDate, status, depositRequired, depositAmount) VALUES
(1, 1, '2026-01-02', '2026-01-10', '2026-01-13', 'Confirmed', 0, 0.00),
(2, 2, '2026-01-05', '2026-02-01', '2026-02-04', 'Confirmed', 1, 100.00),
(3, 3, '2025-11-15', '2026-01-20', '2026-01-23', 'Confirmed', 1, 500.00),
(4, 4, '2025-12-01', '2026-02-10', '2026-02-15', 'Confirmed', 1, 800.00),
(5, 5, '2026-02-25', '2026-03-01', '2026-03-03', 'Completed', 0, 0.00),
(6, 6, '2025-10-10', '2026-03-15', '2026-03-18', 'Confirmed', 1, 1200.00),
(7, 3, '2026-03-01', '2026-03-20', '2026-03-22', 'Confirmed', 0, 0.00),
(8, 1, '2026-03-18', '2026-03-25', '2026-03-27', 'Confirmed', 0, 0.00);

INSERT OR IGNORE INTO room_assignment (assignmentId, reservationId, roomId, assignmentDate) VALUES
(1, 1, 'OT-A-101', '2026-01-09'),
(2, 2, 'OT-A-102', '2026-01-31'),
(3, 3, 'OT-B-101', '2026-01-18'),
(4, 4, 'OT-B-201', '2026-02-08'),
(5, 5, 'GL-A-101', '2026-02-28'),
(6, 6, 'GL-B-101', '2026-03-12'),
(7, 7, 'GL-B-102', '2026-03-18'),
(8, 8, 'OT-A-201', '2026-03-24'),
(10, 6, 'GL-B-102', '2026-03-13');

INSERT OR IGNORE INTO stay (stayId, reservationId, checkinTime, checkoutTime) VALUES
(1, 1, '2026-01-10 16:00:00', '2026-01-13 10:00:00'),
(2, 2, '2026-02-01 16:00:00', '2026-02-04 11:00:00'),
(3, 3, '2026-01-20 08:00:00', '2026-01-23 18:00:00'),
(4, 4, '2026-02-10 14:00:00', '2026-02-15 22:00:00'),
(5, 5, '2026-03-01 16:00:00', '2026-03-03 11:30:00'),
(6, 6, '2026-03-15 08:00:00', '2026-03-18 17:00:00'),
(7, 8, '2026-03-25 16:00:00', '2026-03-27 10:00:00'),
(8, 7, '2026-03-20 15:00:00', '2026-03-22 12:00:00');

INSERT OR IGNORE INTO event (eventId, hostPartyId, eventType, startTime, endTime, estimatedGuestCount, usageTime) VALUES
(1, 3, 'Conference', '2026-01-20 09:00:00', '2026-01-22 18:00:00', 120, 'Morning'),
(2, 4, 'Wedding', '2026-02-11 14:00:00', '2026-02-11 22:00:00', 200, 'Evening'),
(3, 6, 'Seminar', '2026-03-16 08:00:00', '2026-03-17 17:00:00', 80, 'Afternoon'),
(4, 3, 'Banquet', '2026-03-21 18:00:00', '2026-03-21 23:00:00', 150, 'Supper');

INSERT OR IGNORE INTO event_room (eventId, roomId) VALUES
(1, 'OT-B-101'),
(1, 'OT-B-102'),
(2, 'GL-B-101'),
(2, 'GL-B-102'),
(3, 'GL-B-101'),
(4, 'GL-B-102');

INSERT OR IGNORE INTO service_type (serviceCode, serviceType, baseRate) VALUES
(1, 'Sleeping Room', 200.00),
(2, 'Meeting Room Rental', 500.00),
(3, 'Restaurant', 80.00),
(4, 'Business Service', 40.00),
(5, 'Laundry', 20.00),
(6, 'Spa', 120.00);

INSERT OR IGNORE INTO charge (chargeId, accountId, stayId, serviceCode, chargeAmount, dateIncurred) VALUES
(1, 1, 1, 1, 540.00, '2026-01-10'),
(2, 1, 1, 3, 95.00, '2026-01-11'),
(3, 1, 1, 5, 25.00, '2026-01-12'),

(4, 2, 2, 1, 660.00, '2026-02-01'),
(5, 2, 2, 3, 120.00, '2026-02-02'),
(6, 2, 2, 4, 60.00, '2026-02-03'),

(7, 3, 3, 2, 1200.00, '2026-01-20'),
(8, 3, 3, 3, 300.00, '2026-01-21'),
(9, 3, 3, 4, 150.00, '2026-01-22'),

(10, 4, 4, 1, 1400.00, '2026-02-10'),
(11, 4, 4, 2, 2000.00, '2026-02-11'),
(12, 4, 4, 6, 220.00, '2026-02-12'),

(13, 5, 5, 1, 380.00, '2026-03-01'),
(14, 5, 5, 3, 85.00, '2026-03-02'),

(15, 6, 6, 2, 1800.00, '2026-03-15'),
(16, 6, 6, 4, 210.00, '2026-03-16'),
(17, 6, 6, 3, 260.00, '2026-03-17'),
(18, 6, 6, 6, 150.00, '2026-03-17'),

(19, 3, 8, 2, 900.00, '2026-03-21'),
(20, 3, 8, 3, 450.00, '2026-03-21'),

(21, 1, 7, 1, 500.00, '2026-03-25'),
(22, 1, 7, 5, 20.00, '2026-03-26');

INSERT OR IGNORE INTO maintenance_ticket (ticketId, roomId, issueDescription, status, dateCreated, dateResolved) VALUES
(1, 'OT-B-102', 'Projector malfunction', 'Resolved', '2026-01-10', '2026-01-12'),
(2, 'OT-A-102', 'Air conditioning issue', 'Resolved', '2026-02-01', '2026-02-03'),
(3, 'GL-A-102', 'Bathroom leak', 'Resolved', '2026-02-14', '2026-02-18'),
(4, 'GL-B-101', 'Lighting replacement', 'Resolved', '2026-03-05', '2026-03-06'),
(5, 'GL-B-102', 'Wall partition repair', 'Open', '2026-03-22', NULL);
