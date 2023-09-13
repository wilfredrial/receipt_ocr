import sqlite3
    
if __name__ == "__main__":    
    # Connect to the SQLite database (or create if it doesn't exist)
    with sqlite3.connect('spending_tracker.db') as con:
        cursor = con.cursor()
    
        # Create the merchants table
        # A new merchant will likely be created for each store number 
        # the name field can be used to track trips to the same chain
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS merchants (
                merchant_id INTEGER PRIMARY KEY,
                ocr_name TEXT UNIQUE,
                address TEXT,
                name TEXT,
                phone TEXT,
                website TEXT,
                city TEXT,
                state TEXT,
                zip TEXT,
                country TEXT
            )
        ''')
    
        # Create the receipts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS receipts (
                receipt_id INTEGER PRIMARY KEY,
                merchant_id INTEGER,
                trip_datetime TEXT UNIQUE, -- datetime
                upload_datetime TEXT, -- datetime
                subtotal REAL,
                tax REAL,
                total REAL,
                FOREIGN KEY (merchant_id) REFERENCES merchants (merchant_id)
            )
        ''')
    
        # Create the items table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS items (
                item_id INTEGER PRIMARY KEY,
                merchant_id INTEGER,
                description TEXT,
                user_descr TEXT,
                FOREIGN KEY (merchant_id) REFERENCES merchants (merchant_id)
            )
        ''')
    
        # Create the purchases table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS purchases (
                purchase_id INTEGER PRIMARY KEY,
                receipt_id INTEGER,
                merchant_id INTEGER,
                item_id INTEGER,
                item_cost REAL,
                discount REAL,
                quantity INTEGER,
                unit_price REAL,
                flag TEXT,
                notes TEXT,
                creditor INTEGER,
                debtor INTEGER,
                debt_multiplier REAL,
                FOREIGN KEY (receipt_id) REFERENCES receipts (receipt_id),
                FOREIGN KEY (merchant_id) REFERENCES merchants (merchant_id)
                FOREIGN KEY (creditor) REFERENCES participants (participant_id)
                FOREIGN KEY (debtor) REFERENCES participants (participant_id)
            )
        ''')
    
        # Create the participants table
        # This is for people you share the costs with
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS participants (
                participant_id INTEGER PRIMARY KEY,
                name TEXT,
                email TEXT UNIQUE
            )
        ''')
    
        # Create the shared_payments table
        # tracks shared payments, supposing the trip should be divided among
        # multiple people
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shared_payments (
                shared_payment_id INTEGER PRIMARY KEY,
                receipt_id INTEGER,
                debtor INTEGER,
                creditor INTEGER,
                amount_owed INTEGER,
                is_paid INTEGER, -- boolean
                paid_datetime TEXT, -- datetime
                FOREIGN KEY (receipt_id) REFERENCES receipts (receipt_id),
                FOREIGN KEY (debtor) REFERENCES participants (participant_id),
                FOREIGN KEY (creditor) REFERENCES participants (participant_id)
            )
        ''')
    
        # Creates a trigger to update the paid_datetime column
        # from shared_payments table when is_paid is changed
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_date_trigger
            AFTER UPDATE OF is_paid ON shared_payments
            WHEN new.is_paid = 1
            BEGIN
                UPDATE shared_payments
                SET paid_datetime = DATETIME('now')
                WHERE id = new.id;
            END;
        """)
    
        # Create the BEFORE INSERT trigger on receipts table
        # checks to make sure the same datetime isn't added twice
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS check_duplicate_trip_datetime
            BEFORE INSERT ON receipts
            BEGIN
                SELECT CASE
                WHEN EXISTS (SELECT 1 FROM receipts WHERE trip_datetime = NEW.trip_datetime) THEN
                RAISE(ABORT, 'Duplicate trip_datetime detected. Record not inserted.')
            END;
            END;
        ''')
    
    
        # Commit changes and close the connection
        con.commit()
    
    print("Connection closed.")