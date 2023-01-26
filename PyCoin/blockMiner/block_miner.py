
import random
import threading
import hashlib
import pickle
import time
import copy


class BlockMiner(threading.Thread):

    max_nonce  = 4294967295
    newBlock   = None

    def __init__(self, protocol):

        # Gestione interna al thread delle variabili del protocollo
        self.protocol = protocol

        # Inizializzazione thread
        threading.Thread.__init__(self)


    def run(self):

        # Attesa aggiornamento blockchain
        while(self.protocol.eventBlockchainUpdate == False):
            time.sleep(3)


        while True :

            # Se hash dell'header del nuovo blocco soddisfa la difficoltà attuale
            newBlock = self.tryNewNonce()

            if(newBlock != False):

                # Blocco generato

                # Inoltra blocco generato al protocollo
                self.protocol.query.put(("checkBlock", newBlock))

                # -- break

    # -------------------------------------------------------------------------------------

    def tryNewNonce(self):

        self.protocol.candidateBlock["tx_counter"] = len(self.protocol.candidateBlock["tx"])

        # Generazione ed inserimento del nonce nell'header
        self.protocol.candidateBlock["header"]["nonce"] = random.randint(1, self.max_nonce)

        # Inserimento time attuale nell'header del blocco
        self.protocol.candidateBlock["header"]["time"] = int(time.time())

        # Estrazione header
        header = self.protocol.candidateBlock["header"]

        # Generazione hash dell'header
        h = hashlib.sha256(pickle.dumps(header)).hexdigest()
        h_dec = int(h, 16)


        ## Controllo difficoltà hash --> Validità blocco

        if(h_dec > header["difficulty"]):

            # Blocco non valido
            return False


        else:

            # Memorizzazione hash del blocco generato
            self.protocol.candidateBlock["hash"] = h

            # Deep copy del nuovo blocco --> Evitare modifiche
            newBlock = copy.deepcopy(self.protocol.candidateBlock)
            
            print("\nNUOVO BLOCCO GENERATO (MINED) [ID: %s]\n" %(h))

            # Blocco valido
            return newBlock


