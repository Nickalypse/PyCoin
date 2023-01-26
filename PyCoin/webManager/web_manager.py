
from tornado         import httpserver, websocket, ioloop, web, gen, concurrent
from tornado.ioloop  import PeriodicCallback
from webbrowser      import open_new_tab

import os.path
import time

import sys
sys.path.append("../")
import globalVariables.variables


# --------------------------------------------------------------------------------------

class webPage(web.RequestHandler):
    # Apertura nuova finestra browser --> pannello di controllo del wallet
    def get(self):
        self.render("pages/index.html")
 

# --------------------------------------------------------------------------------------

class webSocketServer(websocket.WebSocketHandler):

    # Lista client --> finestre del browser connesse al pannello di controllo del wallet
    listaConnessioni = []

    # Esegue funzione in parallelo (thread specifici)
    executor = concurrent.futures.ThreadPoolExecutor(1)


    def open(self):
        # --> Nuova connessione dal browser
        self.listaConnessioni.append(self)
        print("[+] Browser connection")

        # Attesa generazione/estrazione indirizzi del wallet
        while(len(globalVariables.variables.protocol.keys) == 0):
            time.sleep(1)

        # Invio indirizzi del wallet al browser
        for i in range(len(globalVariables.variables.protocol.keys)) :
            key = globalVariables.variables.protocol.keys
            self.write_message("key %s" %(key["address"]))

        # Attesa connessione alla rete p2p
        while(len(globalVariables.variables.peersManager.peers_server) == 0):
            time.sleep(2)

        # Attessa aggiornamento blockchain
        while(globalVariables.variables.protocol.eventBlockchainUpdate == False):
            time.sleep(2)

        # Invia totale di pycoin in possesso
        pycoinAmmount = globalVariables.variables.protocol.pycoinAmmount
        pycoinAmmount = "pycoinAmmount {0:.8f}".format(pycoinAmmount)
        globalVariables.variables.protocol.log.put(pycoinAmmount)

        # Invia totale di blocchi memorizzati
        blockchainLength = globalVariables.variables.protocol.blockHeightIndex + 1
        blockchainLength = "blockchainLength %d" %(blockchainLength)
        globalVariables.variables.protocol.log.put(blockchainLength)

        # Invia lista ip dei peers connessi al browser
        # >> Abilita pannello di amministrazione del wallet
        peersList = "peers"
        for ip in globalVariables.variables.peersManager.peers_server :
            peersList = peersList + " " + ip
        globalVariables.variables.protocol.log.put(peersList)

        # . . .

        # Esecuzione thread inoltro dati al wallet
        self.send_data_to_browser()


    def on_message(self, browserQuery):
        # --> Messaggio ricevuto dal browser
        # -- print("[RECV]: %s" %(browserQuery))

        # Conversione stringa in vettore di dati
        data = browserQuery.split(" ")

        # Generazione query da inoltrare al protocollo
        query = [data[0], []]
        for i in range(1, len(data)):
            query[1].append(data[i])
        
        # Invia query dell'utente dal browser al protocollo
        globalVariables.variables.protocol.query.put(query)


    def on_close(self):
        # --> Connessione al browser terminata
        self.listaConnessioni.remove(self)
        print("[-] Browser disconnection")


    def check_origin(self, origin):
        # --> Mantiene connessione con il browser
        return True


    @gen.coroutine
    def send_data_to_browser(self):
        while True:
            # Ricezione dati dal thread
            msg = yield self.get_data_from_wallet()
            # print("MSG >>", msg)
            
            if(len(self.listaConnessioni) != 0):
                try:
                    # Invia dati ad ogni connessione (finestra) del browser
                    for client in self.listaConnessioni:
                        client.write_message(msg)
                except:
                    pass


    @concurrent.run_on_executor
    def get_data_from_wallet(self):
        # Estrazione dati da inoltrare al browser
        msg = globalVariables.variables.protocol.log.get()
        return msg


# --------------------------------------------------------------------------------------

def start_web_control_panel():

    # Indica al browser la posizione dei file statici nella pagina web
    settings = dict(
        static_path = os.path.join(os.path.dirname(__file__), "static")
    )
    
    application = web.Application([
        (r"/", webPage),
        (r"/streaming", webSocketServer)
    ], **settings)

    http_server = httpserver.HTTPServer(application)
    http_server.listen(8001)


    ## Apre nuova finestra browser --> Pannello di controllo del wallet
    open_new_tab("http://localhost:8001")


    # Esecuzione infinita
    ioloop.IOLoop.instance().start()





