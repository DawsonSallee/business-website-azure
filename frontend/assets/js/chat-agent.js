// This event listener ensures that our code only runs after the entire
// HTML page has been loaded and is ready.
document.addEventListener('DOMContentLoaded', function() {

    // This is the URL of our secure backend proxy. The frontend only ever
    // talks to this single endpoint for all AI chat interactions.
    const AGENT_PROXY_ENDPOINT = "https://my-unique-business-api.azurewebsites.net/api/chat-with-agent"; 


    // We get references to all the parts of our chat interface once, at the start
    const chatWindow = document.getElementById('chat-window');
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatSubmitButton = document.getElementById('chat-submit-button');

    // A safety check. If any chat elements are missing from the HTML,
    // we stop executing to prevent errors.
    if (!chatWindow || !chatForm || !chatInput) {
        return;
    }

    // --- State Management ---
    // Start the conversation with the initial greeting from the assistant.
    let conversationHistory = [
        { role: 'assistant', content: 'Hello! How can I help you today?' }
    ];

    // --- Main Chat Logic ---
    chatForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const userMessage = chatInput.value.trim();
        if (!userMessage) return;

        // 1. Display the user's message immediately for a snappy UI
        addMessageToWindow('user', userMessage);
        conversationHistory.push({ role: 'user', content: userMessage });
        chatInput.value = '';
        
        // 2. Disable form while waiting for the AI response
        setFormDisabled(true);

        // 3. Prepare for the streaming response from the AI
        const assistantMessageElement = addMessageToWindow('assistant', '...');

    try {
        const response = await fetch(AGENT_PROXY_ENDPOINT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            // 1. FIX: Send the simple body format your backend expects.
            body: JSON.stringify({
                "message": userMessage
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`API Error: ${response.status} - ${errorData.detail || 'Unknown error'}`);
        }

        // 2. FIX: Handle a simple JSON response, not a stream.
        const data = await response.json();
        const fullReply = data.reply; // Get the reply text from the JSON

        // 3. Update the UI with the final, complete answer.
        assistantMessageElement.innerText = fullReply;

    } catch (error) {
        console.error('Failed to fetch from agent:', error);
        assistantMessageElement.innerHTML = `<p style="color: #ff7b7b;">Sorry, an error occurred. Please try again later.</p>`;
    } finally {
        setFormDisabled(false);
        scrollToBottom(); // Call this to make sure the view scrolls down
        chatInput.focus();
    }
    });


    // --- Helper Functions ---
    function addMessageToWindow(sender, message) {
        const messageWrapper = document.createElement('div');
        messageWrapper.className = `chat-message ${sender}-message`;
        
        const messageParagraph = document.createElement('p');
        messageParagraph.innerText = message; // Use innerText for security
        
        messageWrapper.appendChild(messageParagraph);
        chatWindow.appendChild(messageWrapper);
        scrollToBottom();
        return messageParagraph; // Return the paragraph to allow for streaming updates
    }

    function scrollToBottom() {
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    function setFormDisabled(isDisabled) {
        chatInput.disabled = isDisabled;
        chatSubmitButton.disabled = isDisabled;
        chatSubmitButton.innerText = isDisabled ? 'Thinking...' : 'Send';
    }
});