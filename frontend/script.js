// API base URL - use relative path to work from any host
const API_URL = '/api';

// Global state
let currentSessionId = null;

// DOM elements
let chatMessages, chatInput, sendButton, totalCourses, courseTitles, newChatButton;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Get DOM elements after page loads
    chatMessages = document.getElementById('chatMessages');
    chatInput = document.getElementById('chatInput');
    sendButton = document.getElementById('sendButton');
    totalCourses = document.getElementById('totalCourses');
    courseTitles = document.getElementById('courseTitles');
    newChatButton = document.getElementById('newChatButton');

    setupEventListeners();
    createNewSession();
    loadCourseStats();
});

// Event Listeners
function setupEventListeners() {
    // Chat functionality
    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    // New chat button
    newChatButton.addEventListener('click', handleNewChat);

    // Suggested questions
    document.querySelectorAll('.suggested-item').forEach(button => {
        button.addEventListener('click', (e) => {
            const question = e.target.getAttribute('data-question');
            chatInput.value = question;
            sendMessage();
        });
    });
}


// Chat Functions
async function sendMessage() {
    const query = chatInput.value.trim();
    if (!query) return;

    // Disable input
    chatInput.value = '';
    chatInput.disabled = true;
    sendButton.disabled = true;
    newChatButton.disabled = true;

    // Add user message
    addMessage(query, 'user');

    // Add loading message - create a unique container for it
    const loadingMessage = createLoadingMessage();
    chatMessages.appendChild(loadingMessage);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const response = await fetch(`${API_URL}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                session_id: currentSessionId
            })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(`Query failed: ${errorData.detail || response.statusText}`);
        }

        const data = await response.json();
        
        // Update session ID if new
        if (!currentSessionId) {
            currentSessionId = data.session_id;
        }

        // Replace loading message with response
        loadingMessage.remove();
        addMessage(data.answer, 'assistant', data.sources);

    } catch (error) {
        // Replace loading message with error
        loadingMessage.remove();
        addMessage(`Error: ${error.message}`, 'assistant');
    } finally {
        chatInput.disabled = false;
        sendButton.disabled = false;
        newChatButton.disabled = false;
        chatInput.focus();
    }
}

function createLoadingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="loading">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    return messageDiv;
}

function addMessage(content, type, sources = null, isWelcome = false) {
    const messageId = Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}${isWelcome ? ' welcome-message' : ''}`;
    messageDiv.id = `message-${messageId}`;

    // Convert markdown to HTML for assistant messages
    let displayContent = type === 'assistant' ? marked.parse(content) : escapeHtml(content);

    // Process citation markers to make them clickable
    if (sources && sources.length > 0) {
        displayContent = makeCitationsClickable(displayContent, messageId);
    }

    let html = `<div class="message-content">${displayContent}</div>`;

    if (sources && sources.length > 0) {
        html += renderSourceCards(sources, messageId);
    }

    messageDiv.innerHTML = html;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return messageId;
}

function makeCitationsClickable(content, messageId) {
    // Replace citation markers [1], [2], etc. with clickable links
    return content.replace(/\[(\d+)\]/g, (match, num) => {
        return `<a href="#source-${messageId}-${num}" class="citation-link" onclick="scrollToSource(event, '${messageId}', '${num}')">[${num}]</a>`;
    });
}

function renderSourceCards(sources, messageId) {
    const sourcesHtml = sources.map((source, index) => {
        const num = index + 1;
        let cardHtml = `
            <div class="source-card" id="source-${messageId}-${num}">
                <div class="source-number">[${num}]</div>
                <div class="source-details">
                    <div class="source-course">
        `;

        // Course title with link if available
        if (source.course_link) {
            cardHtml += `<a href="${escapeHtml(source.course_link)}" target="_blank" rel="noopener noreferrer" class="source-link">${escapeHtml(source.course_title)}</a>`;
        } else {
            cardHtml += escapeHtml(source.course_title);
        }

        cardHtml += `</div>`;

        // Lesson information if available
        if (source.lesson_number !== null && source.lesson_number !== undefined) {
            cardHtml += `<div class="source-lesson">`;

            if (source.lesson_link) {
                cardHtml += `Lesson ${source.lesson_number}`;
                if (source.lesson_title) {
                    cardHtml += `: <a href="${escapeHtml(source.lesson_link)}" target="_blank" rel="noopener noreferrer" class="source-link">${escapeHtml(source.lesson_title)}</a>`;
                } else {
                    cardHtml += ` - <a href="${escapeHtml(source.lesson_link)}" target="_blank" rel="noopener noreferrer" class="source-link">View Lesson</a>`;
                }
            } else {
                cardHtml += `Lesson ${source.lesson_number}`;
                if (source.lesson_title) {
                    cardHtml += `: ${escapeHtml(source.lesson_title)}`;
                }
            }

            cardHtml += `</div>`;
        }

        cardHtml += `
                </div>
            </div>
        `;

        return cardHtml;
    }).join('');

    return `
        <details class="sources-collapsible" open>
            <summary class="sources-header">Sources (${sources.length})</summary>
            <div class="sources-cards">
                ${sourcesHtml}
            </div>
        </details>
    `;
}

// Scroll to source card when citation is clicked
function scrollToSource(event, messageId, sourceNum) {
    event.preventDefault();
    const sourceCard = document.getElementById(`source-${messageId}-${sourceNum}`);
    if (sourceCard) {
        sourceCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        // Add highlight animation
        sourceCard.classList.add('highlight');
        setTimeout(() => sourceCard.classList.remove('highlight'), 2000);
    }
}

// Helper function to escape HTML for user messages
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Removed removeMessage function - no longer needed since we handle loading differently

async function createNewSession() {
    currentSessionId = null;
    chatMessages.innerHTML = '';
    addMessage('Welcome to the Course Materials Assistant! I can help you with questions about courses, lessons and specific content. What would you like to know?', 'assistant', null, true);
}

function handleNewChat() {
    // クエリ実行中は新規チャット開始を許可しない
    if (chatInput.disabled) {
        return;
    }

    // 会話履歴が存在する場合は確認ダイアログを表示
    const hasMessages = chatMessages.children.length > 1; // ウェルカムメッセージ以外のメッセージが存在
    if (hasMessages) {
        const confirmed = confirm('新しい会話を開始しますか？現在のチャット履歴はクリアされます。');
        if (!confirmed) {
            return;
        }
    }

    // セッションをクリア
    createNewSession();

    // 入力欄にフォーカス
    chatInput.focus();

    // チャットを最上部にスクロール
    chatMessages.scrollTop = 0;
}

// Load course statistics
async function loadCourseStats() {
    try {
        console.log('Loading course stats...');
        const response = await fetch(`${API_URL}/courses`);
        if (!response.ok) throw new Error('Failed to load course stats');
        
        const data = await response.json();
        console.log('Course data received:', data);
        
        // Update stats in UI
        if (totalCourses) {
            totalCourses.textContent = data.total_courses;
        }
        
        // Update course titles
        if (courseTitles) {
            if (data.course_titles && data.course_titles.length > 0) {
                courseTitles.innerHTML = data.course_titles
                    .map(title => `<div class="course-title-item">${title}</div>`)
                    .join('');
            } else {
                courseTitles.innerHTML = '<span class="no-courses">No courses available</span>';
            }
        }
        
    } catch (error) {
        console.error('Error loading course stats:', error);
        // Set default values on error
        if (totalCourses) {
            totalCourses.textContent = '0';
        }
        if (courseTitles) {
            courseTitles.innerHTML = '<span class="error">Failed to load courses</span>';
        }
    }
}