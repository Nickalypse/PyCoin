
import random
import threading
import hashlib
import pickle
import time
import json


class BlockMiner(threading.Thread):

    actually_difficulty = 110427941548649020598956093796432407239217743554726184882600387580788735
    max_nonce = 4294967295


    def __init__(self):

        blockHeight = 1
        print("\nBLOCK %d\n" %(blockHeight))

        # Estrazione blocco
        file = open(str(blockHeight)+".json")
        content = file.read()
        file.close()

        block = json.loads(content)

        self.header = block["header"]

        # Inizializzazione thread
        threading.Thread.__init__(self)


    def run(self):

        while True :

            # Se hash header del blocco soddisfa difficoltà attuale --> nonce valido

            if(self.tryNewNonce() == 1):

                print(self.header)
                print(hashlib.sha256(pickle.dumps(self.header)).hexdigest(), "\n")


    # -------------------------------------------------------------------------------------

    def tryNewNonce(self):

        # Generazione ed inserimento del nonce nell'header
        self.header["nonce"] = random.randint(1, self.max_nonce)

        # Inserimento time attuale nell'header del blocco
        self.header["time"] = int(time.time())

        # Generazione hash dell'header
        h = hashlib.sha256(pickle.dumps(self.header)).hexdigest()
        h_dec = int(h, 16)

        # Controllo se l'hash ha valore minore della difficoltà attuale
        if(h_dec > self.actually_difficulty):
            return 0
        else:
            return 1


# MAIN

miner = BlockMiner()
miner.start()

miner.join()


