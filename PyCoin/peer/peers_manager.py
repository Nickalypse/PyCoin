
import threading
import socket
import queue
import time


class Peer(threading.Thread) :

    seed_server       = []               # Lista ip dei "seed server"
    
    ip_to_client      = queue.Queue()    # Coda di ip (stringhe) dei peers a cui connettersi tramite socket
    query_to_server   = queue.Queue()    # Coda di richieste da inviare agli altri peer tramite peer client

    peers_unchecked   = []               # Lista ip dei peers a cui connettersi all'inizio
    peers_server      = []               # Lista ip dei peers a cui si è stabilita la connesione
    peers_client      = []               # Lista ip dei peers da cui si è ricevuta la connesione


    def __init__(self, db):

        # Gestione interna alla classe del thread "db"
        self.db = db

        # Inizializzazione thread
        threading.Thread.__init__(self)


    def run(self):

        # Acquisizione ip dei peers dell'ultima sessione
        self.getPeersFromDatabase()

        # Se nessun ip presente nell'ultima sessione --> "seed server"
        if(len(self.peers_unchecked) == 0):
            
            # Acquisizione ip del "seed server" dal database
            self.getSeedServerFromDatabase()

            if(len(self.seed_server) == 0):
                print("[!] ERRORE: IP del 'Seed Server' NON presente nel database locale.\nImpossibile connettersi alla rete p2p.")
                self.db.operations.put(("exit", ""))
                exit(-1)

            # Connessione al "seed server" per riceve lista di peers
            # con cui effettuare la prima connessione alla rete p2p
            self.getPeersFromSeedServer()

        # Connessione ai peers
        for ip in self.peers_unchecked :
            if(ip != socket.gethostbyname(socket.gethostname())):
                self.ip_to_client.put(ip)

        time.sleep(1)
        if(len(self.peers_server) == 0):
            print("[...] Attesa connessione da parte di un peer")


    ### Fine __init__ ---------------------------------------------------------------------


    def getPeersFromDatabase(self):

        self.db.operations.put(("getPeers", ""))
        results = self.db.results.get()
        
        # Memorizzazione ip in peers_unchecked
        self.peers_unchecked += results
        print("[i] IP dei peers memorizzati nel database: {}".format(self.peers_unchecked))


    def getSeedServerFromDatabase(self):

        self.db.operations.put(("getSeedServer", ""))
        results = self.db.results.get()
        
        # Memorizzazione ip "seed server"
        self.seed_server += results
        print("[i] IP del Seed Server: %s" %(self.seed_server))


    def getPeersFromSeedServer(self):

        # Inizializzazione socket per connessione al "seed server"
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Timeout di connessione
        s.settimeout(3)

        # Numero di porta di connessione
        port = 4097

        # Connessione ad ogni ip del "seed server"
        for ip in self.seed_server :

            try:
                # Tentativo di connessione al "seed server"
                s.connect((ip, port))
            except:
                print("\n[!] Impossibile stabilire connessione al Seed Server\n")
            else:
                # -- print("[+] Connessione stabilita al Seed Server (%s)" %(ip))

                query = "getPeers".encode("utf-8")
                
                # Richiesta ricevimento lista ip dei peers
                s.send(query)

                peersList = s.recv(512)
                peersList = peersList.decode("ascii")
                peersList = peersList.split(" ")

                # Memorizzazione ip in peers_unchecked
                self.peers_unchecked += peersList

                # Termine connessione al "seed server"
                s.close()

                print("[i] IP dei peers ricevuti dal Seed Server: {}".format(self.peers_unchecked))




