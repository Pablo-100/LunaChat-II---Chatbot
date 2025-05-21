document.addEventListener('DOMContentLoaded', function() {
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const newChatButton = document.getElementById('new-chat');
    const sourcesContent = document.getElementById('sources-content');
    const themeToggle = document.getElementById('theme-toggle');
    
    let conversationId = 'default';
    let isWaitingForResponse = false;
    let currentTheme = localStorage.getItem('theme') || 'light';

    // Initialiser le thème
    document.documentElement.setAttribute('data-theme', currentTheme);
    updateThemeIcon();

    // Gérer le changement de thème
    themeToggle.addEventListener('click', function() {
        currentTheme = currentTheme === 'light' ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', currentTheme);
        localStorage.setItem('theme', currentTheme);
        updateThemeIcon();
    });

    function updateThemeIcon() {
        if (currentTheme === 'dark') {
            themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
            themeToggle.title = 'Passer au mode clair';
        } else {
            themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
            themeToggle.title = 'Passer au mode sombre';
        }
    }

    // Ajuster automatiquement la hauteur du textarea
    userInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        if (this.scrollHeight > 150) {
            this.style.height = '150px';
            this.style.overflowY = 'auto';
        } else {
            this.style.overflowY = 'hidden';
        }
    });

    // Envoyer un message quand on clique sur le bouton ou qu'on appuie sur Entrée
    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Nouvelle conversation
    newChatButton.addEventListener('click', function() {
        conversationId = Date.now().toString();
        chatMessages.innerHTML = `
            <div class="message system">
                <div class="message-content">
                    <p>Nouvelle conversation démarrée. Comment puis-je vous aider ?</p>
                </div>
            </div>
        `;
        sourcesContent.innerHTML = `<p class="no-sources">Les sources des réponses apparaîtront ici.</p>`;
        chatMessages.scrollTop = chatMessages.scrollHeight;
    });

    function sendMessage() {
        const message = userInput.value.trim();
        if (message === '' || isWaitingForResponse) return;

        // Ajouter le message de l'utilisateur à l'interface
        addMessage(message, 'user');
        
        // Réinitialiser l'input
        userInput.value = '';
        userInput.style.height = 'auto';
        
        // Afficher l'indicateur de chargement
        addLoadingIndicator();
        isWaitingForResponse = true;

        // Envoyer la requête à l'API
        fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                question: message,
                conversation_id: conversationId
            })
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.response || 'Une erreur est survenue');
                });
            }
            return response.json();
        })
        .then(data => {
            // Supprimer l'indicateur de chargement
            removeLoadingIndicator();
            
            // Ajouter la réponse de l'assistant
            addMessage(data.response, 'assistant');
            
            // Mettre à jour les sources
            updateSources(data.source_documents || []);
            
            // Mettre à jour l'ID de conversation si nécessaire
            if (data.conversation_id) {
                conversationId = data.conversation_id;
            }
        })
        .catch(error => {
            // Supprimer l'indicateur de chargement
            removeLoadingIndicator();
            
            // Afficher l'erreur
            addMessage(`Erreur: ${error.message}`, 'system');
        })
        .finally(() => {
            isWaitingForResponse = false;
        });
    }

    function addMessage(content, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        // Convertir les sauts de ligne en balises <br>
        const formattedContent = content.replace(/\n/g, '<br>');
        
        messageDiv.innerHTML = `
            <div class="message-content">
                <p>${formattedContent}</p>
            </div>
        `;
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function addLoadingIndicator() {
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message assistant loading';
        loadingDiv.id = 'loading-indicator';
        loadingDiv.innerHTML = `
            <div class="message-content loading">
                <div class="loading-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;
        
        chatMessages.appendChild(loadingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function removeLoadingIndicator() {
        const loadingIndicator = document.getElementById('loading-indicator');
        if (loadingIndicator) {
            loadingIndicator.remove();
        }
    }

    function updateSources(sources) {
        if (!sources || sources.length === 0) {
            sourcesContent.innerHTML = `<p class="no-sources">Aucune source spécifique pour cette réponse.</p>`;
            return;
        }

        sourcesContent.innerHTML = '';
        
        sources.forEach((source, index) => {
            const sourceDiv = document.createElement('div');
            sourceDiv.className = 'source-item';
            
            // Extraire le nom du fichier à partir du chemin complet
            const fileName = source.source.split('/').pop();
            
            sourceDiv.innerHTML = `
                <h3>Source ${index + 1}: ${fileName}</h3>
                <p>${source.content.substring(0, 200)}${source.content.length > 200 ? '...' : ''}</p>
            `;
            
            sourcesContent.appendChild(sourceDiv);
        });
    }
});