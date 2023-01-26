
// Gestione schermata attesa connessione
var runningWallet = false;

function changeStateWallet(){
  if(runningWallet == false){
    $("#loadingText").html("CONNECTED");
    $("#loadingSub").hide();
    $("#loading").fadeOut(1000);
    runningWallet = true;
  }
  else {
    $("#loadingText").html("LOADING");
    $("#loadingSub").show();
    $("#loading").fadeIn(1000);
    runningWallet = false;
  }
}
// --------------------------------------------------------------


// VARIABILI GLOBALI <-- Dati ricevuti dal wallet desktop
var peers          = [];  // ip dei peers online
var peers_offline  = [];  // ip dei peers disconnessi
var my_address     = [];  // Indirizzi dei wallet Pycoin


var e               = document.getElementById("main");
var pycoinAmmount   = document.getElementById("pycoinAmmount");
// var newTransaction  = document.getElementById("newTransaction");


e.innerHTML = "HELLO WORLD!";



// Effettua connessione al wallet
var ws_wallet = new WebSocket("ws://localhost:8001/streaming");

// --> Connessione effettuata
/*
ws_wallet.onopen = function(){
  e.innerHTML += "<br>Connceted to Pycoin Desktop Wallet<br><br>";
}
*/

// --> Dati ricevuti dal wallet
ws_wallet.onmessage = function(event){

  log = event.data.split(" ");
  e.innerHTML += log + "<br>";

  switch(log[0]) {

    ////////////////////////////////////////////////////////////////////////////
    case("pycoin"):
      pycoinAmmount.innerHTML = log[1];
    break;
    ////////////////////////////////////////////////////////////////////////////
    case("relationTime"):



    break;
    ////////////////////////////////////////////////////////////////////////////
    case("peers"):
      for(var i=1; i<log.length; i++){
        // Aggiunge (se non presente) ip del peers alla lista dei peers online
        if(peers.indexOf(log[i]) == -1){
          peers.push(log[i]);
        }
        // Elimina (se presente) ip del peer nella lista dei peers offline
        var index = peers_offline.indexOf(log[i]);
        if(index != -1){
          peers_offline.splice(index, 1);
        }
      }
      // Apertura pannello di controllo del wallet --> Prima connessione alla rete p2p
      if((peers.length != 0) && (runningWallet == false)){
        changeStateWallet();
      }
    break;
    ////////////////////////////////////////////////////////////////////////////
    case("disconnectedPeer"):
      // Aggiunge ip del peer alla lista dei peers offline
      peers_offline.push(log[1]);
      // Elimina ip del peer nella lista dei peers online
      var index = peers.indexOf(log[1]);
      peers.splice(index, 1);

      if(peers.length == 0){
        changeStateWallet();
      }
    break;
    ////////////////////////////////////////////////////////////////////////////
  }



// --> Connessione terminata
ws_wallet.onclose = function(){
  window.close();
}




// Invia nuova transazione al wallet
function sendTransaction(){
  ws_wallet.send("newTransaction 5f8b4aa0f33eed49c21ed72ecaab59e347b015c47024eb2425585c0fac7d766c bSLumahuvSM4MEYDbzGQ3iSsds1D9KuV4YQyqTS4wbZaBX4SDrdaLV8KehdybQGrfz26 63.0 1.0");
}

















// ----------------------------------------------------------------------------
