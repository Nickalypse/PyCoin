
# _ - * .  PYCOIN  . * - _ #

# Pycoin Cryptocurrency (C)
# Conceived and realized by Niccolò Campitelli, 5 IND, 2018


import globalVariables.variables

from database.database_manager    import *
from peer.peers_manager           import *
from peer.peer_client             import *
from peer.peer_server             import *
from dataExchange.query_spreader  import *
from webManager.web_manager       import *
from protocol.protocol_manager    import *
from blockMiner.block_miner       import *

from os                           import path
from time                         import *


# ----------------------------------------------------------------------------------------

# Controllo esistenza DB
if(path.isfile("database/pycoinDB.db") == False):
    print("[ERRORE FATALE]: 'database/pycoinDB.db'")
    exit(-1)

# Controllo esistenza
if(path.isfile("blockchain/blockData.db") == False):
    print("[ERRORE FATALE]: 'blockchain/blockData.db'")
    exit(-1)

# Controllo esistenza
if(path.isfile("blockchain/0.json") == False):
    print("[ERRORE FATALE]: 'blockchain/0.json'")
    exit(-1)


# ----------------------------------------------------------------------------------------

# Inizializzazione variabili condivise
globalVariables.variables.init()


# Inizializzazione thread - gestione DB
db = Database()
# Esecuzione thread gestione database
db.start()


"""
db.operations.put(("removeSeedServer", "192.168.1.3"))
db.operations.put(("addSeedServer", "192.168.1.2"))
"""

# Inizializzazione gestore peers
globalVariables.variables.peersManager = Peer(db)
# Esecuzione thread gestione peers
globalVariables.variables.peersManager.start()


# Inizializzazione ed esecuzione thread per l'inoltro delle operazioni ai peers client
querySpreader = querySpreader(globalVariables.variables.peersManager)
querySpreader.start()


# Socket del server in ascolto <-- connesioni dei peers client
server = Server()

# Esecuzione thread --> Accettare connessione del peer client
startNewPeerServer(server, globalVariables.variables.peersManager)

# Inizializzazione protocollo Pycoin
globalVariables.variables.protocol = Protocol(db, querySpreader, globalVariables.variables.peersManager)
# Esecuzione thread per la gestione del protocollo Pycoin
globalVariables.variables.protocol.start()

# Creazione + esecuzione nuovo thread-client
startNewPeerClient(globalVariables.variables.peersManager)


"""--------------------------------------------------------
# Inizializzazione processo di mining
blockMiner = BlockMiner(globalVariables.variables.protocol)

# Esecuzione thread proccesso di mining
blockMiner.start()
#--------------------------------------------------------"""

# . . .

# Esecuzione gestore browser
start_web_control_panel()


