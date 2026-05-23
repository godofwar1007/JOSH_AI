import asyncio
import asyncpg

class ORCR_Retriever:
    async def run(self,rank,category,gender):
        conn = await asyncpg.connect(user='postgres', password='postgres',
                                    database='orcrdb', host='127.0.0.1',port=5555)
        values = await conn.fetch(
            "SELECT * FROM seat_allocation WHERE seat_type =$1 AND gender=$2",category,gender 
        
        )
        l=[]
        for row in values:
            r=row["opening_rank"]
            cr=row["closing_rank"]
            institute=row["institute"]
            k=len(institute)
            institute=institute[0:3]+" "+institute[3:k]
            record=[institute,row["academic_program"],r,cr,row["rank_type"]]
            if rank>cr and (rank-cr)<=250:
                l.append(record)
            if rank<cr and (cr-rank)<=800:
                l.append(record)

        p=sorted(l,key=lambda x:x[2],reverse=False)
        print(p)
        await conn.close()

retriever=ORCR_Retriever()
asyncio.run(retriever.run(1688,"OPEN","Gender-Neutral"))