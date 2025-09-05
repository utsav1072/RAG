import { useState, useRef } from 'react'
import { Link } from 'react-router-dom'
import { RAGAPI } from '../auth/api'
import { useAuth } from '../auth/AuthContext'

export default function UploadPage() {
  const { user, logout } = useAuth()
  const [files, setFiles] = useState([])
  const [source, setSource] = useState('')
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(false)
  const [dragActive, setDragActive] = useState(false)
  const fileInputRef = useRef(null)

  const onSubmit = async (e) => {
    e.preventDefault()
    if (!files.length) return
    setStatus('')
    setLoading(true)
    try {
      const res = await RAGAPI.upload(files, source)
      setStatus(`✅ Successfully ingested ${res.files?.length || 0} files, ${res.chunks} chunks`)
      setFiles([])
      setSource('')
    } catch (e) {
      setStatus(`❌ ${e?.response?.data?.detail || 'Upload failed'}`)
    } finally {
      setLoading(false)
    }
  }

  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFiles(Array.from(e.dataTransfer.files))
    }
  }

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFiles(Array.from(e.target.files))
    }
  }

  const removeFile = (index) => {
    setFiles(files.filter((_, i) => i !== index))
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
      {/* Header */}
      <header className="glass border-b border-white/20 p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gradient-to-r from-green-600 to-blue-600 rounded-lg flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          <h1 className="text-xl font-bold gradient-text">Upload Documents</h1>
        </div>
        <div className="flex items-center gap-4">
          <Link 
            to="/chat" 
            className="flex items-center gap-2 px-4 py-2 bg-white/50 hover:bg-white/70 rounded-lg transition-all duration-200 text-sm font-medium"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            Chat
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

      {/* Main Content */}
      <main className="max-w-4xl mx-auto p-6">
        <div className="glass rounded-2xl shadow-2xl p-8 backdrop-blur-lg animate-fadeInUp">
          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold gradient-text mb-2">Upload Your Documents</h2>
            <p className="text-gray-600">Upload PDFs, text files, and other documents to build your knowledge base</p>
          </div>

          <form onSubmit={onSubmit} className="space-y-6">
            {/* Source Label */}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">Source Label (Optional)</label>
              <input 
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 bg-white/50 backdrop-blur-sm" 
                value={source} 
                onChange={(e) => setSource(e.target.value)}
                placeholder="e.g., 'Company Handbook', 'Research Papers'"
              />
            </div>

            {/* File Upload Area */}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">Documents</label>
              <div
                className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all duration-200 ${
                  dragActive 
                    ? 'border-blue-500 bg-blue-50/50' 
                    : 'border-gray-300 hover:border-gray-400'
                }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  onChange={handleFileSelect}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  accept=".pdf,.txt,.md,.csv,.log"
                />
                <div className="space-y-4">
                  <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center mx-auto">
                    <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-lg font-medium text-gray-700">
                      {dragActive ? 'Drop files here' : 'Drag & drop files here'}
                    </p>
                    <p className="text-sm text-gray-500 mt-1">
                      or <span className="text-blue-600 font-medium">browse files</span>
                    </p>
                    <p className="text-xs text-gray-400 mt-2">
                      Supports PDF, TXT, MD, CSV, LOG files (max 20MB each)
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Selected Files */}
            {files.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-sm font-medium text-gray-700">Selected Files ({files.length})</h3>
                <div className="space-y-2">
                  {files.map((file, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-white/50 rounded-lg border border-white/30">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-gradient-to-r from-green-500 to-blue-500 rounded-lg flex items-center justify-center">
                          <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                          </svg>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-700">{file.name}</p>
                          <p className="text-xs text-gray-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => removeFile(index)}
                        className="p-1 text-red-500 hover:bg-red-50 rounded-lg transition-colors duration-200"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Upload Button */}
            <button 
              type="submit" 
              disabled={loading || !files.length} 
              className="w-full bg-gradient-to-r from-green-600 to-blue-600 text-white font-semibold py-3 px-6 rounded-xl hover:from-green-700 hover:to-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 transform hover:scale-105 active:scale-95 shadow-lg"
            >
              {loading ? (
                <div className="flex items-center justify-center">
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                  Uploading and processing...
                </div>
              ) : (
                `Upload ${files.length} file${files.length !== 1 ? 's' : ''}`
              )}
            </button>

            {/* Status */}
            {status && (
              <div className={`p-4 rounded-lg text-sm ${
                status.includes('✅') 
                  ? 'bg-green-50 border border-green-200 text-green-700' 
                  : 'bg-red-50 border border-red-200 text-red-700'
              } animate-fadeInUp`}>
                {status}
              </div>
            )}
          </form>
        </div>
      </main>
    </div>
  )
}


