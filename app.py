import json
import random
import pickle
import numpy as np
from flask import Flask, request, jsonify, render_template
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
from tensorflow.keras.models import load_model
import traceback
from flask_cors import CORS
#from db_config import connect_to_db, search_product_info
import os

app = Flask(__name__)
CORS(app)

# Configuration du CORS
'''CORS(app, resources={
    r"/chat": {"origins": os.getenv("FRONTEND_URL", "http://localhost:3000")},
    r"/static/*": {"origins": "*"}
})'''

# Initialisation NLP
lemmatizer = WordNetLemmatizer()
intents = None
model = None
words = None
classes = None
livraison_data= None

def initialize_nlp():
    #Chargement des modèles NLP et les données une seule fois au démarrage
    global intents, model, words, classes, livraison_data, annulation, remboursement, retour, statut
    
    # Chargement des fichiers NLP
    model = load_model("model/model.h5")
    words = pickle.load(open("model/words.pkl", "rb"))
    classes = pickle.load(open("model/classes.pkl", "rb"))
    
    # Chargement des intentions
    with open("jsonfiles/intents.json", "r", encoding="utf-8") as file:
        intents = json.load(file)
    
    print("Modèle NLP chargé avec succès !")
    print(f"Mots vocab: {len(words)} | Classes: {classes}")

    # Chargement des données des delais de livraison
    with open("jsonfiles/livraison.json", "r", encoding="utf-8") as f:
        livraison_data = json.load(f)

    # Chargement des données de remboursement
    with open("jsonfiles/Remboursement.json", "r", encoding="utf-8") as f:
        remboursement = json.load(f)

    # Chargement des données de retour
    with open("jsonfiles/Retour.json", "r", encoding="utf-8") as f:
        retour = json.load(f)

    # Chargement des données de statut des commandes
    with open("jsonfiles/Statut_commande.json", "r", encoding="utf-8") as f:
        statut = json.load(f)

    # Chargement des données d'annulation
    with open("jsonfiles/Annulation.json", "r", encoding="utf-8") as f:
        annulation = json.load(f)

# Initialisation au démarrage
initialize_nlp()

def clean_up_sentence(sentence):
    #Cette fonction nettoie et tokenise la phrase
    sentence = ''.join(char for char in sentence if char.isalnum() or char in (' ', '?', '!'))
    sentence_words = word_tokenize(sentence.lower())
    sentence_words = [lemmatizer.lemmatize(word) for word in sentence_words]
    return sentence_words

def bag_of_words(sentence):
    #Convertit la phrase en sac de mots
    sentence_words = clean_up_sentence(sentence)
    bag = [0] * len(words)
    for w in sentence_words:
        for i, word in enumerate(words):
            if word == w:
                bag[i] = 1
    return np.array(bag)

def predict_class(sentence):
    #Prédit la classe de tag
    bow = bag_of_words(sentence)
    res = model.predict(np.array([bow]))[0]
    threshold = 0.15
    results = [[i, r] for i, r in enumerate(res) if r > threshold]
    results.sort(key=lambda x: x[1], reverse=True)
    return [{'intent': classes[r[0]], 'probability': str(r[1])} for r in results]

def get_response(intents_list):
    if not intents_list or float(intents_list[0]['probability']) < 0.3:
        # Trouver le tag "unknown" dans le fichier JSON
        unknown_intent = next((i for i in intents['intents'] if i['tag'] == 'unknown'), None)
        # fallback si jamais "unknown" n'existe pas
        return random.choice(unknown_intent['responses']) if unknown_intent else "Je n'ai pas bien compris."
    
    tag = intents_list[0]['intent']
    for intent in intents['intents']:
        if intent['tag'] == tag:
            return random.choice(intent['responses'])
    return "Je ne peux pas répondre pour le moment."

# Recherche des info sur livraison
def search_delivery_info(postal_code=None, city=None):
    results = []
    for livraison in livraison_data:
        if postal_code and livraison['code_postal'] == postal_code:
            results.append(livraison)
        if city and city.lower() in livraison['lib_commune'].lower():
            results.append(livraison)
    return results[0] if results else None

# Dictionnaire des fichiers et messages associés
order_files = {
    "statut": {
        "data": statut,
        "message": lambda item: f"Votre commande concernant : {item['offer_productTitle']}, a pour statut : {item['status']}",
    },
    "remboursement": {
        "data": remboursement,
        "message": lambda item: f"Le statut de votre remboursement est : {item['refundstatus']}, pour un montant de {item['Amounttorefunded']} DH. La méthode de récupération est : {item['refundMethod']}.",
    },
    "retour": {
        "data": retour,
        "message": lambda item: f"Vous pouvez retourner votre commande concernant : {item['offer_productTitle']}. Pour connaître la politique de retour, veuillez contacter notre service client au 0802007700.",
    },
    "annulation": {
        "data": annulation,
        "message": lambda item: f"Pour annuler votre commande concernant : {item['offer_productTitle']}, actuellement au statut : {item['status']}, veuillez contacter notre service client au 0802007700.",
    }
}


# Fonction générique pour rechercher dans tous les fichiers
def search_order_info(orderNumber):
    for key, config in order_files.items():
        for item in config["data"]:
            if item.get("reference") == orderNumber:
                return {
                    "response": config["message"](item),
                    "order": item
                }
    return {
        "response": "Aucune opération possible avec ce numéro. Veuillez contacter le service client au 0802007700."
    }
    
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        print("DATA REÇUE:", data)
        print("Current working dir:", os.getcwd())
        print("Files in current dir:", os.listdir())
        message = data["message"].strip()
        postal_code = data.get("code_postal", None)
        city = data.get("lib_commune", None)
        orderNumber = data.get("reference", None)
        if city:
            city = city.strip().title() 

        print(f"Message reçu: {message}")
        print(f"Info reçue: code={postal_code}, ville={city}")

        # Si on a un code postal ou une ville, on recherche livraison
        if postal_code or (city and search_delivery_info(None, city)):
            deliv = search_delivery_info(postal_code, city)
            if deliv:
                return jsonify({
                    "response": f"La livraison à {deliv['lib_commune']} va prendre {deliv['SLA']} jours avec le transporteur {deliv['Transporteur']}",
                    "order": deliv
                })
            else:
                return jsonify({"response": "Aucune ville trouvée avec ces informations."})
        elif orderNumber:
            result = search_order_info(orderNumber)
            return jsonify(result)


        # Sinon on prédit l'intention
        intents_list = predict_class(message)
        print(f"Intentions prédites: {intents_list}")

        if intents_list:
            # On prend l'intention la plus probable (la première)
            top_intent = intents_list[0]['intent'] 
            # Récupérer la réponse correspondant à cette intention
            response = get_response(intents_list) 
        else:
            # Pas d'intention détectée, réponse par défaut
            response = "Désolé, je n'ai pas compris votre question."

        return jsonify({"response": response})

    except Exception as e:
        print("ERROR:", str(e))
        traceback.print_exc()   
        return jsonify({"error": "Une erreur est survenue"})



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)     

