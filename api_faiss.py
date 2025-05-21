import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
# Remplacer cette ligne:
# from langchain_community.vectorstores import FAISS
# Par:
from langchain_community.vectorstores import DocArrayInMemorySearch
# Remplacer cette ligne:
# from langchain_community.embeddings import GoogleGenerativeAIEmbeddings
# Par:
from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA

app = Flask(__name__)
CORS(app)

# Configuration de l'API
os.environ["GEMINI_API_KEY"] = "----------------------"  # Remplacez par votre clé API valide
faiss_index_path = "./faiss_index"

# Initialisation du modèle et du vector store (chargé une seule fois)
try:
    # Charger ou créer le vector store
    pdf_paths = ["./documents/doc1.pdf.pdf", "./documents/doc2.pdf.pdf"]  # Chemins corrects
    loaders = [PyMuPDFLoader(path) for path in pdf_paths]

    docs = []
    for loader in loaders:
        docs.extend(loader.load())

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = splitter.split_documents(docs)

    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=os.environ["GEMINI_API_KEY"])
    
    # Utiliser FAISS au lieu de Chroma
    # Remplacer ce bloc:
    # if os.path.exists(f"{faiss_index_path}/index.faiss"):
    #     vectorstore = FAISS.load_local(faiss_index_path, embeddings)
    #     print("Index FAISS chargé depuis le disque")
    # else:
    #     vectorstore = FAISS.from_documents(documents=splits, embedding=embeddings)
    #     # Sauvegarder l'index pour une utilisation future
    #     os.makedirs(faiss_index_path, exist_ok=True)
    #     vectorstore.save_local(faiss_index_path)
    #     print("Nouvel index FAISS créé et sauvegardé")
    
    # Par:
    vectorstore = DocArrayInMemorySearch.from_documents(documents=splits, embedding=embeddings)
    print("Index DocArray créé en mémoire")
    retriever = vectorstore.as_retriever()

    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=os.environ["GEMINI_API_KEY"])
    test_response = llm.invoke("Test de connexion")
    print("Connexion au modèle Gemini réussie:", test_response.content)

    # Template du prompt
    prompt_template = """Historique de la conversation :\n{history}\n\nContexte pertinent récupéré :\n{context}\n\nUtilisateur : {question}\n\nAssistant : Répondez en utilisant le contexte fourni. Si le contexte est insuffisant, indiquez-le."""
    prompt = PromptTemplate(input_variables=["history", "context", "question"], template=prompt_template)

    # Chaîne RAG
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt}
    )
except Exception as e:
    print(f"Erreur lors de l'initialisation : {str(e)}")

# Stockage des conversations
conversations = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    question = data.get('question', '')
    conversation_id = data.get('conversation_id', 'default')
    
    if conversation_id not in conversations:
        conversations[conversation_id] = []
    
    history = conversations[conversation_id]
    
    try:
        history_text = "\n".join([f"Utilisateur : {q}\nAssistant : {r}" for q, r in history])
        result = qa_chain.invoke({"query": question, "history": history_text})
        response = result["result"]
        
        history.append((question, response))
        conversations[conversation_id] = history
        formatted_history = [(q, r) for q, r in history]
        
        print(f"Réponse générée pour '{question}': {response}")
        return jsonify({
            'response': response,
            'conversation_id': conversation_id,
            'history': formatted_history,
            'source_documents': [{'source': doc.metadata['source'], 'content': doc.page_content} for doc in result['source_documents']]
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
