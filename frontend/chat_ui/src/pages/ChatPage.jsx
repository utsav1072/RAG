import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { RAGAPI } from '../auth/api'
import { useAuth } from '../auth/AuthContext'
import DocumentSidebar from '../components/DocumentSidebar'

export default function ChatPage() {
  const { user, logout } = useAuth()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true) // Default to open on desktop
  const endRef = useRef(null)

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const ask = async () => {
    const q = input.trim()
    if (!q) return
    setInput('')
    setMessages((m) => [...m, { role: 'user', content: q }])
    setLoading(true)
    try {
      const res = await RAGAPI.query({ query: q, top_k: 4, generate: true })
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          content: res.answer || 'No answer',
          citations: res.citations || [],
          results: res.results || [],
        },
      ])
    } catch (e) {
      setMessages((m) => [...m, { role: 'assistant', content: e?.response?.data?.detail || 'Error' }])
    } finally {
      setLoading(false)
    }
  }

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      ask()
    }
  }

  return (
    <div className="h-screen flex bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
      {/* Sidebar */}
      <DocumentSidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      
      {/* Main Content */}
      <div className="flex-1 flex flex-col lg:ml-0">
        {/* Header */}
        <header className="glass border-b border-white/20 p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="hidden lg:flex items-center gap-2 px-3 py-2 bg-white/50 hover:bg-white/70 rounded-lg transition-all duration-200 text-sm font-medium"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Documents
          </button>
          <div className="w-8 h-8 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">R</span>
          </div>
          <h1 className="text-xl font-bold gradient-text">RAG Chat</h1>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={() => setSidebarOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-white/50 hover:bg-white/70 rounded-lg transition-all duration-200 text-sm font-medium lg:hidden"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Documents
          </button>
          <Link 
            to="/upload" 
            className="flex items-center gap-2 px-4 py-2 bg-white/50 hover:bg-white/70 rounded-lg transition-all duration-200 text-sm font-medium"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            Upload
          </Link>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-r from-green-400 to-blue-500 rounded-full flex items-center justify-center">
              <span className="text-white font-semibold text-sm">{user?.username?.[0]?.toUpperCase()}</span>
            </div>
            <span className="text-sm font-medium">{user?.username}</span>
          </div>
          <button 
            onClick={logout} 
            className="px-3 py-2 text-red-600 hover:bg-red-50 rounded-lg transition-all duration-200 text-sm font-medium"
          >
            Logout
          </button>
        </div>
      </header>

      {/* Messages */}
      <main className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-24 h-24 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center mb-6">
              <svg className="w-12 h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold gradient-text mb-2">Welcome to RAG Chat!</h2>
            <p className="text-gray-600 max-w-md">
              Upload your documents and start asking questions. I'll help you find answers from your content.
            </p>
          </div>
        )}
        
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'} animate-fadeInUp`}>
            <div className={`flex items-start gap-3 max-w-3xl ${m.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                m.role === 'user' 
                  ? 'bg-gradient-to-r from-blue-500 to-blue-600' 
                  : 'bg-gradient-to-r from-purple-500 to-purple-600'
              }`}>
                {m.role === 'user' ? (
                  <span className="text-white font-semibold text-sm">{user?.username?.[0]?.toUpperCase()}</span>
                ) : (
                  <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                )}
              </div>
              <div className={`rounded-2xl px-4 py-3 shadow-lg ${
                m.role === 'user' 
                  ? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white' 
                  : 'bg-white/80 backdrop-blur-sm border border-white/20'
              }`}>
                <div className="whitespace-pre-wrap text-sm leading-relaxed">{m.content}</div>
                {m.citations?.length ? (
                  <div className={`mt-3 pt-3 border-t ${
                    m.role === 'user' ? 'border-blue-400' : 'border-gray-200'
                  }`}>
                    <div className={`text-xs ${m.role === 'user' ? 'text-blue-100' : 'text-gray-500'}`}>
                      <span className="font-medium">Sources:</span>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {m.citations.map((c, idx) => (
                          <span 
                            key={idx} 
                            className={`px-2 py-1 rounded-full text-xs ${
                              m.role === 'user' 
                                ? 'bg-blue-400/30 text-blue-100' 
                                : 'bg-gray-100 text-gray-600'
                            }`}
                          >
                            [{c.index}] {c.source || 'unknown'}{c.page != null ? ` p.${c.page}` : ''}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>
            </div>
          </div>
        ))}
        
        {loading && (
          <div className="flex justify-start animate-fadeInUp">
            <div className="flex items-start gap-3 max-w-3xl">
              <div className="w-8 h-8 rounded-full bg-gradient-to-r from-purple-500 to-purple-600 flex items-center justify-center flex-shrink-0">
                <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <div className="bg-white/80 backdrop-blur-sm border border-white/20 rounded-2xl px-4 py-3 shadow-lg">
                <div className="flex items-center gap-2">
                  <div className="flex gap-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                  </div>
                  <span className="text-sm text-gray-500">Thinking...</span>
                </div>
              </div>
            </div>
          </div>
        )}
        <div ref={endRef} />
      </main>

      {/* Input */}
      <footer className="glass border-t border-white/20 p-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex gap-3 items-end">
            <div className="flex-1 relative">
              <textarea
                rows={1}
                className="w-full px-4 py-3 bg-white/50 backdrop-blur-sm border border-white/30 rounded-2xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 resize-none placeholder-gray-500"
                placeholder="Ask anything about your documents..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={onKeyDown}
                style={{ minHeight: '48px', maxHeight: '120px' }}
              />
            </div>
            <button 
              onClick={ask} 
              disabled={loading || !input.trim()} 
              className="bg-gradient-to-r from-blue-600 to-purple-600 text-white p-3 rounded-2xl hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 transform hover:scale-105 active:scale-95 shadow-lg"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </footer>
      </div>
    </div>
  )
}


