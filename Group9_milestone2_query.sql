-- 1. Room Usage by Building and Wing
SELECT
    b.buildingName AS building_name,
    w.wingCode AS wing_code,
    COUNT(DISTINCT ra.assignmentId) AS total_assignments
FROM room_assignment AS ra
JOIN room AS r
    ON ra.roomId = r.roomId
JOIN floor AS f
    ON r.floorId = f.floorId
JOIN wing AS w
    ON f.wingId = w.wingId
JOIN building AS b
    ON w.buildingId = b.buildingId
GROUP BY
    b.buildingName,
    w.wingCode
ORDER BY
    total_assignments DESC;

-- 2. Average Actual Usage Duration by Party Type
SELECT
    p.partyType AS party_type,
    ROUND(AVG(julianday(s.checkoutTime) - julianday(s.checkinTime)), 2) AS avg_usage_days,
    COUNT(DISTINCT s.stayId) AS total_stays
FROM stay AS s
JOIN reservation AS res
    ON s.reservationId = res.reservationId
JOIN party AS p
    ON res.partyId = p.partyId
GROUP BY
    p.partyType
ORDER BY
    avg_usage_days DESC;

-- 3. Reservation Lead Time and Deposit Pattern
SELECT
    CASE
        WHEN julianday(startDate) - julianday(dateCreated) < 7 THEN 'Under 7 days'
        WHEN julianday(startDate) - julianday(dateCreated) < 30 THEN '7-29 days'
        WHEN julianday(startDate) - julianday(dateCreated) < 90 THEN '30-89 days'
        ELSE '90+ days'
    END AS lead_time_group,
    COUNT(*) AS reservation_count,
    SUM(CASE WHEN depositRequired = 1 THEN 1 ELSE 0 END) AS reservations_with_deposit,
    ROUND(AVG(depositAmount), 2) AS avg_deposit_amount
FROM reservation
GROUP BY
    lead_time_group
ORDER BY
    reservation_count DESC;

-- 4. Most Common Bed Configurations in Assigned Rooms
SELECT
    bt.name AS bed_type,
    SUM(rhb.quantity) AS total_beds_in_assigned_rooms,
    COUNT(DISTINCT r.roomId) AS rooms_with_this_bed_type
FROM room_assignment AS ra
JOIN room AS r
    ON ra.roomId = r.roomId
JOIN room_has_bed AS rhb
    ON r.roomId = rhb.roomId
JOIN bed_type AS bt
    ON rhb.bedTypeId = bt.bedTypeId
GROUP BY
    bt.name
ORDER BY
    total_beds_in_assigned_rooms DESC,
    rooms_with_this_bed_type DESC;

-- 5. Event Size and Room Usage by Event Type
SELECT
    e.eventType AS event_type,
    COUNT(DISTINCT e.eventId) AS total_events,
    ROUND(AVG(e.estimatedGuestCount), 2) AS avg_estimated_guests,
    ROUND(AVG(rc.room_count), 2) AS avg_rooms_used
FROM event AS e
JOIN (
    SELECT
        eventId AS event_id,
        COUNT(roomId) AS room_count
    FROM event_room
    GROUP BY
        eventId
) AS rc
    ON e.eventId = rc.event_id
GROUP BY
    e.eventType
ORDER BY
    avg_rooms_used DESC,
    avg_estimated_guests DESC;

-- 6. Revenue by Service Type
SELECT
    st.serviceType AS service_type,
    COUNT(c.chargeId) AS total_charges,
    SUM(c.chargeAmount) AS total_revenue,
    ROUND(AVG(c.chargeAmount), 2) AS avg_charge
FROM charge AS c
JOIN service_type AS st
    ON c.serviceCode = st.serviceCode
GROUP BY
    st.serviceType
ORDER BY
    total_revenue DESC;

-- 7. Top 10 Highest-Value Billing Parties
SELECT
    p.partyId AS party_id,
    p.partyType AS party_type,
    p.contactPersonName AS contact_person_name,
    p.email AS email,
    COUNT(DISTINCT ba.accountId) AS total_accounts,
    COUNT(c.chargeId) AS total_charges,
    SUM(c.chargeAmount) AS total_billed_amount
FROM party AS p
JOIN billing_account AS ba
    ON p.partyId = ba.partyId
JOIN charge AS c
    ON ba.accountId = c.accountId
GROUP BY
    p.partyId,
    p.partyType,
    p.contactPersonName,
    p.email
ORDER BY
    total_billed_amount DESC
LIMIT 10;

-- 8. Maintenance Burden by Building and Wing
SELECT
    b.buildingName AS building_name,
    w.wingCode AS wing_code,
    COUNT(mt.ticketId) AS total_tickets,
    ROUND(AVG(julianday(mt.dateResolved) - julianday(mt.dateCreated)), 2) AS avg_resolution_days
FROM maintenance_ticket AS mt
JOIN room AS r
    ON mt.roomId = r.roomId
JOIN floor AS f
    ON r.floorId = f.floorId
JOIN wing AS w
    ON f.wingId = w.wingId
JOIN building AS b
    ON w.buildingId = b.buildingId
GROUP BY
    b.buildingName,
    w.wingCode
ORDER BY
    total_tickets DESC,
    avg_resolution_days DESC;

-- 9. Top 10 Rooms with the Highest Turnover
SELECT
    r.roomId AS room_id,
    r.roomNumber AS room_number,
    COUNT(ra.assignmentId) AS total_assignments
FROM room AS r
JOIN room_assignment AS ra
    ON r.roomId = ra.roomId
GROUP BY
    r.roomId,
    r.roomNumber
ORDER BY
    total_assignments DESC
LIMIT 10;

-- 10. Monthly Revenue Trend by Service Type
SELECT
    strftime('%Y-%m', c.dateIncurred) AS revenue_year_month,
    st.serviceType AS service_type,
    COUNT(c.chargeId) AS total_charges,
    SUM(c.chargeAmount) AS total_revenue
FROM charge AS c
JOIN service_type AS st
    ON c.serviceCode = st.serviceCode
GROUP BY
    strftime('%Y-%m', c.dateIncurred),
    st.serviceType
ORDER BY
    revenue_year_month,
    total_revenue DESC;
