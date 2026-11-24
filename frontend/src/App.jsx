import { useEffect, useRef, useState } from 'react'
import {
  Bot,
  Database,
  Gauge,
  Send,
  Sparkles,
  User,
  Zap,
} from 'lucide-react'

import './App.css'

const API_URL =
  import.meta.env.VITE_API_URL || 'http://localhost:8000'

function createSessionId() {
  return `session-${Date.now()}-${Math.random()
    .toString(36)
    .slice(2, 8)}`
}

function App() {
  const [sessionId, setSessionId] = useState(
    createSessionId()
  )
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: 'smooth',
    })
  }, [messages, loading])

  async function sendMessage(event) {
    event?.preventDefault()

    const trimmedMessage = input.trim()

    if (!trimmedMessage || loading) {
      return
    }

    const userMessage = {
      role: 'user',
      content: trimmedMessage,
    }

    setMessages((current) => [
      ...current,
      userMessage,
    ])

    setInput('')
    setError('')
    setLoading(true)

    try {
      const response = await fetch(
        `${API_URL}/chat`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            session_id: sessionId,
            message: trimmedMessage,
          }),
        }
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          data.detail ||
            'Unable to get an AI response.'
        )
      }

      const assistantMessage = {
        role: 'assistant',
        content: data.reply,
        metadata: data.metadata,
      }

      setMessages((current) => [
        ...current,
        assistantMessage,
      ])
    } catch (requestError) {
      setError(
        requestError.message ||
          'Something went wrong.'
      )
    } finally {
      setLoading(false)
    }
  }

  function startNewChat() {
    setSessionId(createSessionId())
    setMessages([])
    setInput('')
    setError('')
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-icon">
            <Sparkles size={20} />
          </div>

          <div>
            <h1>Lyftr AI</h1>
            <p>Resilient AI Chat</p>
          </div>
        </div>

        <button
          className="new-chat-button"
          onClick={startNewChat}
          type="button"
        >
          New chat
        </button>
      </header>

      <main className="chat-container">
        {messages.length === 0 && (
          <section className="welcome">
            <div className="welcome-icon">
              <Bot size={32} />
            </div>

            <h2>How can I help you?</h2>

            <p>
              Ask anything. Your conversation is
              persisted securely and powered by a
              resilient multi-key AI backend.
            </p>

            <div className="feature-row">
              <span>
                <Zap size={15} />
                Automatic failover
              </span>

              <span>
                <Database size={15} />
                Persistent sessions
              </span>

              <span>
                <Gauge size={15} />
                Response caching
              </span>
            </div>
          </section>
        )}

        <section className="messages">
          {messages.map((message, index) => (
            <article
              key={`${message.role}-${index}`}
              className={`message-row ${message.role}`}
            >
              <div className="avatar">
                {message.role === 'user' ? (
                  <User size={18} />
                ) : (
                  <Bot size={18} />
                )}
              </div>

              <div className="message-content">
                <div
                  className="message-bubble"
                  data-testid={
                    message.role === 'assistant'
                      ? 'assistant-message'
                      : undefined
                  }
                >
                  {message.content}
                </div>

                {message.role === 'assistant' &&
                  message.metadata && (
                    <div className="metadata-card">
                      <span
                        data-testid="meta-source"
                        className={
                          message.metadata
                            .resolution_source ===
                          'LLM_CACHE'
                            ? 'cache-badge'
                            : 'live-badge'
                        }
                      >
                        {
                          message.metadata
                            .resolution_source
                        }
                      </span>

                      <span
                        data-testid="meta-model"
                      >
                        {message.metadata.model}
                      </span>

                      <span
                        data-testid="meta-latency"
                      >
                        {
                          message.metadata
                            .latency_ms
                        }{' '}
                        ms
                      </span>

                      <span
                        data-testid="meta-input-tokens"
                      >
                        ↑{' '}
                        {
                          message.metadata
                            .input_tokens
                        }{' '}
                        tokens
                      </span>

                      <span
                        data-testid="meta-output-tokens"
                      >
                        ↓{' '}
                        {
                          message.metadata
                            .output_tokens
                        }{' '}
                        tokens
                      </span>
                    </div>
                  )}
              </div>
            </article>
          ))}

          {loading && (
            <article className="message-row assistant">
              <div className="avatar">
                <Bot size={18} />
              </div>

              <div className="typing-indicator">
                <span />
                <span />
                <span />
              </div>
            </article>
          )}

          <div ref={bottomRef} />
        </section>
      </main>

      <footer className="composer-wrapper">
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        <form
          className="composer"
          onSubmit={sendMessage}
        >
          <textarea
            data-testid="chat-input"
            value={input}
            onChange={(event) =>
              setInput(event.target.value)
            }
            onKeyDown={(event) => {
              if (
                event.key === 'Enter' &&
                !event.shiftKey
              ) {
                event.preventDefault()
                sendMessage()
              }
            }}
            placeholder="Message Lyftr AI..."
            rows={1}
            maxLength={4000}
          />

          <button
            data-testid="send-button"
            className="send-button"
            type="submit"
            disabled={
              loading || !input.trim()
            }
            aria-label="Send message"
          >
            <Send size={18} />
          </button>
        </form>

        <p className="composer-note">
          Session: {sessionId}
        </p>
      </footer>
    </div>
  )
}

export default App