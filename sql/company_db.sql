DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS leave_balances;
DROP TABLE IF EXISTS tickets;

CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT NOT NULL
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    order_date DATE NOT NULL,
    status TEXT NOT NULL,
    total_amount NUMERIC(10, 2) NOT NULL
);

CREATE TABLE leave_balances (
    employee_id TEXT NOT NULL,
    leave_type TEXT NOT NULL,
    days_left INTEGER NOT NULL,
    PRIMARY KEY (employee_id, leave_type)
);

CREATE TABLE tickets (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    priority TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at DATE NOT NULL
);

INSERT INTO customers VALUES
    (1, 'Arun', 'Chennai'), (2, 'Priya', 'Bengaluru'), (3, 'Rahul', 'Mumbai'),
    (4, 'Anjali', 'Kochi'), (5, 'Vikram', 'Delhi');

INSERT INTO orders VALUES
    (1001, 1, '2026-03-02', 'delivered', 2499.00),
    (1002, 1, '2026-03-15', 'shipped', 899.00),
    (1003, 2, '2026-03-05', 'delivered', 15999.00),
    (1004, 3, '2026-03-10', 'out for delivery', 3297.00),
    (1005, 3, '2026-03-18', 'processing', 4999.00),
    (1006, 4, '2026-03-11', 'cancelled', 1299.00),
    (1007, 5, '2026-03-12', 'delivered', 799.00),
    (1008, 1, '2026-03-20', 'processing', 1599.00);

INSERT INTO leave_balances VALUES
    ('E001', 'Earned', 14), ('E001', 'Sick', 8), ('E001', 'Casual', 5),
    ('E002', 'Earned', 18), ('E002', 'Sick', 10), ('E002', 'Casual', 2),
    ('E003', 'Earned', 6), ('E003', 'Sick', 9), ('E003', 'Casual', 6);

INSERT INTO tickets VALUES
    (1, 'Payslip shows the wrong month', 'high', 'open', '2026-03-01'),
    (2, 'Laptop battery drains fast', 'medium', 'open', '2026-03-03'),
    (3, 'VPN disconnects every hour', 'high', 'open', '2026-03-04'),
    (4, 'Add GST number to invoice', 'low', 'closed', '2026-03-05'),
    (5, 'Cannot book a meeting room', 'low', 'open', '2026-03-06'),
    (6, 'Leave balance not updated', 'medium', 'open', '2026-03-07');
