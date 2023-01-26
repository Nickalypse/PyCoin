
import json
import pickle
import hashlib


def generateHashBlockHeader(header):

    print(header)

    header = pickle.dumps(header)

    h = hashlib.sha256(header).hexdigest()

    return h

# ----------------------------------------------------------------------------------------

blockHeight = 5
print("\nBLOCK %d\n" %(blockHeight))

# Estrazione blocco
file = open(str(blockHeight)+".json")
content = file.read()
file.close()

block = json.loads(content)

# Funzione --> generazione hash dell'header del blocco
h = generateHashBlockHeader(block["header"])

print("\n%s" %(h))

input("")


