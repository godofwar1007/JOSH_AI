import psycopg2
import json
import re 

"""so apparently some ranks contain the like "50P" here P is preparatory which causes an issue as other ranks are straight numbers so the rank type 
here is like GENERAL and PREPARATORY and the two functions that i wrote are used to deal with this stuff . i added the an extra filed rank_type for the db .
:P
"""

def clean_rank(rank):

    if rank is None:
        return  None
    
    digits = re.sub(r'\D', '', str(rank))
    return int(digits) if digits else None

def get_rank_type(rank):

    if rank is None:
        return 'GENERAL'
    return 'PREPARATORY' if str(rank).strip().upper().endswith('P') else 'GENERAL'

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="orcr_data",
    user="postgres",
    password="mysecretpassword"  # LMAO 
)
curr=conn.cursor()

with open('2025_iit_cutoffs.json', 'r', encoding='utf-8') as f:
    seats = json.load(f)

for seat in seats:
    rank_type=get_rank_type(seat.get('opening_rank'))

    curr.execute("""

        INSERT INTO seat_allocation 
        (institute, academic_program, seat_type, gender, opening_rank, closing_rank, rank_type)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        seat.get('institute'),
        seat.get('academic_program'),
        seat.get('seat_type'),
        seat.get('gender'),
        clean_rank(seat.get('opening_rank')),   
        clean_rank(seat.get('closing_rank')),
        rank_type)

    )

conn.commit()
curr.close()    

print("Data imported successfully and solved the 'P' thingy problem")
