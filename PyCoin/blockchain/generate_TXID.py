
# Genera TXID

import json
import pickle
import hashlib


def generateTXID(tx):

    # -- rimozione txid
    tx.pop("txid")

    for out in tx["out"]:
        # Rimozione stato output (speso/non speso)
        out.pop("spent")

    tx = pickle.dumps(tx)

    # Generazione hash della transazione (txid)
    txid = hashlib.sha256(tx).hexdigest()

    return txid


# -----------------------------------------------------------------------------------------

# Estrazione blocco
blockHeight = 1
print("BLOCK %d\n" %(blockHeight))

file = open(str(blockHeight)+".json")
content = file.read()
file.close()


block = json.loads(content)

tx = block["tx"][0]

# Funzione --> generazione TXID da transazione
txid = generateTXID(tx)

print(txid)


input("")


