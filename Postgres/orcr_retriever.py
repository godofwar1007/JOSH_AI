import asyncio
import asyncpg

s=[250,120,120,60,30,15]
h=[800,400,400,200,120,40]
class ORCR_Retriever:
    async def runa(self,ja_rank,category,gender):#for advanced rank
        conn = await asyncpg.connect(user='postgres', password='postgres',
                                    database='orcr_data', host='127.0.0.1',port=5555)
        values = await conn.fetch(
            "SELECT * FROM seat_allocation WHERE seat_type =$1 AND gender=$2 AND rank='adv'",category,gender 
        
        )
        

        l=[]
        c=["OPEN","OBC-NCL","GEN-EWS","SC","ST"]
        if category in c:
            self.low=s[c.index(category)]
            self.high=h[c.index(category)]
        else:
            self.low=25
            self.high=90
        for row in values:
            r=row["opening_rank"]
            cr=row["closing_rank"]
            institute=row["institute"]
            record={"Institute":institute,"Academic program":row["academic_program"],"Opening Rank":r,"Closing Rank":cr,"Alloted on basis of":"JEE Advanced" }
            if ja_rank>cr and (ja_rank-cr)<=self.low:
                l.append(record)
            if ja_rank<cr and (cr-ja_rank)<=self.high:
                l.append(record)

        p=sorted(l,key=lambda x:x["Opening Rank"],reverse=False)
        await conn.close()
        return p
    
    async def runm(self,jm_rank,category,gender): #for mains rank
        conn = await asyncpg.connect(user='postgres', password='postgres',
                                    database='orcr_data', host='127.0.0.1',port=5555)
        values = await conn.fetch(
            "SELECT * FROM seat_allocation WHERE seat_type =$1 AND gender=$2 AND rank='mains'",category,gender 
        
        )
        l=[]
        for row in values:
            r=row["opening_rank"]
            cr=row["closing_rank"]
            institute=row["institute"]
            record={"Institute":institute,"Academic program":row["academic_program"],"Opening Rank":r,"Closing Rank":cr,"Allotted on basis of":"JEE Mains"}
            if jm_rank>cr and (jm_rank-cr)<=self.low:
                l.append(record)
            if jm_rank<cr and (cr-jm_rank)<=self.high:
                l.append(record)

        p=sorted(l,key=lambda x:x["Opening Rank"],reverse=False)
        await conn.close()
        return p
        
        
    
def main():
    retriever=ORCR_Retriever()
    options=asyncio.run(retriever.runa(20,"ST(PwD)","Gender-Neutral"))
    print(options)
    options=asyncio.run(retriever.runm(20,"OPEN(PwD)","Gender-Neutral"))

    print(options)

if __name__== "__main__":
    main()