
import random
import hashlib
import pickle
import json


def generateMerkleRoot(transactions):

    merkle_tree = []    

    # Generazione del primo livello del merkle tree
    for tx in transactions:
        merkle_tree.append(tx["txid"])

    # Se presente una sola transazione, ne duplico l'hash
    if(len(merkle_tree) %2 != 0):
        merkle_tree.append(merkle_tree[-1])

    # --
    print("MERKLE TREE BASE:\n")
    i = 1
    for h in merkle_tree:
        print("[%d] %s" %(i, h))
        i += 1
    # --

    # Generazione merkle root
    while(len(merkle_tree) != 1):
        # Se il totale di hash è dispari ne duplico l'ultimo
        # al fine di operare sempre con coppie di hash
        if(len(merkle_tree) %2 != 0):
            print("[!]")
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


# -----------------------------------------------------------------------------------------

blockHeight = 5
print("\nBLOCK %d\n" %(blockHeight))

# Estrazione blocco
file = open(str(blockHeight)+".json")
content = file.read()
file.close()

block = json.loads(content)

# Funzione --> Generazione merkle root da transazioni del blocco
merkleRoot = generateMerkleRoot(block["tx"])


print("\n\n%s" %(merkleRoot))


input("")

