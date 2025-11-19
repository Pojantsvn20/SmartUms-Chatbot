import { initializeApp } from "https://www.gstatic.com/firebasejs/11.0.1/firebase-app.js";
import { getFirestore, collection, getDocs, setDoc, doc, writeBatch } from "https://www.gstatic.com/firebasejs/11.0.1/firebase-firestore.js";

const firebaseConfig = {
    apiKey: "AIzaSyCfK4nCoo-DVH_K5zLspglcnFjvLK1CL2A",
    authDomain: "smartums-feedback.firebaseapp.com",
    projectId: "smartums-feedback",
    storageBucket: "smartums-feedback.firebasestorage.app",
    messagingSenderId: "814627859215",
    appId: "1:814627859215:web:92b919f7ac350fae6e2c7a",
    measurementId: "G-372D93YSL0"
};
const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

const CHAT_COLLECTION = 'chat_sessions';
let currentSessionId = generateSessionId();
let chatSessions = {};

function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

async function loadChatHistory() {
    chatSessions = {};
    const qSnap = await getDocs(collection(db, CHAT_COLLECTION));
    qSnap.forEach(docSnap => {
        chatSessions[docSnap.id] = { ...docSnap.data(), id: docSnap.id };
    });
    updateHistoryUI();
}

async function saveChatSession(session) {
    await setDoc(doc(db, CHAT_COLLECTION, session.id), session);
    chatSessions[session.id] = session;
    updateHistoryUI();
}

function getCurrentSession() {
    if (!chatSessions[currentSessionId]) {
        chatSessions[currentSessionId] = {
            id: currentSessionId,
            title: 'New Chat',
            messages: [],
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString()
        };
        saveChatSession(chatSessions[currentSessionId]);
    }
    return chatSessions[currentSessionId];
}

function updateHistoryUI() {
    const historyList = document.getElementById('historyList');
    const sessions = Object.values(chatSessions).sort((a, b) => 
        new Date(b.updatedAt) - new Date(a.updatedAt)
    );
    if (sessions.length === 0) {
        historyList.innerHTML = '<p style="text-align:center; padding:20px; color:#999;">No history yet</p>';
        return;
    }
    historyList.innerHTML = sessions.map(session => {
        const date = new Date(session.updatedAt);
        const timeStr = date.toLocaleString('en-US', { 
            month: 'short', 
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
        const isActive = session.id === currentSessionId ? 'active' : '';
        return `
            <div class="history-item ${isActive}" onclick="loadSession('${session.id}')">
                <div class="history-title">${session.title}</div>
                <div class="history-time">${timeStr} • ${session.messages.length} messages</div>
            </div>
        `;
    }).join('');
}

window.loadSession = function(sessionId) {
    currentSessionId = sessionId;
    const session = chatSessions[sessionId];
    if (!session) {
        console.error('Session not found:', sessionId);
        return;
    }
    const chatMessages = document.getElementById('chatMessages');
    chatMessages.innerHTML = '';
    session.messages.forEach(msg => {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message ' + msg.type + '-message';
        const msgDate = new Date(msg.timestamp);
        const time = msgDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const avatar = msg.type === 'user' ? '👤' : '🤖';
        messageDiv.innerHTML = `
            <div class="message-header">
                <div class="avatar ${msg.type}-avatar">${avatar}</div>
                <span class="sender-name">${msg.sender}</span>
                <span class="timestamp">${time}</span>
            </div>
            <div class="message-content">${msg.content}</div>
        `;
        chatMessages.appendChild(messageDiv);
    });
    chatMessages.scrollTop = chatMessages.scrollHeight;
    updateHistoryUI();
};

window.startNewChat = async function() {
    currentSessionId = generateSessionId();
    chatSessions[currentSessionId] = {
        id: currentSessionId,
        title: 'New Chat',
        messages: [],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
    };
    await saveChatSession(chatSessions[currentSessionId]);
    document.getElementById('chatMessages').innerHTML = `
        <div class="welcome">
            <h2>New Chat Started! ✨</h2>
            <p>Ask me anything about UMS!</p>
        </div>
    `;
    updateHistoryUI();
};

window.clearAllHistory = async function() {
    if (confirm('Clear all chat history? This cannot be undone.')) {
        const qSnap = await getDocs(collection(db, CHAT_COLLECTION));
        const batch = writeBatch(db);
        qSnap.forEach(docSnap => batch.delete(docSnap.ref));
        await batch.commit();
        chatSessions = {};
        currentSessionId = generateSessionId();
        updateHistoryUI();
        startNewChat();
    }
};

// On page load
loadChatHistory();
