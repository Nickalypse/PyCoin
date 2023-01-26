
import sqlite3


dbFileName = "blockData.db"

# Connessione ad database
dbConnession = sqlite3.connect(dbFileName)
dbCursor = dbConnession.cursor()


"""
dbQuery = "INSERT INTO block VALUES ('0000050727d2917021bb0ebf92607f7f93c3d3580b57273b324e2ab5b065af91', '1')"
dbCursor.execute(dbQuery)
dbConnession.commit()
"""

height = int(input("N: "))

dbQuery = "DELETE FROM block WHERE height = %d" %(height)
dbCursor.execute(dbQuery)
dbConnession.commit()

dbQuery = "SELECT * FROM block"
dbCursor.execute(dbQuery)
dbConnession.commit()
results = dbCursor.fetchall()

for r in results:
    print(r)



input("")




# . . .

# Disconnessione dal database
dbConnession.close()


