PRAGMA foreign_keys = ON;

CREATE TABLE hotel (
    hotelId INTEGER PRIMARY KEY,
    hotelName TEXT NOT NULL
);

CREATE TABLE building (
    buildingId INTEGER PRIMARY KEY,
    hotelId INTEGER NOT NULL,
    buildingName TEXT NOT NULL,
    FOREIGN KEY (hotelId) REFERENCES hotel(hotelId)
);

CREATE TABLE wing (
    wingId INTEGER PRIMARY KEY,
    buildingId INTEGER NOT NULL,
    wingCode TEXT NOT NULL,
    nearPool INTEGER NOT NULL CHECK (nearPool IN (0, 1)),
    nearParking INTEGER NOT NULL CHECK (nearParking IN (0, 1)),
    handicapAccess INTEGER NOT NULL CHECK (handicapAccess IN (0, 1)),
    FOREIGN KEY (buildingId) REFERENCES building(buildingId),
    UNIQUE (buildingId, wingCode)
);

CREATE TABLE floor (
    floorId INTEGER PRIMARY KEY,
    wingId INTEGER NOT NULL,
    floorNumber INTEGER NOT NULL,
    nonSmokingFloor INTEGER NOT NULL CHECK (nonSmokingFloor IN (0, 1)),
    FOREIGN KEY (wingId) REFERENCES wing(wingId),
    UNIQUE (wingId, floorNumber)
);

CREATE TABLE room (
    roomId INTEGER PRIMARY KEY,
    floorId INTEGER NOT NULL,
    roomNumber TEXT NOT NULL,
    baseRate REAL NOT NULL,
    maxCapacity INTEGER NOT NULL,
    currentStatus TEXT NOT NULL,
    FOREIGN KEY (floorId) REFERENCES floor(floorId),
    UNIQUE (floorId, roomNumber)
);

CREATE TABLE function (
    functionCode TEXT PRIMARY KEY,
    functionName TEXT NOT NULL UNIQUE
);

CREATE TABLE room_function (
    roomId INTEGER NOT NULL,
    functionCode TEXT NOT NULL,
    activeness TEXT,
    PRIMARY KEY (roomId, functionCode),
    FOREIGN KEY (roomId) REFERENCES room(roomId),
    FOREIGN KEY (functionCode) REFERENCES function(functionCode)
);

CREATE TABLE bed_type (
    bedTypeId INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    capacity INTEGER NOT NULL
);

CREATE TABLE room_has_bed (
    roomId INTEGER NOT NULL,
    bedTypeId INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity >= 0),
    isFoldable INTEGER NOT NULL CHECK (isFoldable IN (0, 1)),
    PRIMARY KEY (roomId, bedTypeId),
    FOREIGN KEY (roomId) REFERENCES room(roomId),
    FOREIGN KEY (bedTypeId) REFERENCES bed_type(bedTypeId)
);

CREATE TABLE room_adjacency (
    roomId1 INTEGER NOT NULL,
    roomId2 INTEGER NOT NULL,
    connectionType TEXT NOT NULL,
    PRIMARY KEY (roomId1, roomId2),
    FOREIGN KEY (roomId1) REFERENCES room(roomId),
    FOREIGN KEY (roomId2) REFERENCES room(roomId),
    CHECK (roomId1 <> roomId2)
);

CREATE TABLE party (
    partyId INTEGER PRIMARY KEY,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    partyType TEXT NOT NULL,
    contactPersonName TEXT NOT NULL
);

CREATE TABLE guest_group (
    partyId INTEGER NOT NULL,
    guestId INTEGER NOT NULL,
    guestName TEXT NOT NULL,
    PRIMARY KEY (partyId, guestId),
    FOREIGN KEY (partyId) REFERENCES party(partyId)
);

CREATE TABLE billing_account (
    accountId INTEGER PRIMARY KEY,
    partyId INTEGER NOT NULL,
    status TEXT NOT NULL,
    creditLimit REAL,
    FOREIGN KEY (partyId) REFERENCES party(partyId)
);

CREATE TABLE reservation (
    reservationId INTEGER PRIMARY KEY,
    partyId INTEGER NOT NULL,
    dateCreated TEXT NOT NULL,
    startDate TEXT NOT NULL,
    endDate TEXT NOT NULL,
    status TEXT NOT NULL,
    depositRequired INTEGER NOT NULL CHECK (depositRequired IN (0, 1)),
    depositAmount REAL DEFAULT 0,
    FOREIGN KEY (partyId) REFERENCES party(partyId),
    CHECK (julianday(endDate) >= julianday(startDate))
);

CREATE TABLE room_assignment (
    assignmentId INTEGER PRIMARY KEY,
    reservationId INTEGER NOT NULL,
    roomId INTEGER NOT NULL,
    assignmentDate TEXT NOT NULL,
    FOREIGN KEY (reservationId) REFERENCES reservation(reservationId),
    FOREIGN KEY (roomId) REFERENCES room(roomId)
);

CREATE TABLE stay (
    stayId INTEGER PRIMARY KEY,
    reservationId INTEGER NOT NULL,
    checkinTime TEXT NOT NULL,
    checkoutTime TEXT,
    FOREIGN KEY (reservationId) REFERENCES reservation(reservationId),
    CHECK (checkoutTime IS NULL OR julianday(checkoutTime) >= julianday(checkinTime))
);

CREATE TABLE event (
    eventId INTEGER PRIMARY KEY,
    hostPartyId INTEGER NOT NULL,
    eventType TEXT NOT NULL,
    startTime TEXT NOT NULL,
    endTime TEXT NOT NULL,
    estimatedGuestCount INTEGER,
    usageTime TEXT,
    FOREIGN KEY (hostPartyId) REFERENCES party(partyId),
    CHECK (julianday(endTime) >= julianday(startTime))
);

CREATE TABLE event_room (
    eventId INTEGER NOT NULL,
    roomId INTEGER NOT NULL,
    PRIMARY KEY (eventId, roomId),
    FOREIGN KEY (eventId) REFERENCES event(eventId),
    FOREIGN KEY (roomId) REFERENCES room(roomId)
);

CREATE TABLE service_type (
    serviceCode INTEGER PRIMARY KEY,
    serviceType TEXT NOT NULL UNIQUE,
    baseRate REAL NOT NULL
);

CREATE TABLE charge (
    chargeId INTEGER PRIMARY KEY,
    accountId INTEGER NOT NULL,
    stayId INTEGER,
    serviceCode INTEGER NOT NULL,
    chargeAmount REAL NOT NULL,
    dateIncurred TEXT NOT NULL,
    FOREIGN KEY (accountId) REFERENCES billing_account(accountId),
    FOREIGN KEY (stayId) REFERENCES stay(stayId),
    FOREIGN KEY (serviceCode) REFERENCES service_type(serviceCode)
);

CREATE TABLE maintenance_ticket (
    ticketId INTEGER PRIMARY KEY,
    roomId INTEGER NOT NULL,
    issueDescription TEXT NOT NULL,
    status TEXT NOT NULL,
    dateCreated TEXT NOT NULL,
    dateResolved TEXT,
    FOREIGN KEY (roomId) REFERENCES room(roomId),
    CHECK (dateResolved IS NULL OR julianday(dateResolved) >= julianday(dateCreated))
);
