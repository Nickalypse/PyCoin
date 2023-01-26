
import sqlite3


dbConnession = sqlite3.connect("pycoinDB.db")
dbCursor = dbConnession.cursor()








"""
dbQuery = "SELECT * FROM key"
dbCursor.execute(dbQuery)
result = dbCursor.fetchall()

print(result)



dbQuery = "DELETE FROM key WHERE 1"
dbCursor.execute(dbQuery)
result = dbCursor.fetchall()
dbConnession.commit()



dbQuery = "SELECT * FROM key"
dbCursor.execute(dbQuery)
result = dbCursor.fetchall()

print(result)
"""

