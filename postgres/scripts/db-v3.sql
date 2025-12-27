CREATE DATABASE cars;
GRANT ALL PRIVILEGES ON DATABASE cars TO program;

CREATE DATABASE rentals;
GRANT ALL PRIVILEGES ON DATABASE rentals TO program;

CREATE DATABASE payments;
GRANT ALL PRIVILEGES ON DATABASE payments TO program;

-- Connect to cars database
\c cars;

-- Create cars table
CREATE TABLE IF NOT EXISTS cars
(
    id                  SERIAL PRIMARY KEY,
    car_uid             uuid UNIQUE NOT NULL,
    brand               VARCHAR(80) NOT NULL,
    model               VARCHAR(80) NOT NULL,
    registration_number VARCHAR(20) NOT NULL,
    power               INT,
    price               INT         NOT NULL,
    type                VARCHAR(20)
        CHECK (type IN ('SEDAN', 'SUV', 'MINIVAN', 'ROADSTER')),
    availability        BOOLEAN     NOT NULL
);

-- Grant permissions to program user
GRANT ALL PRIVILEGES ON TABLE cars TO program;
GRANT USAGE, SELECT ON SEQUENCE cars_id_seq TO program;

-- Insert test data
INSERT INTO cars (car_uid, brand, model, registration_number, power, type, price, availability)
VALUES ('109b42f3-198d-4c89-9276-a7520a7120ab', 'Mercedes Benz', 'GLA 250', 'ЛО777Х799', 249, 'SEDAN', 3500, true)
ON CONFLICT (car_uid) DO NOTHING;

-- Connect to rentals database
\c rentals;

-- Create rental table
CREATE TABLE IF NOT EXISTS rental
(
    id          SERIAL PRIMARY KEY,
    rental_uid  uuid UNIQUE              NOT NULL,
    username    VARCHAR(80)              NOT NULL,
    payment_uid uuid                     NOT NULL,
    car_uid     uuid                     NOT NULL,
    date_from   TIMESTAMP WITH TIME ZONE NOT NULL,
    date_to     TIMESTAMP WITH TIME ZONE NOT NULL,
    status      VARCHAR(20)              NOT NULL
        CHECK (status IN ('IN_PROGRESS', 'FINISHED', 'CANCELED'))
);

-- Grant permissions to program user
GRANT ALL PRIVILEGES ON TABLE rental TO program;
GRANT USAGE, SELECT ON SEQUENCE rental_id_seq TO program;

-- Connect to payments database
\c payments;

-- Create payment table
CREATE TABLE IF NOT EXISTS payment
(
    id          SERIAL PRIMARY KEY,
    payment_uid uuid UNIQUE NOT NULL,
    status      VARCHAR(20) NOT NULL
        CHECK (status IN ('PAID', 'CANCELED')),
    price       INT         NOT NULL
);

-- Grant permissions to program user
GRANT ALL PRIVILEGES ON TABLE payment TO program;
GRANT USAGE, SELECT ON SEQUENCE payment_id_seq TO program;