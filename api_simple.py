import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import re

app = Flask(__name__)
CORS(app)

# Configuration de l'API
os.environ["GEMINI_API_KEY"] = "------------------------"  # Remplacez par votre clé API valide

# Initialisation du modèle (version simplifiée)
try:
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=os.environ["GEMINI_API_KEY"])
    test_response = llm.invoke("Test de connexion")
    print("Connexion au modèle Gemini réussie:", test_response.content)
except Exception as e:
    print(f"Erreur lors de l'initialisation : {str(e)}")

# Stockage des conversations
conversations = {}

@app.route('/')
def index():
    return render_template('index.html')

# Ajouter après les imports:
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import re

# Ajouter avant l'initialisation du modèle:
# Charger les documents
try:
    pdf_paths = ["./documents/doc1.pdf.pdf", "./documents/doc2.pdf.pdf"]
    loaders = [PyMuPDFLoader(path) for path in pdf_paths]

    docs = []
    for loader in loaders:
        docs.extend(loader.load())

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = splitter.split_documents(docs)
    print(f"Documents chargés: {len(splits)} segments")
except Exception as e:
    print(f"Erreur lors du chargement des documents: {str(e)}")
    splits = []

# Fonction de recherche simple
def search_documents(query, top_k=3):
    results = []
    query_terms = re.findall(r'\w+', query.lower())
    
    for doc in splits:
        score = 0
        text = doc.page_content.lower()
        for term in query_terms:
            if term in text:
                score += 1
        
        if score > 0:
            results.append((doc, score))
    
    # Trier par score et prendre les top_k
    results.sort(key=lambda x: x[1], reverse=True)
    return [doc for doc, _ in results[:top_k]]

# Modifier la route /api/chat:
@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    question = data.get('question', '')
    conversation_id = data.get('conversation_id', 'default')
    
    if conversation_id not in conversations:
        conversations[conversation_id] = []
    
    history = conversations[conversation_id]
    
    try:
        # Rechercher des documents pertinents
        relevant_docs = search_documents(question)
        context = "\n\n".join([doc.page_content for doc in relevant_docs])
        
        # Version simplifiée avec recherche basique
        history_text = "\n".join([f"Utilisateur : {q}\nAssistant : {r}" for q, r in history])
        system_context = "Vous êtes LunaChat, un assistant IA conversationnel."
        full_prompt = f"{system_context}\n\nContexte pertinent récupéré :\n{context}\n\nHistorique de la conversation :\n{history_text}\n\nUtilisateur : {question}\n\nAssistant :"
        
        response = llm.invoke(full_prompt).content
        
        history.append((question, response))
        conversations[conversation_id] = history
        formatted_history = [(q, r) for q, r in history]
        
        print(f"Réponse générée pour '{question}': {response}")
        return jsonify({
            'response': response,
            'conversation_id': conversation_id,
            'history': formatted_history,
            'source_documents': [{'source': doc.metadata['source'], 'content': doc.page_content} for doc in relevant_docs]
        })
    except Exception as e:
        error_message = str(e)
        print(f"Erreur API détaillée pour '{question}': {error_message}")
        formatted_history = [(q, r) for q, r in history] if history else []
        
        if "429" in error_message or "quota" in error_message or "ResourceExhausted" in error_message:
            fallback_message = "Désolé, la limite de quota Gemini API est atteinte. Réessayez plus tard."
        elif "401" in error_message or "unauthorized" in error_message.lower():
            fallback_message = "Erreur d'authentification : clé API invalide. Vérifiez votre clé."
        elif "model" in error_message.lower():
            fallback_message = "Modèle Gemini indisponible. Vérifiez la documentation Google."
        else:
            fallback_message = f"Erreur : {error_message}"
        
        history.append((question, fallback_message))
        conversations[conversation_id] = history
        return jsonify({
            'response': fallback_message,
            'conversation_id': conversation_id,
            'history': formatted_history
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
