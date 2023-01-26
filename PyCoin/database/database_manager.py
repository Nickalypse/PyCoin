
import os.path
import sqlite3
import threading
import queue



class Database(threading.Thread) :

    dbFileName      = "database/pycoinDB.db"

    dbConnession    = None
    dbCursor        = None

    queryAddPeer    = "INSERT INTO {} (ip) VALUES ('{}')"
    queryRemovePeer = "DELETE FROM {} WHERE ip = '{}'"
    queryGetPeers   = "SELECT ip FROM {}"
    
    operations      = queue.Queue()  # Coda di tuple --> (("query", "data"), ...)
    results         = queue.Queue()  # Coda di liste --> (["ip", ...], ...)



    def __init__(self):

        # Inizializzazione thread
        threading.Thread.__init__(self)


    def run(self):
        # Connessione al DB
        self.dbConnect()
        # Creazione tabelle mancanti nel DB
        self.checkTables()

        while True:
            
            # Lettura funzione da eseguire <-- Coda
            function, data = self.operations.get()

            if(function == "getPeers"):
                # Ottieni lista peers da DB
                self.getPeers("peer")
            if(function == "getSeedServer"):
                # Ottieni lista ip "seed server" da DB
                self.getPeers("seedServer")
            elif(function == "addPeer"):
                # Aggiungi nuovo peer al DB
                self.addPeer("peer", data)
            elif(function == "removePeer"):
                # Elimina peer da DB
                self.removePeer("peer", data)
            elif(function == "addSeedServer"):
                # Aggiungi nuovo ip "seed server" al DB
                self.addPeer("seedServer", data)
            elif(function == "removeSeedServer"):
                # Elimina ip "seed server" da DB
                self.removePeer("seedServer", data)


            elif(function == "getKeys"):
                # Elimina ip "seed server" da DB
                self.getKeys()

            elif(function == "addKeys"):
                # Aggiunge chiave privata ed indirizzo wallet
                self.addKey(data)

            elif(function == "removeKeys"):
                # Aggiunge chiave privata ed indirizzo wallet
                self.removeKey(data)


            # . . .

            elif(function == "exit"):
                # Termina esecuzione thread
                break


        # Disconnessione dal DB
        self.dbDisconnect()


    # ---------------------------------------------------------------------------------------------

    def dbConnect(self):
        try:
            self.dbConnession = sqlite3.connect(self.dbFileName)
            self.dbCursor = self.dbConnession.cursor()
        except:
            print("FATAL ERROR: '%s' NOT WORK." %(self.dbFileName))
            exit(-1)


    def dbDisconnect(self):
        self.dbConnession.close()
        self.dbConnession = None
        self.dbCursor = None


    def checkTables(self):
        self.dbQuery = """
            CREATE TABLE IF NOT EXISTS seedServer(
                id  int          AUTO_INCREMENT  PRIMARY KEY,
                ip  varchar(15)  NOT NULL
            )"""
        self.dbCursor.execute(self.dbQuery)
        self.dbConnession.commit()
        
        self.dbQuery = """
            CREATE TABLE IF NOT EXISTS peer(
                id  int          AUTO_INCREMENT PRIMARY KEY,
                ip  varchar(15)  NOT NULL
            )"""
        self.dbCursor.execute(self.dbQuery)
        self.dbConnession.commit()

        self.dbQuery = """
            CREATE TABLE IF NOT EXISTS key(
                id  int   AUTO_INCREMENT  PRIMARY KEY,
                n   text  NOT NULL,
                e   text  NOT NULL,
                d   text  NOT NULL,
                p   text  NOT NULL,
                q   text  NOT NULL
            )"""
        self.dbCursor.execute(self.dbQuery)
        self.dbConnession.commit()


    # ------------------------------------------------------------------------------------

    def getKeys(self):
        dbQuery = "SELECT n, e, d, p, q FROM key"
        self.dbCursor.execute(dbQuery)
        # Estrazione righe
        result = self.dbCursor.fetchall()
        if(len(result) != 0):
            self.results.put(result[0])
        else:
            self.results.put([])


    def addKey(self, data):
        dbQuery = "INSERT INTO key (n, e, d, p, q) VALUES ('{}', '{}', '{}', '{}', '{}')".format(data["n"], data["e"], data["d"], data["p"], data["q"])
        self.dbCursor.execute(dbQuery)
        self.dbConnession.commit()


    def removeKey(self, id_profile):
        dbQuery = "DELETE FROM key WHERE id = '{}'".format(id_key)
        self.dbCursor.execute(dbQuery)
        self.dbConnession.commit()


    # ------------------------------------------------------------------------------------

    def addPeer(self, tableName, ipPeer):
        dbQuery = self.queryAddPeer.format(tableName, ipPeer)
        self.dbCursor.execute(dbQuery)
        self.dbConnession.commit()


    def removePeer(self, tableName, ipPeer):
        dbQuery = self.queryRemovePeer.format(tableName, ipPeer)
        self.dbCursor.execute(dbQuery)
        self.dbConnession.commit()


    def getPeers(self, tableName):
        dbQuery = self.queryGetPeers.format(tableName)
        self.dbCursor.execute(dbQuery)
        # Estrazione righe
        results = self.dbCursor.fetchall()
        
        # Generazione lista IP dei peers
        results_ip_list = []
        for row in results:
            results_ip_list.append(row[0])
            
        self.results.put(results_ip_list)



## MAIN ##################################################################################
"""
db = Database()
db.start()
db.operations.put(("getKeys", ""))
print(db.results.get())
"""




