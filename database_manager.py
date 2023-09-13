import json
import datetime
import pandas as pd
import sqlite3

import ocr_api

DB_NAME = "spending_tracker.db"

def items_to_df():
    with sqlite3.connect(DB_NAME) as con:
        sql = 'select * from items'
        df = pd.read_sql(sql=sql, con=con)
    return df

def insert_to_merchants(df):
    if not isinstance(df, pd.DataFrame):
        raise ValueError('1st argument must be pandas dataframe!!')
    print('opening connection to merchants')
    with sqlite3.connect(DB_NAME) as con:
        cur = con.cursor()
        data = df.to_dict(orient='records')
        insert = """
                INSERT OR IGNORE INTO merchants 
                VALUES(
                        :merchant_id, 
                        :ocr_name,
                        :address,
                        :name,
                        :phone,
                        :website, 
                        :city,
                        :state,
                        :zip,
                        :country
                )"""
        cur.executemany(insert, data)
        con.commit()
    print('exiting insert_to_merchants')

def insert_to_items(df):
    if not isinstance(df, pd.DataFrame):
        raise ValueError('1st argument must be pandas dataframe!!')
    print('opening connection to items')
    with sqlite3.connect(DB_NAME) as con:
        cur = con.cursor()
        data = df.to_dict(orient='records')
        insert = """
                INSERT OR IGNORE INTO items 
                VALUES(
                        :item_id, 
                        :merchant_id,
                        :description,
                        :user_descr
                )"""
        cur.executemany(insert, data)
        con.commit()
    print('exiting insert_to_items')

def insert_to_receipts(df):
    if not isinstance(df, pd.DataFrame):
        raise ValueError('1st argument must be pandas dataframe!!')
    print('opening connection to receipts')
    with sqlite3.connect(DB_NAME) as con:
        cur = con.cursor()
        data = df.to_dict(orient='records')
        insert = """
                INSERT OR ABORT INTO receipts 
                VALUES(
                        :receipt_id,
                        :merchant_id, 
                        :trip_datetime,
                        :upload_datetime,
                        :subtotal,
                        :tax,
                        :total
                )"""
        cur.executemany(insert, data)
        con.commit()
    print('exiting insert_to_receipts')

def insert_to_purchases(df):
    if not isinstance(df, pd.DataFrame):
        raise ValueError('1st argument must be pandas dataframe!!')
    print('opening connection to purchases')
    with sqlite3.connect(DB_NAME) as con:
        cur = con.cursor()
        data = df.to_dict(orient='records')
        insert = """
                INSERT OR IGNORE INTO purchases 
                VALUES
                (
                    :purchase_id,
                    :receipt_id,
                    :merchant_id,
                    :item_id,
                    :item_cost,
                    :discount,
                    :quantity,
                    :unit_price,
                    :flag,
                    :notes,
                    :creditor,
                    :debtor,
                    :debt_multiplier 
                )"""
        cur.executemany(insert, data)
        con.commit()
    print('exiting insert_to_purchases')

def insert_to_shared_payments(df):
    if not isinstance(df, pd.DataFrame):
        raise ValueError('1st argument must be pandas dataframe!!')
    print('opening connection to shared_payments')
    with sqlite3.connect(DB_NAME) as con:
        cur = con.cursor()
        data = df.to_dict(orient='records')
        insert = """
                INSERT OR IGNORE INTO shared_payments 
                VALUES(
                :shared_payment_id,
                :receipt_id,
                :creditor,
                :debtor,
                :amount_owed,
                :is_paid,
                :paid_datetime 
                )"""
        cur.executemany(insert, data)
        con.commit()
    print('exiting insert_to_shared_payments')

def get_merchant_id(ocr_name):
    with sqlite3.connect(DB_NAME) as con:
        params = {'ocr_name':ocr_name}
        cur = con.cursor()
        sql = """
            select 
                merchant_id
            from 
                merchants
            where 
                ocr_name = :ocr_name
        """
        cur.execute(sql, params)
        result = cur.fetchall()
    return result[0][0]

def get_trip_id(trip_datetime):
    with sqlite3.connect(DB_NAME) as con:
        params = {'trip_datetime':trip_datetime}
        cur = con.cursor()
        sql = """
            select 
                receipt_id
            from 
                receipts
            where 
                trip_datetime = :trip_datetime 
        """
        cur.execute(sql, params)
        result = cur.fetchall()
    return result[0][0]

def get_item_ids(descriptions, merchant_id):
    # descriptions should be a list
    # use the descriptions and merchant_id to get itemids for the trip
    with sqlite3.connect(DB_NAME) as con:
        cur = con.cursor()
        placeholders = ','.join(['?'] * len(descriptions))
        sql = f'''
            select description, item_id 
            from items
            where
                description in ({placeholders})
                and
                merchant_id = ?
        '''
        params = descriptions + [merchant_id]
        cur.execute(sql, params)
        description_to_id = {}
        for row in cur.fetchall():
            description_to_id[row[0]] = row[1]
    return description_to_id

def remove_existing_records(dataframe):
    with sqlite3.connect(DB_NAME) as con:
        sql = "SELECT description, merchant_id FROM items"
        existing_data = pd.read_sql_query(sql, con)
    merged_data = dataframe.merge(existing_data, 
                                  on=['description', 'merchant_id'], 
                                  how='left', 
                                  indicator=True)
    new_data = merged_data[merged_data['_merge'] == 'left_only']    
    new_data = new_data.drop(columns=['_merge'])
    return new_data.drop_duplicates()

def upload_response(filename):
    with open(f"json/{filename}") as f_in:
        jobj = json.load(f_in)
    receipt = jobj['receipts'][0]

    # list the merchant details
    merchant = {
        'merchant_id':None,
        'ocr_name': receipt['merchant_name'],
        'address': receipt['merchant_address'], 
        'name':None,
        'phone': receipt['merchant_phone'],
        'website': receipt['merchant_website'],
        'city':receipt['city'],
        'state':receipt['state'],
        'zip':receipt['zip'],
        'country': receipt['country']
    }
    merchant_df = pd.DataFrame(merchant, index=[0])
    # load merchant to db if not already there
    insert_to_merchants(merchant_df)

    # load the items into a dataframe if not already there
    items = pd.DataFrame(receipt['items'])
    items.rename(columns={
                    'amount':'item_cost',
                    'qty':'quantity', 
                    'unitPrice':'unit_price', 
                    'flags':'flag', 
                    'remarks':'notes'},
                inplace=True)

    items['discount']=0 # creates a new column for discounts
    # loops through the discounts and adds it to the row above
    discount_list = items[items['item_cost'] < 0].index
    if len(discount_list) != 0:
        for i in discount_list: 
            items.loc[i-1, 'discount'] = items.loc[i, 'item_cost']
        dis_del = discount_list.append(discount_list-1) # get indexes of discounts
        dis_del = dis_del.sort_values() # sort them

        print(items.loc[dis_del])
        if input('Do you approve deleting the discount row and writing the \
                 item_cost to the discount value in the previous row? y/n\n')!='y':
            raise ValueError('Not approved. Exiting!!')

        # remove the row(s)
        # if else because the drop function doesn't like a list with 1 value
        if len(discount_list)==1:
            items.drop(discount_list[0], inplace=True)
        else:
            items.drop(discount_list, inplace=True)
        items.reset_index(drop=True, inplace=True)

    # make the dataframe for the items table
    items_df = pd.DataFrame(items['description'])
    merchant_id = get_merchant_id(merchant['ocr_name'])
    try:
        items_df['merchant_id'] = merchant_id
    except ValueError:
        breakpoint()
    items_df = remove_existing_records(items_df)
    if len(items_df) > 0:
        items_df['item_id'] = None
        items_df['user_descr'] = None
        insert_to_items(items_df)    

    # make the dataframe for the receipts table
    # read the datetime from the receipt
    date_dict = {
        'date': receipt['date'],
        'time': receipt['time']
    }

    try:
        trip_dt = date_dict['date'] + ' ' + date_dict['time']
    except TypeError:
        print('Error with date or time from receipt!')
        breakpoint()
    now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    trip_df = pd.DataFrame(data={'receipt_id':None,
                                'merchant_id':merchant_id,
                                'trip_datetime':trip_dt,
                                'upload_datetime':now,
                                'subtotal':receipt['subtotal'],
                                'tax':receipt['tax'],
                                'total':receipt['total']},
                            index=[0])
    insert_to_receipts(trip_df)

    # preparing purchases
    trip_id = get_trip_id(trip_dt)
    purchase_df = items[['item_cost',
                         'description',
                        'quantity',
                        'flag',
                        'unit_price', 
                        'notes',
                        'discount']].copy()
    purchase_df['purchases_id'] = None
    purchase_df['merchant_id'] = merchant_id
    purchase_df['receipt_id'] = trip_id
    # getting item ids based on matching description and merchant_id
    purchase_dict = get_item_ids(items['description'].to_list(), merchant_id)
    purchase_df['item_id'] = purchase_df['description'].map(purchase_dict)
    
    # This part is under construction
    # Eventually I would like to make a GUI and add dynamic options
    # This works well enough for now...
    purchase_df['creditor'] = 2 # default is my friend with costco card
    purchase_df['debtor'] = 1 # default is me
    purchase_df['debt_multiplier'] = 0.4 # we agreed on 40%

    print(purchase_df[['description','item_cost', 'creditor','debtor']])
    print('This is your chance to change debt_multiplier easily!')
    # I may skip this part for now
    me = input('Type the ids of the values that should be paid only by me').split(' ')
    me = [int(x) for x in me]
    fr = input('Type the ids of the values that should be paid only by friend').split(' ')
    fr = [int(x) for x in fr]
    if me[0] != '':
        purchase_df.loc[me, 'debt_multiplier'] = 1
    if fr[0] != '':
        purchase_df.loc[fr, 'debtor'] = 2 # friend
        purchase_df.loc[fr, 'debt_multiplier'] = 1
    purchase_df.drop(columns='description', inplace=True)
    purchase_df['purchase_id'] = None
    insert_to_purchases(purchase_df)

    # preparing shared_payments
    # later I want to generalize this for more than 2 ppl
    purchase_df['final_price'] = (purchase_df['item_cost'] + purchase_df['discount']) * purchase_df['debt_multiplier']
    # creates a df with total amount paid by each person
    shared_payments_df = purchase_df[['creditor','debtor','final_price']].groupby(['debtor','creditor']).sum().reset_index()
    shared_payments_df['is_paid'] = 0 # false; sqlite doesn't support boolean
    shared_payments_df.rename(columns={'final_price':'amount_owed'}, inplace=True)
    # filters out rows where debtor and creditor are equal
    shared_payments_df = shared_payments_df[shared_payments_df['creditor'] != shared_payments_df['debtor']].copy()
    shared_payments_df['shared_payment_id'] = None
    shared_payments_df['receipt_id'] = trip_id
    shared_payments_df['paid_datetime'] = None
    insert_to_shared_payments(shared_payments_df) 
    print("Finished last insert!")

def recalculate_shared_payment(receipt_id):
    """
        supply a shopping trip id to recalculate amount_owed in shared_payments
    """
    with sqlite3.connect(DB_NAME) as con:
        cur = con.cursor()
        params = {'receipt_id':receipt_id}        
        sql = """
        UPDATE shared_payments
        SET amount_owed = (
            SELECT sum((item_cost + discount)) * debt_multiplier
            FROM purchases
            WHERE receipt_id = :receipt_id
            and debtor = 1
        )
        WHERE receipt_id = :receipt_id
        """
        cur.execute(sql, params)
        con.commit()

def get_recent_purchases():
    with sqlite3.connect(DB_NAME) as con:
        sql = """
          select sum((item_cost + discount)) as subtotal
          from purchases
          where receipt_id = ( 
              select receipt_id 
              from receipts
              order by receipt_id desc
              limit 1
             )
        """
        res = pd.read_sql(sql=sql, con=con)
    return res

def get_recent_receipt():
    with sqlite3.connect(DB_NAME) as con:
        sql = """
            select * 
            from receipts
            order by receipt_id desc
            limit 1
        """
        res = pd.read_sql(sql=sql, con=con)
    return res

def get_recent_shared_payment():
    with sqlite3.connect(DB_NAME) as con:
        sql = """
          select *
          from shared_payments
          where receipt_id = ( 
              select receipt_id 
              from receipts
              order by receipt_id desc
              limit 1
             )
        """
        res = pd.read_sql(sql=sql, con=con)
    return res

def generate_report():
    with sqlite3.connect(DB_NAME) as con:
        sql = """
          select
              i.description,
              p.item_cost,
              p.discount,
              (p.item_cost + p.discount) as net_cost,
              p.debt_multiplier as debt_fraction,
              p1.name as creditor_name,
              p2.name as debtor_name,
              r.trip_datetime
          from purchases p
              inner join merchants m on 
                  p.merchant_id = m.merchant_id
              inner join receipts r on 
                  p.receipt_id = r.receipt_id
              inner join items i on 
                  p.item_id = i.item_id
              inner join participants p1 on
                  p.creditor = p1.participant_id
              inner join participants p2 on
                  p.debtor = p2.participant_id
          where r.receipt_id = ( 
              select receipt_id 
              from receipts
              order by receipt_id desc
              limit 1
             )
        """
        res = pd.read_sql(sql=sql, con=con)
    return res

def main(img_path=None):
    if img_path == None:
        img_path = input('Enter the receipt pic filename:\n')
    res = ocr_api.get_results(img_path)
    upload_response(res)

if __name__ == "__main__":
    main()
    