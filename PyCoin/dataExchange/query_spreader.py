
import threading
import queue
import random


class querySpreader(threading.Thread):

    # Coda di tuple --> Richieste per peer client --> (("operation", "data"), ...)
    query_to_peer = queue.Queue()

    # Tupla estratta
    query = None


    def __init__(self, peersManager):

        # Gestione liste & code peers interna al thread
        self.peersManager = peersManager
        
        # Inizializzazione thread
        threading.Thread.__init__(self)


    def run(self):

        while True:

            # Estrazione query (tupla) dalla coda
            self.query = self.query_to_peer.get()
            # -- print("{QUERY_SPREADER} >>", self.query)

            operation = self.query[0]


            if(operation == "sendTransaction"):
                self.broadcast()

            elif(operation == "sendBlock"):
                self.broadcast()

            elif(operation == "updateBlockchain"):
                self.single()

            # --
            elif(operation == "testing"):
                self.broadcast()
            # --

    # -----------------------------------------------------------------------

    def broadcast(self):

        # Calcolo totale di peers server connessi
        totPeers = len(self.peersManager.peers_server)

        # Aggiunge query alla coda dei peer client
        for i in range(totPeers):
            self.peersManager.query_to_server.put(self.query)


    def single(self):

        # Calcolo totale di peers server connessi
        totPeers = len(self.peersManager.peers_server)

        index = random.randint(0, totPeers-1)

        for i in range(totPeers):
            if(i == index):
                # Singolo peer client estrae query
                self.peersManager.query_to_server.put(self.query)
            else:
                # Gli altri peer client ignorano la query estratta
                self.peersManager.query_to_server.put(("pass", ""))



