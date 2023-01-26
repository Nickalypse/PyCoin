
import threading
import socket
import pickle
import time

import sys
sys.path.append("../")
import globalVariables.variables


class Client(threading.Thread):

    port  = 8096
    ip    = None


    def __init__(self, peersManager):

        # Gestione liste & code peers interna al thread
        self.peersManager = peersManager

        # Creazione socket
        self.peerServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Inizializzazione thread
        threading.Thread.__init__(self)


    def run(self):

        # Estrazione indirizzo ip del peer server a cui connettersi
        self.ip = self.peersManager.ip_to_client.get()

        # Esegui nuovo client per successuva connessione
        startNewPeerClient(self.peersManager)
        
        try:
            # Connessione al lato server del peer
            self.peerServer.connect((self.ip, self.port))
        except:
            # Peer offline
            print("\n[!] Connessione fallita al peer %s\n" %(self.ip))
        else:

            if self.ip in self.peersManager.peers_server :
                self.peerServer.close()
                # Termina thread
                return

            # -- print("\n[i] Connessione stabilita al peer %s\n" %(self.ip))

            # Attesa esito connessione al peer server
            connectionResult = self.peerServer.recv(512)
            connectionResult = connectionResult.decode("ascii")

            if(connectionResult == "alreadyConnected"):
                # Connessione già stabilita --> Disconnessione
                self.peerServer.close()
                # -- print("[!] Connessione gia' effettuata con %s" %(self.ip))
                # Termina thread
                return

            
            # Nuova connessione --> Peer online
            print("\n[i] Connessione stabilita al peer %s\n" %(self.ip))
            # Aggiunge ip alla lista dei peers server online
            self.peersManager.peers_server.append(self.ip)


            # Ricezione lista peers conosciuti dal peer a cui si è connessi
            self.receivePeersList()


            # -- MAIN -----------------------------------------------------------------
            while True:

                # Estrazione indirizzo ip del peer server a cui connettersi
                query = self.peersManager.query_to_server.get()
                # -- print("<<< {} >>>".format(query))

                operation = query[0]

                if(operation != "pass"):

                    # Invio richiesta operazione al server
                    query = pickle.dumps(query)
                    try:
                        self.peerServer.send(query)
                        time.sleep(0.3)
                    except:
                        pass
                    else:
                        if(operation == "sendTransaction"):
                            pass
                            # -- print("[CLIENT][SEND] transaction")

                        elif(operation == "sendBlock"):
                            pass
                            # -- print("[CLIENT][SEND] block")

                        elif(operation == "updateBlockchain"):
                            # -- print("[CLIENT][SEND] updateBlockchain")
                            self.updateBlockchain()


            # Termina thread
            return


    # -------------------------------------------------------------------------------------

    def updateBlockchain(self):

        # Estrazione height del blocco memorizzato più recente
        blockHeight = globalVariables.variables.protocol.lastBlock["height"]
        
        # Estrazione hash del blocco memorizzato più receente
        blockHash = globalVariables.variables.protocol.lastBlock["hash"]

        # Invio dati blocco al peer per l'aggiornamento
        self.peerServer.send( pickle.dumps( (blockHeight, blockHash) ) )


        # Ricezione esito analisi blocco da peer server
        result = self.peerServer.recv(512)
        result = result.decode("ascii")

        # Se blocco inviato ha height o hash non valido, termina esecuzione
        if(result == "alteredBlockchainError"):
            print("[ERRORE FATALE]: La blockchain locale è stata alterata")
            input("")
            exit(-1)

        # Ricezione nuovi blocchi da peer server
        elif(result == "sendingBlocks"):

            # Ricezione nuovi blocchi dal peer server
            while True:

                # Ricezione nuovo blocco dal peer server
                try:
                    time.sleep(0.3)
                    block = self.peerServer.recv(2048)
                except:
                    break

                # Conversione del blocco ricevuto
                block = pickle.loads(block)

                if(block == "inexistentBlock"):
                    print("[+++] AGGIORNAMENTO BLOCKCHAIN COMPLETATO")
                    globalVariables.variables.protocol.eventBlockchainUpdate = True
                    break

                # Blocco inviato al protocol manager per il controllo validità
                globalVariables.variables.protocol.checkBlockOption(block)

                # Esito controllo del blocco
                result = globalVariables.variables.protocol.result.get()

                if(result == False):
                    # Ricevuto blocco non valido --> peer client rifiutato
                    print("[!!!]: Ricevuto blocco non valido.\nTerminata connessione con peer non affidabile (%s)" %(self.ip))
                    break

    # -------------------------------------------------------------------------------------










    # -------------------------------------------------------------------------------------



    # -------------------------------------------------------------------------------------

    def receivePeersList(self):

        query = ("getPeersList", None)
        query = pickle.dumps(query)

        # Invio richiesta operazione al server
        self.peerServer.send(query)

        totPeers = self.peerServer.recv(512)
        totPeers = int( totPeers.decode("ascii") )

        # -- print("[TOT PEERS DA RICEVERE]: %d" %(totPeers))

        for i in range(totPeers) :
            # Ricezione ip del peer online
            ipPeerOnline = self.peerServer.recv(512)
            ipPeerOnline = ipPeerOnline.decode("ascii")
            print("\n<+> Ricevuto ip del peers: %s\n" %(ipPeerOnline))
            # Ip aggiunto alla coda per una nuova connessione tramite client
            self.peersManager.ip_to_client.put(ipPeerOnline)



###########################################################################################

def startNewPeerClient(peersManager):
    
    # Creazione nuovo client
    newClient = Client(peersManager)

    # Esecuzione thread --> nuovo client
    newClient.start()

    # -- print("\n<< New ClientThread >>\n")



