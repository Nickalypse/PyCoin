
import json
import pickle
import hashlib


blockHeight = 0
print("\nBLOCK %d\n" %(blockHeight))

# Estrazione blocco
file = open(str(blockHeight)+".json")
content = file.read()
file.close()

block = json.loads(content)

##############################################################################


# Controllo singola transazione
print(block)


