
import threading
import socket
import queue
import pickle
import time

import sys
sys.path.append("../")
import globalVariables.variables


class Server :

    port = 8096

    def __init__(self):

        self.socketServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Socket peer server associato alla porta
        self.socketServer.bind(("", self.port))
        
        # Peer server in ascolto + Dimensione coda connessioni
        self.socketServer.listen(1)


# ------------------------------------------------------------------------------

class ServerThread(threading.Thread):

    def __init__(self, server, peersManager):

        # Gestione interna al thread del socket server
        self.server = server

        # Gestione liste & code peers interna al thread
        self.peersManager = peersManager

        # Inizializzazione thread
        threading.Thread.__init__(self)


    def run(self):

        # Attesa connessione da peer client
        self.socketClient, self.dataClient = self.server.socketServer.accept()

        # Esegui nuovo server per successuva connessione
        startNewPeerServer(self.server, self.peersManager)

        # Controlla se la connessione al client è già effettuata
        # --> Evitare connessioni multiple da parte dello stesso client

        if self.dataClient[0] in self.peersManager.peers_client :
            # Connessione già stabilita --> Disconnessione
            connectionResult = "alreadyConnected"
            flagNewConnection = False
        else:
            # Nuova connessione --> Accettata
            connectionResult = "connected"
            flagNewConnection = True
            globalVariables.variables.protocol.log.put("peers %s" %(self.dataClient[0]))

        # Invia esito connessione al client
        connectionResult = connectionResult.encode("ascii")
        try:
            self.socketClient.send(connectionResult)
        except:
            # Termina thread
            return

        if(flagNewConnection == False):
            # Termina connessione al client
            self.socketClient.close()
            # -- print("[!] {} GIA' CONNESSO!".format(self.dataClient[0]))
            # Termina thread
            return

        # -- print("\nNUOVO CLIENT LANCIATO DA SERVER ({}) \n".format(self.dataClient[0]))
        # Esegue connessione al lato server del peer che si è appena connesso
        self.peersManager.ip_to_client.put(self.dataClient[0])
        # Aggiunge ip alla lista dei peers client online
        self.peersManager.peers_client.append(self.dataClient[0])


        # -- MAIN -------------------------------------------------------------------------
        while True:
            
            try:
                # Ricezione operazione richiesta dal peer client
                query = self.socketClient.recv(65536)
                time.sleep(0.3)
            except:
                # Se peer client si disconnette --> Termina thread
                self.disconnectPeer()
                break

            # Decodifica tupla
            try:
                query = pickle.loads(query)
                # -- print("[QUERY]: {}".format(query[0]))
            except:
                self.disconnectPeer()
                break

            operation = query[0]
            # -- print("[OPERATION]: {}".format(operation))

            if(operation == "getPeersList"):
                print("\n[###] Lista peers inoltrata a %s\n" %(self.dataClient[0]))
                self.getPeersList()

            elif(operation == "sendTransaction"):
                print("[###] Ricevuta transazione da %s\n" %(self.dataClient[0]))
                # Invia blocco ricevuto al protocollo per successivo controllo
                globalVariables.variables.protocol.query.put(("checkTransaction", query[1]))

            elif(operation == "sendBlock"):
                print("\n[###] Ricevuto blocco da %s\n" %(self.dataClient[0]))
                # Invia blocco ricevuto al protocollo per successivo controllo
                globalVariables.variables.protocol.query.put(("checkBlock", query[1]))

            # ------------------------------
            elif(operation == "testing"):
                print("\n--> TESTING <--\n")
            # ------------------------------

            elif(operation == "updateBlockchain"):
                print("\n[###] Aggiornamento blockchain per %s\n" %(self.dataClient[0]))
                self.updateBlockchain()

            else:
                print("\n[!!!] Ricevuta richiesta non valida da %s\n" %(self.dataClient[0]))
                """
                self.disconnectPeer()
                break
                """


        # Termina thread
        return

    # -------------------------------------------------------------------------------------

    def updateBlockchain(self):

        # Gestione di una singola richiesta di aggiornamento blockchain per volta
        while(globalVariables.variables.protocol.blockchainUpdateQuery == True):
            time.sleep(2)

        # Prenotazione del servizio di aggiornamento della blockchain
        globalVariables.variables.protocol.blockchainUpdateQuery = True
        
        # Ricezione dati dell'ultimo blocco memorizzato dal peer client
        blockData = self.socketClient.recv(512)
        blockData = pickle.loads(blockData)

        heightBlock  = blockData[0]
        hashBlock    = blockData[1]

        # Estrazione blocco con height ricevuta
        globalVariables.variables.protocol.extractBlock(heightBlock, True)
        block = globalVariables.variables.protocol.updateData.get()

        # Se blocco richiesto non valido o alterato, termina aggiornamento
        if((block == "inexistentBlock") or (block["hash"] != hashBlock)):
            print("\n[!!!] Ricevuto blocco non valido da %s\n" %(self.dataClient[0]))
            self.socketClient.send("alteredBlockchainError".encode("ascii"))

        # Inoltro dei blocchi mancanti al peer client
        else:
            self.socketClient.send("sendingBlocks".encode("ascii"))

            # Invio dei blocchi successivi al peer client
            while True:

                # Indice del blocco successivo
                heightBlock += 1

                # Estrazione blocco con height ricevuta
                globalVariables.variables.protocol.extractBlock(heightBlock, True)
                block = globalVariables.variables.protocol.updateData.get()

                # Invio blocco al peer client
                try:
                    self.socketClient.send(pickle.dumps(block))
                    time.sleep(0.3)
                except:
                    break

                # Aggiornamento del peer client completato
                if(block == "inexistentBlock"):
                    break
                """
                else:
                    print("[Send block to %s] %s" %(self.dataClient[0], block["header"]))
                """

            # Invio notifica di aggiornamento blockchain completato
            try:
                self.socketClient.send("updatedBlockchain".encode("ascii"))
            except:
                pass

        # Servizio di aggiornamento disponibile ad altri peer
        globalVariables.variables.protocol.blockchainUpdateQuery = False

    # -------------------------------------------------------------------------------------

    def getPeersList(self):
        
        # Creazione lista di ip dei peers online
        peersOnline = []
        
        for i in range(len(self.peersManager.peers_server)) :
            peersOnline.append(self.peersManager.peers_server[i])
            
        # Eliminazione ip del destinatario dalla lista
        if(self.dataClient[0] in peersOnline):
            peersOnline.remove(self.dataClient[0])

        # Calcolo lunghezza lista
        totPeers = len(peersOnline)

        # -- print("[TOT PEERS DA INVIARE]: %d" %(totPeers))

        totPeersToClient = str(totPeers)
        totPeersToClient = totPeersToClient.encode("ascii")

        # Invio lunghezza lista al client
        self.socketClient.send(totPeersToClient)

        for i in range(totPeers) :
            # Invio ip del peer online al client
            ipPeerOnline = peersOnline[i]
            # -- print(">> Inviato ip: %s" %(ipPeerOnline))
            ipPeerOnline = ipPeerOnline.encode("ascii")
            self.socketClient.send(ipPeerOnline)
            # Delay --> Evita concatenazione dati inviati
            time.sleep(0.05)


    def disconnectPeer(self):

        print("\n[---] Disconnessione da %s\n" %(self.dataClient[0]))
        # Peer client disconnesso
        # --> Rimozione ip dalla lista peers
        self.peersManager.peers_client.remove(self.dataClient[0])
        self.peersManager.peers_server.remove(self.dataClient[0])

        # Invia notifica disconnessione peer al browser
        globalVariables.variables.protocol.log.put("disconnectedPeer %s" %(self.dataClient[0]))

        # Termina connessione al peer client
        self.socketClient.close()
        
        
        


############################################################################################

def startNewPeerServer(server, peersManager):
    
    # Creazione nuovo client
    newServer = ServerThread(server, peersManager)

    # Esecuzione thread --> nuovo client
    newServer.start()

    # -- print("\n{ New ServerThread }\n")



