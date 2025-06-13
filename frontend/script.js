// Get references to our HTML elements
const chatForm = document.getElementById('chat-form');
const messageInput = document.getElementById('message-input');
const chatWindow = document.getElementById('chat-window');

// Define the URL of our backend API
// This MUST match the port we exposed with Docker (-p 8000:80)
const API_URL = 'https://my-unique-business-api.azurewebsites.net/chat';

// Function to add a message to the chat window
function addMessage(sender, text) {
    const messageElement = document.createElement('div');
    messageElement.classList.add('message');

    if (sender === 'user') {
        messageElement.classList.add('user-message');
    } else if (sender === 'ai') {
        messageElement.classList.add('ai-message');
    } else if (sender === 'loading') {
        messageElement.classList.add('loading-message');
    }
    
    messageElement.textContent = text;
    chatWindow.appendChild(messageElement);

    // Scroll to the bottom of the chat window
    chatWindow.scrollTop = chatWindow.scrollHeight;
    return messageElement; // Return the element so we can update it
}

// Handle form submission
chatForm.addEventListener('submit', async (event) => {
    event.preventDefault(); // Prevent the page from reloading

    const userMessage = messageInput.value.trim();
    if (!userMessage) return; // Don't send empty messages

    // Display the user's message immediately
    addMessage('user', userMessage);

    // Clear the input field
    messageInput.value = '';
    
    // Show a loading indicator
    const loadingMessage = addMessage('loading', '...');

    try {
        // Make the API call to our FastAPI backend
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: userMessage }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        
        // Remove the loading message
        loadingMessage.remove();
        
        // Display the AI's response
        addMessage('ai', data.reply);

    } catch (error) {
        console.error('Error fetching from API:', error);
        // Remove the loading message and show an error
        loadingMessage.remove();
        addMessage('ai', 'Sorry, I ran into an error. Please try again.');
    }
});