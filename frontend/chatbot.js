const API_URL = "http://localhost:8000/api";
let conversationHistory = [];
let isOpen = false;

// ===== CREATE WIDGET =====
document.addEventListener("DOMContentLoaded", () => {
  createBubble();
  createChatWindow();
});

function createBubble() {
  const bubble = document.createElement("div");
  bubble.id = "chat-bubble";
  bubble.innerHTML = `
    <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/>
    </svg>`;
  bubble.addEventListener("click", toggleChat);
  document.body.appendChild(bubble);
}

function createChatWindow() {
  const win = document.createElement("div");
  win.id = "chat-window";
  win.innerHTML = `
    <div id="chat-header">
      <div id="chat-header-info">
        <div class="avatar">🏥</div>
        <div>
          <h3>Клиника Асистент</h3>
          <p>Онлайн • Отговаря веднага</p>
        </div>
      </div>
      <span id="chat-close">✕</span>
    </div>

    <div id="chat-messages"></div>

    <div id="quick-options">
      <button class="quick-btn" onclick="sendQuick('Искам да запазя час')">📅 Запази час</button>
      <button class="quick-btn" onclick="sendQuick('Искам да проверя час')">🔍 Провери час</button>
      <button class="quick-btn" onclick="sendQuick('Искам да откажа час')">❌ Откажи час</button>
    </div>

    <div id="chat-input-area">
      <input id="chat-input" type="text" placeholder="Напишете съобщение..."/>
      <button id="send-btn">
        <svg viewBox="0 0 24 24"><path d="M2 21l21-9L2 3v7l15 2-15 2v7z"/></svg>
      </button>
    </div>
  `;

  document.body.appendChild(win);

  // Event listeners
  document.getElementById("chat-close").addEventListener("click", toggleChat);
  document.getElementById("send-btn").addEventListener("click", sendMessage);
  document.getElementById("chat-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendMessage();
  });

  // Welcome message
  addMessage("bot", "Здравейте! 👋 Аз съм асистентът на клиниката. Как мога да помогна?");
}

// ===== TOGGLE OPEN/CLOSE =====
function toggleChat() {
  isOpen = !isOpen;
  const win = document.getElementById("chat-window");
  if (isOpen) {
    win.classList.add("open");
  } else {
    win.classList.remove("open");
  }
}

// ===== ADD MESSAGE =====
function addMessage(type, text) {
  const messages = document.getElementById("chat-messages");
  const div = document.createElement("div");
  div.className = `message-${type}`;
  div.textContent = text;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

// ===== TYPING INDICATOR =====
function showTyping() {
  const messages = document.getElementById("chat-messages");
  const div = document.createElement("div");
  div.className = "typing";
  div.id = "typing-indicator";
  div.innerHTML = `<span></span><span></span><span></span>`;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

function hideTyping() {
  const typing = document.getElementById("typing-indicator");
  if (typing) typing.remove();
}

// ===== SEND MESSAGE =====
async function sendMessage() {
  const input = document.getElementById("chat-input");
  const text = input.value.trim();
  if (!text) return;

  input.value = "";
  addMessage("user", text);
  conversationHistory.push({ role: "user", content: text });

  showTyping();

  try {
    const res = await fetch(`${API_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        conversation_history: conversationHistory
      })
    });

    const data = await res.json();
    hideTyping();
    addMessage("bot", data.response);
    conversationHistory.push({ role: "assistant", content: data.response });

  } catch (err) {
    hideTyping();
    addMessage("bot", "Съжалявам, имаше технически проблем. Опитайте по-късно.");
  }
}

// ===== QUICK BUTTONS =====
function sendQuick(text) {
  document.getElementById("chat-input").value = text;
  sendMessage();
}