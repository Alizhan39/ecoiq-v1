/**
 * customer-chat.js — Vanilla JS client for Ask EcoIQ customer assistant.
 * Handles state, session storage, Markdown rendering, and API communication.
 */
(function () {
  'use strict';

  const STORAGE_KEY_CONV = 'ecoiq_chat_conv_id';
  const STORAGE_KEY_HIST = 'ecoiq_chat_history';
  const API_CHAT_URL = '/api/customer-chat/chat/';
  const API_STARTERS_URL = '/api/customer-chat/starters/';

  let conversationId = sessionStorage.getItem(STORAGE_KEY_CONV) || '';
  let chatHistory = [];
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY_HIST);
    if (raw) chatHistory = JSON.parse(raw);
  } catch (e) {
    chatHistory = [];
  }

  let isOpen = false;
  let isSending = false;

  // DOM Elements
  let launcherBtn, widgetEl, bodyEl, formEl, inputEl, sendBtn, closeBtn, clearBtn, startersContainer;

  function init() {
    launcherBtn = document.getElementById('ecoiq-chat-launcher');
    widgetEl = document.getElementById('ecoiq-chat-widget');
    bodyEl = document.getElementById('ecoiq-chat-body');
    formEl = document.getElementById('ecoiq-chat-form');
    inputEl = document.getElementById('ecoiq-chat-input');
    sendBtn = document.getElementById('ecoiq-chat-send');
    closeBtn = document.getElementById('ecoiq-chat-close');
    clearBtn = document.getElementById('ecoiq-chat-clear');
    startersContainer = document.getElementById('ecoiq-chat-starters');

    if (!launcherBtn || !widgetEl) return;

    launcherBtn.addEventListener('click', toggleChat);
    if (closeBtn) closeBtn.addEventListener('click', closeChat);
    if (clearBtn) clearBtn.addEventListener('click', clearChat);
    if (formEl) formEl.addEventListener('submit', handleFormSubmit);

    // Escape key closes widget
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && isOpen) {
        closeChat();
      }
    });

    // Delegate starter button clicks
    if (startersContainer) {
      startersContainer.addEventListener('click', function (e) {
        const btn = e.target.closest('.ecoiq-starter-btn');
        if (btn && btn.dataset.prompt) {
          sendMessage(btn.dataset.prompt);
        }
      });
    }

    // Restore previous conversation if any
    restoreHistory();
  }

  function toggleChat() {
    if (isOpen) {
      closeChat();
    } else {
      openChat();
    }
  }

  function openChat() {
    isOpen = true;
    widgetEl.classList.add('is-open');
    launcherBtn.setAttribute('aria-expanded', 'true');
    if (inputEl) inputEl.focus();
    scrollToBottom();
  }

  function closeChat() {
    isOpen = false;
    widgetEl.classList.remove('is-open');
    launcherBtn.setAttribute('aria-expanded', 'false');
  }

  function clearChat() {
    chatHistory = [];
    conversationId = '';
    sessionStorage.removeItem(STORAGE_KEY_HIST);
    sessionStorage.removeItem(STORAGE_KEY_CONV);

    // Reset body to default welcome
    const welcomeEl = document.getElementById('ecoiq-chat-welcome');
    if (welcomeEl) {
      bodyEl.innerHTML = '';
      bodyEl.appendChild(welcomeEl);
      welcomeEl.style.display = 'block';
    } else {
      location.reload();
    }
  }

  function scrollToBottom() {
    if (bodyEl) {
      bodyEl.scrollTop = bodyEl.scrollHeight;
    }
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function formatMarkdown(text) {
    if (!text) return '';
    let safe = escapeHtml(text);

    // Bold: **text** or __text__
    safe = safe.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    safe = safe.replace(/__(.*?)__/g, '<strong>$1</strong>');

    // Italic: *text* or _text_
    safe = safe.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // Inline code: `text`
    safe = safe.replace(/`(.*?)`/g, '<code style="background:#161b22;padding:2px 4px;border-radius:3px;font-size:12px;">$1</code>');

    // Links: [label](url) — allow only relative or https URLs
    safe = safe.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+|\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

    // Split paragraphs and handle bullet lists
    const lines = safe.split('\n');
    let out = [];
    let inList = false;

    for (let line of lines) {
      let trimmed = line.trim();
      if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
        if (!inList) {
          out.push('<ul>');
          inList = true;
        }
        out.push('<li>' + trimmed.substring(2) + '</li>');
      } else {
        if (inList) {
          out.push('</ul>');
          inList = false;
        }
        if (trimmed.length > 0) {
          out.push('<p>' + trimmed + '</p>');
        }
      }
    }
    if (inList) out.push('</ul>');

    return out.join('');
  }

  function appendMessage(role, content, actions = []) {
    const welcomeEl = document.getElementById('ecoiq-chat-welcome');
    if (welcomeEl && welcomeEl.style.display !== 'none' && chatHistory.length > 0) {
      welcomeEl.style.display = 'none';
    }

    const msgEl = document.createElement('div');
    msgEl.className = 'ecoiq-msg is-' + role;

    const bubbleEl = document.createElement('div');
    bubbleEl.className = 'ecoiq-msg-bubble';
    bubbleEl.innerHTML = formatMarkdown(content);
    msgEl.appendChild(bubbleEl);

    // Render suggested action pills if assistant returned any
    if (role === 'assistant' && actions && actions.length > 0) {
      const actionsEl = document.createElement('div');
      actionsEl.className = 'ecoiq-chat-actions';
      actions.forEach(function (act) {
        if (act.label && act.url) {
          const a = document.createElement('a');
          a.className = 'ecoiq-action-pill';
          a.href = act.url;
          a.innerHTML = escapeHtml(act.label) + ' &rarr;';
          actionsEl.appendChild(a);
        }
      });
      bubbleEl.appendChild(actionsEl);
    }

    bodyEl.appendChild(msgEl);
    scrollToBottom();
  }

  function showTypingIndicator() {
    const typingEl = document.createElement('div');
    typingEl.id = 'ecoiq-chat-typing';
    typingEl.className = 'ecoiq-typing';
    typingEl.innerHTML = '<span class="ecoiq-typing-dot"></span><span class="ecoiq-typing-dot"></span><span class="ecoiq-typing-dot"></span>';
    bodyEl.appendChild(typingEl);
    scrollToBottom();
  }

  function removeTypingIndicator() {
    const typingEl = document.getElementById('ecoiq-chat-typing');
    if (typingEl) typingEl.remove();
  }

  function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.getAttribute('content');

    const input = document.querySelector('[name=csrfmiddlewaretoken]');
    if (input) return input.value;

    const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return match ? match[1] : '';
  }

  function restoreHistory() {
    if (chatHistory && chatHistory.length > 0) {
      const welcomeEl = document.getElementById('ecoiq-chat-welcome');
      if (welcomeEl) welcomeEl.style.display = 'none';

      chatHistory.forEach(function (item) {
        appendMessage(item.role, item.content, item.actions || []);
      });
    }
  }

  function saveHistory() {
    sessionStorage.setItem(STORAGE_KEY_HIST, JSON.stringify(chatHistory));
    if (conversationId) {
      sessionStorage.setItem(STORAGE_KEY_CONV, conversationId);
    }
  }

  async function sendMessage(text) {
    if (!text || isSending) return;
    const cleanText = text.trim();
    if (!cleanText) return;

    if (inputEl) inputEl.value = '';

    // Append User Message
    appendMessage('user', cleanText);
    chatHistory.push({ role: 'user', content: cleanText });
    saveHistory();

    isSending = true;
    if (sendBtn) sendBtn.disabled = true;
    showTypingIndicator();

    try {
      const resp = await fetch(API_CHAT_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify({
          message: cleanText,
          conversation_id: conversationId || undefined,
          history: chatHistory.slice(-8),
        }),
      });

      removeTypingIndicator();

      if (!resp.ok) {
        const errData = await resp.json().catch(function () { return {}; });
        const errMsg = errData.detail || 'Service is temporarily unavailable. Please try again.';
        appendMessage('assistant', errMsg);
      } else {
        const data = await resp.json();
        if (data.conversation_id) conversationId = data.conversation_id;

        const answer = data.answer || 'Thank you for your question.';
        const actions = data.suggested_actions || [];

        appendMessage('assistant', answer, actions);
        chatHistory.push({ role: 'assistant', content: answer, actions: actions });
        saveHistory();
      }
    } catch (err) {
      removeTypingIndicator();
      appendMessage('assistant', 'Unable to reach the EcoIQ Assistant. Please check your connection or contact alizhan@ecoiq.uk.');
    } finally {
      isSending = false;
      if (sendBtn) sendBtn.disabled = false;
      if (inputEl) inputEl.focus();
      scrollToBottom();
    }
  }

  function handleFormSubmit(e) {
    e.preventDefault();
    if (inputEl && inputEl.value) {
      sendMessage(inputEl.value);
    }
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
