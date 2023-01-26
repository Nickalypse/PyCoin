
import threading
import queue
import pickle
import sqlite3
import json
import time
import rsa
import hashlib
import random
import base58
import base64
import copy


class Protocol(threading.Thread):

    log         = queue.Queue()  # Coda delle operazioni effettuate dal wallet --> Inoltrate al browser
    query       = queue.Queue()  # Coda delle richieste effettuate dal browser
    result      = queue.Queue()  # Coda dei risultati delle funzioni del protocollo --> Inoltrate al client
    updateData  = queue.Queue()  # Coda di blocchi per l'aggiornamento della blockchain

    # Dizionario contenente i valori delle chiavi rsa del wallet
    keys = {}

    # ID sessione --> Garantire confidenzialità nella generazione di una nuova transazione
    sessionID = None

    # Oggetti per la gestione della coppia di chiavi
    pubKeyObject   = None
    privKeyObject  = None

    # Lista di transazioni valide --> Da includere in un nuovo blocco
    transactions = []

    # Lista utxo utilizzati dalle transazioni del candidate block
    utxo = []

    # Blocchi confermati
    blocks = []

    # Totale di pycoin associati al proprio indirizzo
    pycoinAmmount = 0.0


    # Indice del blocco più recente nel database
    blockHeightIndex = 0

    # Blocco più recente
    lastBlock = None


    # Assume 'True' quando la blockchain locale è aggiornata
    eventBlockchainUpdate = False

    # Assume 'True' quando un peer richiede l'aggiornamento della propria blockchain
    blockchainUpdateQuery = False



    ## CONFIGURAZIONE DEL PROCESSO DI MINING ##############################################

    # Blocco elaborato dal processo di mining
    candidateBlock = {
        'header': {
            'hashPrevBlock': '',
            'merkleRoot': '',
            'difficulty': 0,
            'time': 0,
            'nonce': 0
        },
        'hash': '',
        'height': 0,
        'fee': 0.0,
        'tx_counter': 1,
        'tx': [
            {
                'txid': '',
                'in_counter': 1,
                'out_counter': 1,
                'in': [
                    {
                        'txid': '0000000000000000000000000000000000000000000000000000000000000000',
                        'index': -1,
                        'unlock': ''
                    }
                ],
                'out': [
                    {
                        'value': 0,
                        'recipient': '',
                        'spent': 'free'
                    }
                ]
            }
        ]
    }

    # Valore ricompensa per il miner che genera un nuovo blocco valido
    reward = 64.0

    # Istante generazione del primo blocco dal quale aggiornare la difficoltà
    time_first_block = None

    min_difficulty  = 110427941548649020598956093796432407239217743554726184882600387580788735
    max_difficulty  = 340282366920938463463374607431768211455
    max_nonce       = 4294967295

    # Indice di aggiornamento della difficoltà
    increment = 1.64

    # Difficoltà che i blocchi attuali devono rispettare
    actually_difficulty = None

    # Totale di blocchi dopo i quali aggiornare la difficoltà
    range_difficulty = 4

    # Tempo (s) ideale per la generazione di un singolo blocco
    ideal_time_for_block = 15
    
    # Calcolo del tempo ideale per la generazione un totale di blocchi
    # dopo i quali aggiornare la difficoltà
    ideal_time_for_range = range_difficulty * ideal_time_for_block

    #######################################################################################



    def __init__(self, db, querySpreader, peersManager):

        # Comunicazione con il thread che gestisce il database locale
        self.db = db
        # Gestione locale del querySpreader --> Aggiunta in coda di query per i client
        self.querySpreader = querySpreader
        # Gestione locale dei peers
        self.peersManager = peersManager

        # Estrazione chiave privata e indirizzo del wallet dal database
        self.getKeysFromDatabase()
        if(len(self.keys) == 0):
            # Generazione chiave pubblica e chiave privata
            self.generateKeys()

        # Generazione indirizzo wallet dalla chiava pubblica
        address = self.generateAddress(self.keys["n"], self.keys["e"])
        self.keys["address"] = address

        # Memorizzazione indirizzo nella transazione coinbase del candidate block
        self.candidateBlock["tx"][0]["out"][0]["recipient"] = self.keys["address"] 

        # Memorizzazione valore ricompensa nella transazione coinbase
        self.candidateBlock["tx"][0]["out"][0]["value"] = self.reward

        # Generazione ID sessione comunicazione con browser
        self.generateSessionID()
        # Inoltro ID sessione al browser
        self.log.put("id %s" %(self.sessionID))

        # Inizializzazione oggetto --> Gestione chiave pubblica
        self.pubKeyObject = rsa.PublicKey(int(self.keys["n"]), int(self.keys["e"]))
        # Inizializzazione oggetto --> Gestione chiave privata
        self.privKeyObject = rsa.PrivateKey(int(self.keys["n"]), int(self.keys["e"]), int(self.keys["d"]), int(self.keys["p"]), int(self.keys["q"]))

        # Inizializzazione thread
        threading.Thread.__init__(self)


    def run(self):

        # Collegamento al database
        try:
            dbConnection  = sqlite3.connect("blockchain/blockData.db")
            dbCursor      = dbConnection.cursor()
        except:
            print("ERRORE FATALE: '%s'" %("blockchain/blockData.db"))
            exit(-1)

        # Estrazione indice del blocco più recente dal database
        dbQuery = "SELECT MAX(height) FROM block"
        dbCursor.execute(dbQuery)
        results = dbCursor.fetchall()
        self.blockHeightIndex = results[0][0]

        print("ULTIMO BLOCCO MEMORIZZATO: %d" %(self.blockHeightIndex))

        # Termine connessione al database
        dbConnection.close()


        # Memorizzazione dell'ultimo blocco
        self.getLastBlock()

        # Estrazione dell'orario in cui è stato generato il primo blocco dell'intervallo
        # di aggiornamanto della difficoltà (Es: Ogni 4 blocchi aggiornare la difficoltà)
        index = (self.blockHeightIndex + 1) % self.range_difficulty
        if(index == 0):
            self.time_first_block = self.lastBlock["header"]["time"]
        elif(self.blockHeightIndex < 3):
            block = self.extractBlock(0, False)
            self.time_first_block = block["header"]["time"]
        else:
            block = self.extractBlock((self.blockHeightIndex - index), False)
            self.time_first_block = block["header"]["time"]


        # Estrazione difficoltà attuale
        self.actually_difficulty = self.lastBlock["header"]["difficulty"]


        # Calcolo totale pycoin associati al proprio indirizzo
        self.pycoinAmmount = self.calculatePycoinAmmount(self.keys["address"])
        print("\nPYCOIN POSSEDUTI: {0:.8f}".format(self.pycoinAmmount))
        # Inoltro totale pycoin al browser
        self.log.put("pycoin {0:.8f}".format(self.pycoinAmmount))


        # Attesa connessione iniziale alla rete p2p
        while(len(self.peersManager.peers_server) == 0):
            time.sleep(3)

        # . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

        # Aggiorna blockchain
        self.blockchainUpdate()

        # Inizializzazione del candidate block per il processo di mining
        self.resetCandidateBlock()


        while True :

            # Estrazione richiesta da coda
            query = self.query.get()

            operation  = query[0]
            data       = query[1]

            ## Controllo validità blocco
            if(operation == "checkBlock"):
                self.checkBlockOption(data)


            ## Controllo validità transazione
            elif(operation == "checkTransaction"):
                print("[PROTOCOL] Check Transaction")
                print("\n----------\n{}\n----------\n".format(data))

                result = self.checkTransaction(data, False)

                if(result != -1):

                    # Transazione valida
                    fee = result

                    # -- print(self.utxo)

                    # Inserimento transazione del candidate block
                    self.updateCandidateBlock(data, fee)

                    # TXID aggiunto alla lista delle transazioni del candidate block
                    self.transactions.append(data["txid"])

                    # Inoltro transazione ricevuta al browser
                    self.log.put("transaction %s %s %f" %(data["txid"], data["out"][0]["recipient"], data["out"][0]["value"]))


                else:

                    print("TRANSAZIONE NON VALIDA")


            ## Generazione nuova transazione
            elif(operation == "newTransaction"):
                self.generateTransactionOption(data)



    ### METODI ##########################################################################

    def checkBlockOption(self, block):

        print("\n-----------------\n{}\n----------------\n".format(block))

        # Controllo validità del blocco
        result = self.checkBlock(block)

        # Nuovo blocco valido
        if(result == True):

            print("[+++] NUOVO BLOCCO AGGIUNTO ALLA BLOCKCHAIN\n[ID: %s]\n" %(block["hash"]))

            # Creazione file json del nuovo blocco
            self.createBlockFile(block)

            # Collegamento al database ---------------------------------------------------
            try:
                dbConnection  = sqlite3.connect("blockchain/blockData.db")
                dbCursor      = dbConnection.cursor()
            except:
                print("ERRORE FATALE: '%s'" %("blockchain/blockData.db"))
                input("")
                exit(-1)
            # Aggiunta nuovo blocco al database
            dbQuery = "INSERT INTO block VALUES ('%s', '%s')" %(block["hash"], block["height"])
            dbCursor.execute(dbQuery)
            dbConnection.commit()
            # Termine connessione al database
            dbConnection.close()
            # ----------------------------------------------------------------------------

            ## Verifica se aggiornare la difficoltà --------------------------------------
            if((self.blockHeightIndex + 1) % self.range_difficulty == 0):

                # Rapporto tra tempo trascorso e tempo ideale
                relation_time = (block["header"]["time"] - self.time_first_block) / self.ideal_time_for_range

                # Generazione nuova difficoltà
                self.difficultyUpdate(relation_time)

                # Aggiornamento tempo iniziale
                self.time_first_block = block["header"]["time"]
                
                print("\nRAPPORTO TEMPO TRASCORSO / TEMPO IDEALE: {}\n".format(relation_time))
                self.log.put("relationTime %f" %(relation_time))
            ## ---------------------------------------------------------------------------

            # Incremento indice blocco attuale
            self.blockHeightIndex += 1

            # Memorizzazione blocco più recente
            self.lastBlock = copy.deepcopy(block)

            # Eliminazione transazioni confermate dal candidate block
            for tx in block["tx"]:
                if(tx["txid"] in self.transactions):
                    # Inoltro conferma della transazione al browser
                    self.log.put("confirmedTransaction %s %s %f" %(tx["txid"], tx["out"][0]["recipient"], tx["out"][0]["value"]))
                    # Rimozione transazione da lista
                    self.transactions.remove(tx["txid"])
                    print("[+] Confermata transazione %s" %(tx["txid"]))

            # Aggiornamento del candidate block
            self.resetCandidateBlock()


            # Aggiornamento totale pycoin posseduti
            if(block["tx"][0]["out"][0]["recipient"] == self.keys["address"]):
                """
                # Estrazione valore della transazione coinbase destinata al mio indirizzo
                coinbaseValue = block["tx"][0]["out"][0]["value"]
                # Aumento totale pycoin posseduti
                self.pycoinAmmount = float("{0:.8f}".format(self.pycoinAmmount + coinbaseValue))
                
                # Aggiornamento pannello browser
                self.log.put("pycoin %f" %(self.pycoinAmmount))
                """
                self.log.put("blockMined %s %s %s %s %s %s %s" %(block["height"], block["header"]["time"], block["hash"], block["tx"][0]["out"][0]["recipient"], block["tx"][0]["out"][0]["value"], block["fee"], block["tx_counter"]))

            else:
                # Aggiornamento pannello browser
                self.log.put("block %s %s %s %s %s %s %s" %(block["height"], block["header"]["time"], block["hash"], block["tx"][0]["out"][0]["recipient"], block["tx"][0]["out"][0]["value"], block["fee"], block["tx_counter"]))


            # Aggiornamento stato utxo --> da 'free' a 'spent'
            for utxo in self.utxo:
                
                height  = utxo[0]
                txid    = utxo[1]
                index   = utxo[2]

                print(utxo)

                # Estrazione blocco contenente utxo
                block = self.extractBlock(height, False)

                # Ricerca transazione con utxo
                for tx in block["tx"]:
                    if(tx["txid"] == txid):
                        tx["out"][index]["spent"] = "spent"
                        break

                # Sovrascrizione con nuovo blocco contenente stato degli utxo aggiornato
                self.createBlockFile(block)


            # Calcolo attuale totale di pycoin
            self.pycoinAmmount = self.calculatePycoinAmmount(self.keys["address"])
            print("\nPYCOIN POSSEDUTI: {0:.8f}".format(self.pycoinAmmount))
            # Inoltro totale pycoin al browser
            self.log.put("pycoin {0:.8f}".format(self.pycoinAmmount))


            # Svuota lista di utxo utilizzati dalle transazioni del candidate block
            self.utxo = []

            # >> Invio del blocco agli altri nodi connessi alla rete p2p
            self.querySpreader.query_to_peer.put(("sendBlock", self.lastBlock))


        else:
            pass
            # -- print("\nBLOCCO SCARTATO [ID: %s]\n" %(block["hash"]))


        # Inoltra esito controllo del blocco al peer client 
        self.result.put(result)


    # ----------------------------------------------------------------------------------

    def resetCandidateBlock(self):

        ## Aggiornamento hash blocco precedente del candidate block
        self.candidateBlock["header"]["hashPrevBlock"] = self.lastBlock["hash"]

        ## Aggiornamento height del candidate block
        self.candidateBlock["height"] = self.blockHeightIndex + 1

        ## Aggiornamento difficoltà del candidate block
        self.candidateBlock["header"]["difficulty"] = self.actually_difficulty

        ## Rispristino fee del candidate block
        self.candidateBlock["fee"] = 0.0


        flagCoinbase = True

        for tx in self.candidateBlock["tx"]:
            if(flagCoinbase == False):
                # Eliminazione transazione se già confermata nel nuovo blocco
                if(tx in self.lastBlock["tx"]):
                    self.candidateBlock["tx"].remove(tx)
            else:
                flagCoinbase = False
                    

        # Memorizzazione valore ricompensa nella transazione coinbase
        self.candidateBlock["tx"][0]["out"][0]["value"] = self.reward

        # Memorizzazione valore ricompensa nella transazione coinbase
        self.candidateBlock["tx"][0]["in"][0]["unlock"] = str(random.randint(1, self.max_nonce))

        # Generazione txid della coinbase transaction
        self.candidateBlock["tx"][0]["txid"] = self.generateTXID(self.candidateBlock["tx"][0])

        # Generazione merkle root del candidate block
        self.candidateBlock["header"]["merkleRoot"] = self.generateMerkleRoot(self.candidateBlock["tx"])

        ## Ripristino totale transazioni
        self.candidateBlock["tx_counter"] = len(self.candidateBlock["tx"])


    # ----------------------------------------------------------------------------------

    def blockchainUpdate(self):

        # Inoltra richiesta di aggiornamento blockchain ai peers client
        self.querySpreader.query_to_peer.put(("updateBlockchain", ""))

        # Attesa conclusione aggiornamento blockchain
        while(self.eventBlockchainUpdate == False):
            time.sleep(2)


    # -----------------------------------------------------------------------------------

    def updateCandidateBlock(self, tx, fee):

        # Transazione aggiunta al candidate block
        self.candidateBlock["tx"].append(copy.deepcopy(tx))

        # Aggiornamento totale transazioni
        self.candidateBlock["tx_counter"] = len(self.candidateBlock["tx"])

        # Incementato fee totale
        fee = float(fee)
        fee = float("{0:.8f}".format(fee))
        if(fee != 0):
            # Aggiornamento fee del blocco
            self.candidateBlock["fee"] = float("{0:.8f}".format(self.candidateBlock["fee"] + fee))
            # Aggiornamento valore della transazione coinbase (reward + fee)
            reward = self.candidateBlock["tx"][0]["out"][0]["value"]
            self.candidateBlock["tx"][0]["out"][0]["value"] = float("{0:.8f}".format(reward + fee))
            # Aggiornamento txid della transazione coinbase
            txid = self.generateTXID(self.candidateBlock["tx"][0])
            self.candidateBlock["tx"][0]["txid"] = txid

        # Aggiornamento merkle root
        self.candidateBlock["header"]["merkleRoot"] = self.generateMerkleRoot(self.candidateBlock["tx"])


    # -----------------------------------------------------------------------------------

    def generateTransactionOption(self, data):

        # Estrazione dati transazione
        sessionID  = data[0]
        recipient  = data[1]
        value      = data[2]
        fee        = data[3]

        # Elimina richiesta transazione non autorizzata
        if(sessionID == self.sessionID):

            # Genera nuova transazione
            result, tx = self.generateTransaction(recipient, value, fee)

            # Controllo validità nuova transazione
            if(result == True):
                self.log.put("generatedTransaction %s" %(tx["txid"]))

                print(self.utxo)

                # Transazione aggiunta al candidate block
                self.updateCandidateBlock(tx, fee)

                # >> Transazione inviata ai peers connessi alla rete p2p
                self.querySpreader.query_to_peer.put(("sendTransaction", tx))

                # TXID aggiunto alla lista delle transazioni generate
                self.transactions.append(tx["txid"])

            else:
                # Indirizzo destinatario transazione non valido
                self.log.put(result)


    # -----------------------------------------------------------------------------------

    def generateTransaction(self, recipient, value, fee):

        # Controllo validità quantitativo di pycoin
        try:
            value = float(value)
            value = float("{0:.8f}".format(value))
        except:
            return ("errorValue", None)

        try:
            fee = float(fee)
            fee = float("{0:.8f}".format(fee))
        except:
            return ("errorFee", None)

        if(value <= 0):
            return ("errorValue", None)

        if(fee < 0):
            return ("errorFee", None)


        # Controllo validità indirizzo
        if(self.checkAddress(recipient) == False):
            return ("errorAddress", None)


        # Calcolo totale minimo di pycoin necessari per generare la transazione
        total = float("{0:.8f}".format(value + fee))

        # Controllo disponibilità quantitativo pycoin
        if(total > self.pycoinAmmount):
            print("#1")
            return ("errorAmmount", None)


        # Struttura transazione
        new_tx = {
            'txid': '',
            'in_counter': 1,
            'out_counter': 1,
            'in': [],
            'out': []
        }


        # Totale di pycoin contenuti negli utxo utilizzati
        utxoValue = []

        # Raggiunti sufficienti utxo per generare la nuova transazione
        ready = False


        # [[height, txid_utxo, index_utxo], ]
        utxo = []


        # Ricerca nella blockchain di utxo disponibili
        for height in range(1, (self.blockHeightIndex + 1)):

            # Estrazione blocco da file json
            block = self.extractBlock(height, False)

            # Estrazione singole transazioni
            for tx in block["tx"]:

                # Estrazione singoli output della transazione
                for i in range(len(tx["out"])):

                    # Controllo se utxo destinato al mio indirizzo
                    if(tx["out"][i]["recipient"] == self.keys["address"]):
                        # Controllo se utxo è disponibile
                        if(tx["out"][i]["spent"] == "free"):

                            utxoFlag = [height, tx["txid"], i]

                            # Controllo che l'utxo non sia utilizzato da altre transazioni
                            # contnute nel candidate block
                            if(not utxoFlag in self.utxo):

                                # Memorizzazione dati uxto
                                utxo.append(utxoFlag)

                                # Memorizzazione quantitativo pycoin utxo
                                utxoValue.append(tx["out"][i]["value"])

                                # Generazione input
                                new_in = {
                                    'txid': tx["txid"],
                                    'index': i,
                                    'unlock': self.generateUnlock(tx["txid"])
                                }

                                # Inserimento input nella nuova transazione
                                new_tx["in"].append(copy.deepcopy(new_in))

                                # Calcolo valore totale degli utxo utilizzati per generare
                                # la nuova transazione
                                full_utxo_value = float("{0:.8f}".format( sum(utxoValue) ))

                                # Se totale della transazione richiesta raggiunto viene
                                # generata la nuova transazione
                                if(full_utxo_value >= total):
                                    ready = True
                                    break

                if(ready == True):
                    break

            if(ready == True):
                    break


        # Transazione non generata se valore utxo non sufficiente
        if(ready == False):
            print("#2")
            return ("errorAmmount", None)

        # Memorizzazione dati degli utxo
        self.utxo.extend(utxo)

        # Generazione output destinatario
        new_out = {
            'value': value,
            'recipient': recipient,
            'spent': 'free'
        }
        # Output aggiunto alla transazione
        new_tx["out"].append(copy.deepcopy(new_out))


        # Calcolo del resto da riaccreditare all'indirizzo mittente della transazione
        rest = float("{0:.8f}".format(full_utxo_value - value - fee))

        if(rest != 0):

            # Generazione output resto
            new_out = {
                'value': rest,
                'recipient': self.keys["address"],
                'spent': 'free'
            }
            # Output aggiunto alla transazione
            new_tx["out"].append(copy.deepcopy(new_out))


        # Memorizzazione totale di input e di output nella transazione
        new_tx["in_counter"]   = len(new_tx["in"])
        new_tx["out_counter"]  = len(new_tx["out"])

        # Generazione txid della nuova transazione
        new_tx["txid"] = self.generateTXID(new_tx)

        print("\n[+] Transazione generata:\n    --> Inviati %f pycoin all'indirizzo %s\n    <-- Ricevuto resto di %f pycoin\n    *** Mancia offerta al miner di %f pycoin\n[i] Attesa convalida del blocco che la contiene\n" %(value, recipient[:8]+"..."+recipient[-8:], rest, fee))
        # Ritorna nuova transazione generata
        return (True, copy.deepcopy(new_tx))


    # -----------------------------------------------------------------------------------

    def checkBlock(self, block):

        # Controllo height del blocco
        if(block["height"] != (self.lastBlock["height"]+1)):

            # Estrazione del blocco
            oldBlock = self.extractBlock(block["height"], False)

            """
            print("\n-------------------\n{}\n-------------------\n".format(oldBlock))
            print("\n___________________\n{}\n___________________\n".format(block))
            """

            # Controllo hash del blocco precedente
            try:
                if(oldBlock["header"]["hashPrevBlock"] == block["header"]["hashPrevBlock"]):

                    # Controllo tempo creazione blocco
                    if(block["header"]["time"] < oldBlock["header"]["time"]):

                        # Collegamento al database --------------------------------------
                        try:
                            dbConnection  = sqlite3.connect("blockchain/blockData.db")
                            dbCursor      = dbConnection.cursor()
                        except:
                            print("ERRORE FATALE: '%s'" %("blockchain/blockData.db"))
                            exit(-1)

                        # Estrazione indice del blocco più recente dal database
                        dbQuery = "DELETE FROM block WHERE height = %d" %(block["height"])
                        dbCursor.execute(dbQuery)
                        dbConnection.commit()

                        dbQuery = "INSERT INTO block VALUES ('%s', '%d')" %(block["hash"], block["height"])
                        dbCursor.execute(dbQuery)
                        dbConnection.commit()

                        # Termine connessione al database
                        dbConnection.close()
                        # --------------------------------------------------------------

                        # Sovrascrive blocco
                        self.createBlockFile(block)

                    else:
                        print("@ERRORE height")
                        return False
                else:
                    print("@ERRORE height")
                    return False
            except:
                return False


        # Controllo time generazione blocco
        if(block["header"]["time"] < self.lastBlock["header"]["time"]):
            print("@ERRORE time")
            return False

        # Controllo difficoltà con  attuale
        if(block["header"]["difficulty"] != self.actually_difficulty):
            print("@ERRORE difficulty diversa")
            return False

        # Controllo hash del blocco precedente
        if(block["header"]["hashPrevBlock"] != self.lastBlock["hash"]):
            print("@ERRORE hash non rispetta difficulty")
            return False

        # Controllo hash del blocco
        if(block["hash"] != self.generateHashBlockHeader(block["header"])):
            print("@ERRORE hash generato diverso da hash memorizzato nel blocco")
            return False

        # Controllo nonce
        if(self.checkBlockHeader(block["header"]) == False):
            print("@ERRORE hash - block header")
            return False

        # Controllo merkle root
        if(self.checkMerkleRoot(block["header"]["merkleRoot"], block["tx"]) == False):
            print("@ERRORE merkle root")
            return False

        # Controllo totale transazioni
        if(block["tx_counter"] != len(block["tx"])):
            print("@ERRORE totale transazioni")
            return False


        # Totale fee del blocco
        fee = 0.0

        # Controllo singole transazioni
        for i in range(1, len(block["tx"])):
            # Estrazione transazione
            tx = block["tx"][i]

            # Controllo validità singola transazione
            result = self.checkTransaction(tx, True)

            # Transazione non valida
            if(result == -1):
                print("@ERRORE transazione")

                """
                if(self.candidateBlock["tx"][i]["txid"] == tx["txid"]):
                    # Transazione rimossa dal candidate block
                    self.candidateBlock["tx"][i].pop()
                    try:
                        self.transactions.remove(tx["txid"])
                    except:
                        pass
                """

                return False

            # Calcolo fee della transazione
            fee += result



        # -- print("[FEE] %f" %(fee))


        # Controllo transazione coinbase
        if(self.checkCoinbaseTransaction(block["tx"][0], fee) == False):
            print("@ERRORE transazione coinbase")
            return False

        # Controllo fee del blocco
        if(block["fee"] != float("{0:.8f}".format(fee))):
            print("@ERRORE fee")
            return False


        # Blocco valido
        return True


    # -----------------------------------------------------------------------------------

    def checkTransaction(self, tx, blockQuery):

        # Controllo totale transazioni in input
        if((tx["in_counter"] != len(tx["in"])) or (tx["in_counter"] <= 0)):
            print("#ERRORE in_counter")
            return -1

        # Controllo totale transazioni in output
        if((tx["out_counter"] != len(tx["out"])) or (tx["in_counter"] <= 0)):
            print("#ERRORE out_counter")
            return -1

        # Controllo txid
        if(tx["txid"] != self.generateTXID(tx)):
            print("#ERRORE txid generato")
            return -1


        tot_out  = 0.0
        tot_in   = 0.0


        ## Controllo singoli output -----------------------------
        for out in tx["out"]:

            # Controllo indirizzo destinatario
            if(self.checkAddress(out["recipient"]) == False):
                print("#ERRORE indirizzo output non valido")
                return -1

            # Controllo stato transazione (free / spent)
            if(out["spent"] != "free"):
                print("#ERRORE spent output non default ('free')")
                return -1

            # Calcolo totale pycoin inviati ai destinatari
            tot_out += out["value"]


        # [[height, txid_utxo, index_utxo], ]

        ## Controllo singoli input ------------------------------
        for in_tx in tx["in"]:

            # Cerca nella blockchain l'output di una specifica transazione e
            # ritorna height, indice transazione del blocco che la contiene e output
            # Ritorna False se transazione non trovata o già spesa

            data = self.searchUTXO(in_tx["txid"], in_tx["index"])

            # return (height, tx["out"][index]["value"], tx["out"][index]["recipient"])

            # return (1, 64.0, destinatario_utxo)

            # Transazione non valida o non trovata
            if(data == False):
                print("#ERRORE ricerca UTXO")
                return -1

            # Estrazione dati sul blocco contenente l'utxo utlizziato dalla transazione
            height     = data[0]  # 1                  (height)
            value      = data[1]  # 64.0               (valore utxo)
            recipient  = data[2]  # destinatario_utxo  (address che può sbloccare)


            # Memorizzazione height, txid e index per evitare transazioni
            # che utilizzano lo stesso utxo
            if(blockQuery == False):
                self.utxo.append( [height, in_tx["txid"], in_tx["index"]] )


            ### VALID BLOCK --> SET TO 'SPENT'


            # Controllo unlock
            if(self.checkUnlock(recipient, in_tx["unlock"], in_tx["txid"]) == False):
                return -1

            # Calcolo totale pycoin acquisiti per la transazione
            tot_in += value


        tot_in   = float("{0:.8f}".format(tot_in))
        tot_out  = float("{0:.8f}".format(tot_out))

        ## Controllo validità totale pycoin inviati
        if(tot_out > tot_in):
            print("#ERRORE out > in")
            return -1

        # Calcolo fee della transazione
        transactionFee = float("{0:.8f}".format(tot_in - tot_out))
        
        if(blockQuery == False):
            print("\n[+] Transazione ricevuta - [TXID]: %s" %(tx["txid"][:8]+"..."+tx["txid"][-8:]))
            print("[i] Indirizzo mittente della transazione: %s" %(recipient[:8]+"..."+recipient[-8:]))
            value      = tx["out"][0]["value"]
            recipient  = tx["out"][0]["recipient"]
            print("    --> Inviati %f pycoin all'indirizzo %s" %(value, recipient[:8]+"..."+recipient[-8:]))
            if(tx["out_counter"] == 2):
                value = tx["out"][1]["value"]
                print("    <-- Ricevuto resto di %f pycoin" %(value))
            print("    *** Mancia offerta al miner di %f pycoin" %(transactionFee))
            print("[i] Attesa convalida del blocco che la contiene\n")


        # Transazione valida --> Ritorna fee della transazione
        return transactionFee


    # -----------------------------------------------------------------------------------

    def checkCoinbaseTransaction(self, tx, fee):

        # Controllo totale input
        if(tx["in_counter"] != 1):
            return False
        if(len(tx["in"]) != 1):
            return False

        # Controllo totale output
        if(tx["out_counter"] != 1):
            return False
        if(len(tx["out"]) != 1):
            return False

        # Controllo txid input
        if(tx["in"][0]["txid"] != "0000000000000000000000000000000000000000000000000000000000000000"):
            return False

        # Controllo indice input
        if(tx["in"][0]["index"] != -1):
            return False

        # Controllo txid
        if(tx["txid"] != self.generateTXID(tx)):
            return False

        # Controllo output
        if(self.checkAddress(tx["out"][0]["recipient"]) == False):
            return False

        """
        # Controllo stato transazione
        if(tx["out"][0]["spent"] != "free"):
            return False
        """

        # Calcolo output del blocco --> Approssimazione ad 8 cifre decimali
        output = self.reward + fee
        output = float("{0:.8f}".format(output))

        # Controllo output del blocco
        # Valore corrispondente a somma tra reward e fee totale
        if(tx["out"][0]["value"] != output):
            return False

        # Transazione valida
        return True


    # -----------------------------------------------------------------------------------

    def generateUnlock(self, txid):

        # Inserimento chiave pubblica in unlock
        unlock = str(self.keys["n"]) + " " + str(self.keys["e"]) + " "

        # Generazione firma digitale txid
        sign = rsa.sign(txid.encode("ascii"), self.privKeyObject, "SHA-256")
        # Codifica base64 della firma dicitale
        sign = base64.b64encode(sign)
        # Conversione in stringa della firma digitale
        sign = str(sign)[2:-1]

        # Inserimento firma digitale in unlock
        unlock += sign

        return unlock


    # -----------------------------------------------------------------------------------

    def checkUnlock(self, recipient, unlock, txid):

        # (recipient, in_tx["unlock"], in_tx["txid"])

        # Estrazione dati da stringa di unlock
        data = unlock.split(" ")

        # Controllo totale di parametri necessari
        if(len(data) != 3):
            return False

        # Estrazione valori chiave pubblica rsa
        n          = int(data[0])
        e          = int(data[1])
        signature  = data[2]


        # Indirizzo wallet nell'utxo non corrispondente all'indirizzo
        # generato dalla chiave pubblica presente in unlock
        if(self.generateAddress(n, e) != recipient):
            print("#ERRORE address destinatario non corrispondente")
            return False


        # -- print("\n[RECIPIENT UTXO]: %s\n" %(recipient))
        # -- print("\n[SINGATURE]: %s\n" %(signature))
        # -- print("\n[TXID UTXO]: %s\n" %(txid))


        # Estrazione firma digitale dell'id dell'utxo
        signature = base64.b64decode(signature.encode("ascii"))


        # -- print("\n[SIGNATURE DECODE]:\n{}\n".format(signature))


        # Controllo firma digitale dell'id dell'utxo attraverso chiave pubblica data
        try:
            pubKeyObject = rsa.PublicKey(n, e)
            rsa.verify(txid.encode("ascii"), signature, pubKeyObject)
        except:
            print("#ERRORE signature")
            return False

        # Firma digitale corretta --> Indirizzo è abilitato all'acquisizione dell'utxo
        return True


    # -----------------------------------------------------------------------------------

    def searchUTXO(self, txid, index):

        # Ricerca transazione nella blockchain
        for height in range(1, (self.blockHeightIndex + 1)):

            # Estrazione blocco data height
            block = self.extractBlock(height, False)

            # Ricerca transazione nel blocco
            for tx_index in range(0, block["tx_counter"]):

                # Estrazione transazione
                tx = block["tx"][tx_index]

                # Se txid trovato
                if(tx["txid"] == txid):
                    # Se indice output specifico compreso nel totale di output
                    if(index < tx["out_counter"]):
                        # Se transazione non spesa
                        if(tx["out"][index]["spent"] == "free"):
                            # Transazione valida
                            return (height, tx["out"][index]["value"], tx["out"][index]["recipient"])
                        else:
                            # UTXO già speso
                            print("#ERRORE utxo già speso")
                            return False
                    else:
                        # Indice out non valido
                        print("#ERRORE indice non valido")
                        return False

        # Transazione non trovata
        return False


    # -----------------------------------------------------------------------------------

    def generateTXID(self, tx):

        # Rimozione txid
        backup_txid = tx.pop("txid")

        # Rimozione stato output (speso/non speso)
        for out in tx["out"]:
            out.pop("spent")

        # Generazione hash della transazione (txid)
        txid = pickle.dumps(tx)
        txid = hashlib.sha256(txid).hexdigest()

        # --------------------------------------------

        # Ripristino txid
        tx["txid"] = backup_txid

        # Ripristino stato output
        for out in tx["out"]:
            # Rimozione stato output (speso/non speso)
            out["spent"] = "free"

        return txid


    # -----------------------------------------------------------------------------------

    def getLastBlock(self):

        # Memorizzazione dell'ultimo blocco
        self.lastBlock = self.extractBlock(self.blockHeightIndex, False)


    # -----------------------------------------------------------------------------------

    def extractBlock(self, blockHeight, update):

        # Apertura file json contenente il blocco
        try:
            file = open("blockchain/"+str(blockHeight)+".json", "r")
        except:
            # Gestione errore se blocco non esistente
            if(update == True):
                self.updateData.put("inexistentBlock")
            else:
                return "inexistentBlock"
        else:
            content = file.read()
            file.close()

            block = json.loads(content)

            if(update == True):
                self.updateData.put(block)
            else:
                return block


    # -----------------------------------------------------------------------------------

    def calculatePycoinAmmount(self, address):

        # Totale di pycoin associati all'indirizzo
        pycoinAmmount = 0.0

        # Controllo utxo non spesi associati
        for height in range(1, (self.blockHeightIndex + 1)):

            # Estrazione blocco da file json
            block = self.extractBlock(height, False)

            # Controllo di ogni transazione
            for tx in block["tx"]:
                # Controllo di ogni output
                for out in tx["out"]:
                    # Se indirizzo destinatario dell'utxo corrispondente
                    if(out["recipient"] == address):
                        # Se utxo non utilizzato
                        if(out["spent"] == "free"):
                            # Valore di pycoin disponibile
                            pycoinAmmount += out["value"]


        # Calcolo output del blocco --> Approssimazione ad 8 cifre decimali
        pycoinAmmount = float("{0:.8f}".format(pycoinAmmount))

        # Memorizzazione del totale di pycoin disponibili
        return pycoinAmmount


    # -----------------------------------------------------------------------------------

    def generateSessionID(self):

        # Genera hash dei valori rsa
        rsaData = pickle.dumps(self.keys)
        h = hashlib.sha256(rsaData).hexdigest()

        # Memorizzazione id sessione
        self.sessionID = h


    # -----------------------------------------------------------------------------------


















    ######################################################################################

    def difficultyUpdate(self, relation_time):

        # Se è trascorso meno tempo rispetto al valore ideale
        # allora difficoltà aumentata
        if(relation_time < 1):
            self.actually_difficulty = int(self.actually_difficulty / self.increment)
            print("\n[+] DIFFICOLTA' AUMENTATA\n")

        # Se è trascorso più tempo rispetto al valore ideale
        # allora difficoltà ridotta
        if(relation_time > 1):
            self.actually_difficulty = int(self.actually_difficulty * self.increment)
            print("\n[-] DIFFICOLTA' RIDOTTA\n")

        # Inserimento difficoltà attuale nell'header del blocco
        self.candidateBlock["header"]["difficulty"] = self.actually_difficulty


    ######################################################################################

    def generateMerkleRoot(self, transactions):

        merkle_tree = []    

        # Generazione del primo livello del merkle tree
        for tx in transactions:
            merkle_tree.append(tx["txid"])

        # Se presente una sola transazione, ne duplico l'hash
        if(len(merkle_tree) %2 != 0):
            merkle_tree.append(merkle_tree[-1])

        # Generazione merkle root
        while(len(merkle_tree) != 1):
            # Se il totale di hash è dispari ne duplico l'ultimo
            # al fine di operare sempre con coppie di hash
            if(len(merkle_tree) %2 != 0):
                merkle_tree.append(merkle_tree[-1])

            tot = len(merkle_tree)

            # Generazione hash delle coppie
            for i in range(0, tot, 2):
                h1 = merkle_tree[i]
                h2 = merkle_tree[i+1]
                h12 = hashlib.sha256((h1+h2).encode("ascii")).hexdigest()
                merkle_tree.append(h12)

            merkle_tree = merkle_tree[tot:]

        return merkle_tree[0]


    # ------------------------------------------------------------------------------------

    def generateHashBlockHeader(self, header):

        header = pickle.dumps(header)
        h = hashlib.sha256(header).hexdigest()

        return h


    # ------------------------------------------------------------------------------------

    def checkBlockHeader(self, header):

        # Generazione hash (decimale) header del blocco
        h = self.generateHashBlockHeader(header)
        h_dec = int(h, 16)

        # Controllo conformità alla difficoltà
        if(h_dec > self.actually_difficulty):
            # Header blocco non valido
            return False
        else:
            # Header blocco valido
            return True


    # ------------------------------------------------------------------------------------

    def checkMerkleRoot(self, merkleRoot, tx):

        if(merkleRoot == self.generateMerkleRoot(tx)):
            # Merkle root valido
            return True
        else:
            # Merkle root non valido
            return False


    # ------------------------------------------------------------------------------------

    def getKeysFromDatabase(self):

        # Estrazione chiave privata e indirizzo del wallet dal database
        self.db.operations.put(("getKeys", ""))
        key = self.db.results.get()

        if(len(key) != 0):
            # Memorizzazione dati del profilo
            self.keys = {
                "n" : key[0],
                "e" : key[1],
                "d" : key[2],
                "p" : key[3],
                "q" : key[4]
            }
        else:
            self.keys = {}


    # ---------------------------------------------------------------------------------------------

    def generateKeys(self):

        # Generazione coppia chiavi RSA --> 2048 bit
        print("\n[...] Generazione coppia chiavi RSA (2048)\n")
        pub, priv = rsa.newkeys(2048)
        print("\n[>>>] Chiavi RSA generate\n")

        # Estrazione valori che compongono le chiavi
        self.keys = {
            "n" : pub.n,
            "e" : pub.e,
            "d" : priv.d,
            "p" : priv.p,
            "q" : priv.q
        }

        # Memorizzazione chiavi nel database
        self.db.operations.put(( "addKeys", self.keys))


    # ---------------------------------------------------------------------------------------------

    def generateAddress(self, n, e):

        # Estrazione valori che compongono la chiave pubblica (da classe --> a stringa)
        pub = "%s %s" %(n, e)

        # Generazione ripemd-160 da hash
        ripemd_160 = hashlib.new("ripemd160")
        ripemd_160.update(pub.encode("ascii"))
        address = ripemd_160.hexdigest()

        # Doppio hash sha-256
        checksum = hashlib.sha256(address.encode("ascii")).digest()
        checksum = hashlib.sha256(checksum).hexdigest()

        # Inserimento checksum
        address = "00" + address + checksum[-8:]

        # Codifica in base58
        address = base58.b58encode(address)
        address = address.decode("ascii")

        # -- print("\nMY ADDRESS: %s\n" %(address))

        return address


    # ---------------------------------------------------------------------------------------------

    def checkAddress(self, address):

        # Decodifica in base58 dell'indirizzo
        try:
            address = str(base58.b58decode(address))[2:-1]
        except:
            return False

        # Controllo intestazione
        if not address.startswith("00"):
            return False

        # Rimozione intestazione
        address = address[2:]

        # Estrazione checksum
        checksum = address[-8:]

        # Estrazione hash della chiave pubblica
        publicKeyHash = address[:-8]

        # Generazione hash per checksum
        hashCheck = hashlib.sha256(publicKeyHash.encode("ascii")).digest()
        hashCheck = hashlib.sha256(hashCheck).hexdigest()
        hashCheck = hashCheck[-8:]

        # Controllo checksum
        if(hashCheck != checksum):
            return False

        # Indirizzo valido
        return True

    # -----------------------------------------------------------------------------------

    def createBlockFile(self, block):

        # Creazione file json
        file = open("blockchain/" + str(block["height"]) + ".json", "w")
        # Memorizzazione blocco in formato json
        file.write(json.dumps(block))
        # Chiusura file
        file.close()


    # -----------------------------------------------------------------------------------











    # ===================================================================================

    def dbConnect(self):
        try:
            self.dbConnection = sqlite3.connect(self.dbFileName)
            self.dbCursor = self.dbConnection.cursor()
        except:
            print("FATAL ERROR: '%s' NOT WORK." %(self.dbFileName))
            exit(-1)


    def dbDisconnect(self):
        self.dbConnection.close()
        self.dbConnection = None
        self.dbCursor = None


    # ===================================================================================

