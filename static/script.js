// GLOBAL VARIABLES 
let chatbotContainer = document.querySelector(".chatbot-container");
let chatbox = document.querySelector(".chatbox");
let send_btn = document.querySelector(".send_btn");
let OpenIcon = document.getElementById("chatbot-icone");
let closeIcon = document.querySelector(".chatbot-container .titre i");
let userInput = document.getElementById("user-input");


// open & close 
OpenIcon.addEventListener('click', () => {
    chatbotContainer.classList.toggle('open');
    openChatbot();
});

// just close by X
closeIcon.addEventListener('click', () => {
    chatbotContainer.classList.remove('open');
});

// pause animation (optional)
OpenIcon.addEventListener("click", function () {
    const beforeElement = this;
    if (beforeElement.classList.contains("paused")) {
        beforeElement.classList.remove("running");
    } else {
        beforeElement.classList.add("paused");
    }
});

// fonction pour ouvrir le conteneur du chatbot
function openChatbot() {
    if (!chatbox.dataset.welcomeShown) {
        let messagetext = "Bonjour 👋 ! Je suis le chatbot de <span>Marjane Mall</span>. Vous pouvez me poser des questions sur :<br>• La livraison<br>• Le paiement<br>• Offres et produits <br>• Remboursement <br>• Annulation du commande <br>• Retourne d'un article<br>• Statut de commande";
        MessageUI(messagetext, 'bot');
        chatbox.dataset.welcomeShown = true;
    }
}

// MESSAGE UI FUNCTION
const MessageUI = (message, type) => {
    const Message = document.createElement("div");
    Message.classList.add(type == 'bot' ? 'bot' : 'user');

    const avatar = document.createElement("div");
    avatar.classList.add('avatar');
    const img = document.createElement("img");
    img.src = type == 'bot' ? "../static/images/avatar.png" : "../static/images/profile.png";
    avatar.appendChild(img);
    Message.appendChild(avatar);

    const messageContent = document.createElement("div");
    messageContent.classList.add(type == 'bot' ? 'bot_message' : 'user_message');
    messageContent.innerHTML = message;
    Message.appendChild(messageContent);

    chatbox.appendChild(Message);
    chatbox.scrollTop = chatbox.scrollHeight;
};

// Fonction pour afficher un message "Le bot écrit..."
function showLoading() {
    const loadingMsg = document.createElement("div");
    loadingMsg.classList.add("bot", "loading");
    loadingMsg.textContent = "Le bot écrit...";
    chatbox.appendChild(loadingMsg);
    chatbox.scrollTop = chatbox.scrollHeight;
    return loadingMsg;
}

// fonction pour envoyer un message
async function sendMessage() {
    let userInputValue = userInput.value.trim();
    if (userInputValue === "") return;

    // Afficher le message utilisateur
    MessageUI(userInputValue, 'user');
    send_btn.disabled = true;

    // Message de chargement
    const loadingMsg = showLoading();

    // Extraction manuelle (regex)
    let orderNumber = null;
    let postalCode = null;
    let cityName = null;

    // Chercher les nombres
    const numbers = userInputValue.match(/\d+/g); // tous les chiffres
    if (numbers) {
        for (let n of numbers) {
            if (n.length === 5) postalCode = parseInt(n);
            else if (n.length >= 6) orderNumber = n;
        }
    }

    // Si pas de code postal, on suppose que c'est une ville
    if (!postalCode && !orderNumber) {
    cityName = userInputValue.toUpperCase(); 
    }


    try {
        let response = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: userInputValue,
                reference: orderNumber || null,
                code_postal: postalCode || null,
                lib_commune: cityName || null
            })
        });

        let data = await response.json();
        chatbox.removeChild(loadingMsg);

        // Afficher réponse bot 
        let botResponse = data.response || "Désolé, je n'ai pas compris.";
        MessageUI(botResponse, 'bot');

    } catch (error) {
        console.error("Erreur lors de l'envoi :", error);
        chatbox.removeChild(loadingMsg);
        MessageUI("Désolé, une erreur est survenue.", 'bot');
    } finally {
        send_btn.disabled = false;
        userInput.value = "";
        userInput.focus();
    }
}

// click "Envoyer"
send_btn.addEventListener('click', () => {
    sendMessage();
});

// touche "Entrée"
userInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
        sendMessage();
    }
});
