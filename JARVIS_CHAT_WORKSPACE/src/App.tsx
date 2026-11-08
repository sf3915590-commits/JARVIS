import { useEffect, useMemo, useRef, useState } from 'react'
import type { ChangeEvent, FormEvent, KeyboardEvent } from 'react'
import {
  Activity, ArrowDown, ArrowUpRight, AudioLines, Bot, BrainCircuit, CalendarDays,
  Check, CheckCircle2, ChevronDown, CircleHelp, Code2, Command, File, FileImage,
  FileText, Folder, FolderOpen, Gauge, Globe, Image, Library, ListMusic, LoaderCircle,
  Menu, MessageCircle, MessageSquare, Mic, MicOff, MoreHorizontal, Music2, Paperclip,
  Pause, Play, Plus, Search, Send, Settings, ShieldCheck, SlidersHorizontal,
  Sparkles, Square, Terminal, Upload, Video, Volume2, VolumeX, WandSparkles, X,
  Monitor, Cpu, HardDrive, Zap, Clock3, Trash2, Download, PanelLeftClose
} from 'lucide-react'

type Mode = 'os' | 'chat' | 'music'
type View = 'chat' | 'projects' | 'library' | 'files' | 'schedules' | 'plugins' | 'models' | 'settings'
type Provider = 'openai' | 'anthropic' | 'gemini'
type Attachment = { name: string; size: number; type: string; url: string }
type Message = { id: string; role: 'user' | 'assistant'; content: string; time: string; files?: Attachment[] }
type Chat = { id: string; title: string; updated: number; messages: Message[] }
type ActivityItem = { id: string; text: string; kind: 'done' | 'working' | 'info'; time: string }

const STORE = 'jarvis-workspace-v1'
const nowTime = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
const makeId = () => `${Date.now()}-${Math.random().toString(16).slice(2)}`
const initialChat = (): Chat => ({ id: makeId(), title: 'New conversation', updated: Date.now(), messages: [{ id: makeId(), role: 'assistant', content: "Hello. I'm JARVIS. Your existing local brain.py is selected. Send a message to start a conversation.", time: nowTime() }] })

function App() {
  const [mode, setMode] = useState<Mode>('chat')
  const [view, setView] = useState<View>('chat')
  const [chats, setChats] = useState<Chat[]>(() => {
    try { const raw = localStorage.getItem(STORE); if (raw) return JSON.parse(raw).chats ?? [initialChat()] } catch { /* clean fallback */ }
    return [initialChat()]
  })
  const [activeId, setActiveId] = useState(() => chats[0]?.id ?? '')
  const [draft, setDraft] = useState('')
  const [files, setFiles] = useState<Attachment[]>([])
  const [provider, setProvider] = useState<Provider>('openai')
  const [model, setModel] = useState('gpt-4.1')
  const [backendUrl, setBackendUrl] = useState('http://127.0.0.1:8765/api/chat')
  const [connected, setConnected] = useState(false)
  const [sending, setSending] = useState(false)
  const [voiceEnabled, setVoiceEnabled] = useState(true)
  const [muted, setMuted] = useState(false)
  const [listening, setListening] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [rightOpen, setRightOpen] = useState(true)
  const [modal, setModal] = useState<'settings' | 'schedule' | 'plugin' | null>(null)
  const [search, setSearch] = useState('')
  const [activities, setActivities] = useState<ActivityItem[]>([
    { id: makeId(), text: 'JARVIS Workspace loaded', kind: 'done', time: nowTime() },
    { id: makeId(), text: 'Chat Mode ready — provider connection not configured', kind: 'info', time: nowTime() },
  ])
  const [schedules, setSchedules] = useState<{ id: string; title: string; when: string; active: boolean }[]>([])
  const [scheduleTitle, setScheduleTitle] = useState('')
  const [scheduleWhen, setScheduleWhen] = useState('')
  const [plugins, setPlugins] = useState([{ name: 'OpenAI', detail: 'Chat and reasoning', enabled: false }, { name: 'Anthropic', detail: 'Claude models', enabled: false }, { name: 'Google Gemini', detail: 'Multimodal assistant', enabled: false }, { name: 'Local Ollama', detail: 'Local models', enabled: false }, { name: 'MCP Tools', detail: 'External tool connections', enabled: false }])
  const [projects] = useState([{ name: 'JARVIS Core', detail: 'Existing primary OS dashboard', status: 'Awaiting source integration' }, { name: 'JARVIS Music', detail: 'Existing Music Core / JSX', status: 'Awaiting source integration' }, { name: 'JARVIS Chat Mode', detail: 'New conversational workspace', status: 'Workspace scaffold ready' }])
  const [libraryItems, setLibraryItems] = useState<Attachment[]>([])
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const recognitionRef = useRef<any>(null)
  const activeChat = chats.find(c => c.id === activeId) ?? chats[0]
  const messages = activeChat?.messages ?? []

  useEffect(() => { localStorage.setItem(STORE, JSON.stringify({ chats })); }, [chats])
  useEffect(() => { if (!activeId && chats[0]) setActiveId(chats[0].id) }, [activeId, chats])
  useEffect(() => { scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' }) }, [messages.length, sending, view])
  useEffect(() => { document.title = `JARVIS — ${mode.toUpperCase()} MODE` }, [mode])

  const addActivity = (text: string, kind: ActivityItem['kind'] = 'info') => setActivities(prev => [{ id: makeId(), text, kind, time: nowTime() }, ...prev].slice(0, 12))
  const updateChat = (id: string, fn: (chat: Chat) => Chat) => setChats(prev => prev.map(c => c.id === id ? fn(c) : c))

  const newChat = () => {
    const chat = initialChat(); setChats(prev => [chat, ...prev]); setActiveId(chat.id); setView('chat'); setMode('chat'); setDraft(''); setFiles([]); addActivity('New conversation created', 'done')
  }
  const selectChat = (id: string) => { setActiveId(id); setView('chat'); setMode('chat') }
  const switchMode = (next: Mode) => {
    // Chat Mode was opened by the original JARVIS dashboard with a returnTo URL.
    // Return to that exact dashboard; Music Mode is activated through a query flag.
    if (next === 'os' || next === 'music') {
      const returnTo = new URLSearchParams(window.location.search).get('returnTo')
      if (returnTo) {
        try {
          const target = new URL(returnTo)
          if (next === 'music') target.searchParams.set('jarvisMode', 'music')
          else target.searchParams.delete('jarvisMode')
          window.location.assign(target.toString())
          return
        } catch (error) {
          console.warn('[JARVIS] Invalid returnTo URL; staying in workspace.', error)
        }
      }
    }
    setMode(next)
    if (next === 'chat') setView('chat')
    addActivity(`Switched to ${next.toUpperCase()} mode`, 'done')
  }
  const addMessage = (chatId: string, message: Message) => updateChat(chatId, c => ({ ...c, title: c.messages.length <= 1 && message.role === 'user' ? message.content.slice(0, 34) || 'New conversation' : c.title, updated: Date.now(), messages: [...c.messages, message] }))

  const sendMessage = async (textOverride?: string) => {
    const text = (textOverride ?? draft).trim()
    if ((!text && files.length === 0) || sending || !activeChat) return
    const selectedFiles = [...files]
    const userMessage: Message = { id: makeId(), role: 'user', content: text, time: nowTime(), files: selectedFiles }
    addMessage(activeChat.id, userMessage)
    setDraft(''); setFiles([]); setSending(true)
    addActivity(`Message sent to ${providerLabel(provider)} (${model})`, 'working')
    try {
      const response = await fetch(backendUrl, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider, model, messages: [...activeChat.messages.filter(m => m.role !== 'assistant' || !m.content.startsWith('Hello. I\'m JARVIS.')), userMessage].map(m => ({ role: m.role, content: m.content })), attachments: selectedFiles.map(f => ({ name: f.name, type: f.type, size: f.size })) })
      })
      if (!response.ok) { const body = await response.text(); throw new Error(body || `Backend returned ${response.status}`) }
      const data = await response.json()
      const answer = String(data.reply ?? data.content ?? 'The provider returned an empty response.')
      addMessage(activeChat.id, { id: makeId(), role: 'assistant', content: answer, time: nowTime() })
      addActivity(`${providerLabel(provider)} response received`, 'done')
      if (voiceEnabled && !muted) speak(answer)
    } catch (error) {
      const reason = error instanceof Error ? error.message : 'Unknown connection error'
      const friendly = reason.includes('Failed to fetch') ? `I couldn't reach the local JARVIS backend at ${backendUrl}. Start the backend and configure its provider API key, then try again.` : `The AI request failed: ${reason}`
      addMessage(activeChat.id, { id: makeId(), role: 'assistant', content: friendly, time: nowTime() })
      addActivity('AI request failed — inspect backend connection and provider settings', 'info')
    } finally { setSending(false) }
  }

  const speak = (text: string) => {
    if (!('speechSynthesis' in window)) { addActivity('Speech synthesis is not supported in this browser', 'info'); return }
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.rate = 1.02; utterance.pitch = 0.96
    window.speechSynthesis.speak(utterance)
  }
  const stopSpeaking = () => { window.speechSynthesis?.cancel(); addActivity('Voice playback stopped', 'done') }

  const toggleMic = () => {
    if (muted) { addActivity('Microphone is muted. Use Unmute to activate voice input.', 'info'); return }
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SpeechRecognition) { addActivity('Voice input is not supported in this browser. Try a Chromium-based browser.', 'info'); return }
    if (listening) { recognitionRef.current?.stop(); setListening(false); return }
    const recognition = new SpeechRecognition(); recognition.lang = 'en-IN'; recognition.continuous = false; recognition.interimResults = true
    recognition.onstart = () => { setListening(true); addActivity('Voice input started', 'working') }
    recognition.onresult = (event: any) => {
      let transcript = ''
      for (let i = event.resultIndex; i < event.results.length; i++) transcript += event.results[i][0].transcript
      setDraft(transcript)
      if (event.results[event.results.length - 1].isFinal) {
        const command = transcript.toLowerCase().trim()
        if (command.includes('switch to os mode') || command.includes('back to os mode') || command.includes('exit chat mode')) switchMode('os')
        else if (command.includes('switch to music mode')) switchMode('music')
        else addActivity('Voice transcription captured — review and send', 'done')
      }
    }
    recognition.onerror = () => { setListening(false); addActivity('Voice input stopped due to a browser microphone error', 'info') }
    recognition.onend = () => setListening(false)
    recognitionRef.current = recognition; recognition.start()
  }
  const toggleMute = () => {
    if (!muted) { recognitionRef.current?.stop(); window.speechSynthesis?.cancel(); setListening(false); setMuted(true); addActivity('JARVIS microphone muted', 'done') }
    else { setMuted(false); addActivity('JARVIS microphone unmuted', 'done') }
  }

  const handleFiles = (event: ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(event.target.files ?? []).map(file => ({ name: file.name, size: file.size, type: file.type || 'application/octet-stream', url: URL.createObjectURL(file) }))
    setFiles(prev => [...prev, ...selected]); setLibraryItems(prev => [...selected, ...prev]); addActivity(`${selected.length} file(s) attached`, 'done'); event.target.value = ''
  }
  const submit = (event: FormEvent) => { event.preventDefault(); sendMessage() }
  const handleInputKey = (event: KeyboardEvent<HTMLTextAreaElement>) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); sendMessage() } }
  const filteredChats = useMemo(() => chats.filter(c => c.title.toLowerCase().includes(search.toLowerCase())), [chats, search])
  const saveSchedule = () => { if (!scheduleTitle.trim() || !scheduleWhen) return; setSchedules(prev => [{ id: makeId(), title: scheduleTitle.trim(), when: scheduleWhen, active: true }, ...prev]); setScheduleTitle(''); setScheduleWhen(''); setModal(null); addActivity('Schedule saved locally', 'done') }
  const deleteChat = (id: string) => { const rest = chats.filter(c => c.id !== id); const next = rest.length ? rest : [initialChat()]; setChats(next); if (activeId === id) setActiveId(next[0].id); addActivity('Conversation deleted', 'done') }

  return <div className="app-shell">
    <div className="ambient ambient-one" /><div className="ambient ambient-two" />
    <header className="topbar">
      <div className="brand"><div className="brand-core"><span /></div><div><div className="brand-name">JARVIS</div><div className="brand-tag">YOUR AI. YOUR SYSTEM.</div></div></div>
      <button className="icon-button mobile-menu" onClick={() => setSidebarOpen(v => !v)} aria-label="Toggle sidebar"><Menu size={18}/></button>
      <div className="mode-switch">
        <ModeButton active={mode === 'os'} onClick={() => switchMode('os')} icon={<Monitor size={16}/>} label="OS Mode" />
        <ModeButton active={mode === 'chat'} onClick={() => switchMode('chat')} icon={<MessageSquare size={16}/>} label="Chat Mode" />
        <ModeButton active={mode === 'music'} onClick={() => switchMode('music')} icon={<Music2 size={16}/>} label="Music Mode" />
      </div>
      <div className="top-actions">
        <div className={`listening-pill ${listening ? 'live' : ''}`}><span className="live-dot" />{muted ? 'Microphone muted' : listening ? 'Listening…' : 'Voice ready'}</div>
        <button className={`top-control mute-control ${muted ? 'active' : ''}`} onClick={toggleMute}><MicOff size={15}/> <span>Mute</span></button>
        <button className={`top-control ${!muted ? 'active-soft' : ''}`} onClick={() => { setMuted(false); addActivity('JARVIS microphone unmuted', 'done') }}><Mic size={15}/> <span>Unmute</span></button>
        <button className="window-control" title="Minimize Chat Mode" onClick={() => switchMode('os')}><span>—</span></button>
      </div>
    </header>

    {mode === 'os' ? <IntegrationView type="os" onBack={() => switchMode('chat')} /> : mode === 'music' ? <IntegrationView type="music" onBack={() => switchMode('chat')} /> : <div className={`workspace ${!sidebarOpen ? 'sidebar-collapsed' : ''} ${!rightOpen ? 'right-collapsed' : ''}`}>
      <aside className="sidebar">
        <button className="new-chat" onClick={newChat}><Plus size={19}/><span>New Chat</span><kbd>Ctrl + N</kbd></button>
        <div className="side-search"><Search size={15}/><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search chats" /></div>
        <nav className="nav-list">
          <NavButton active={view === 'chat'} onClick={() => setView('chat')} icon={<MessageCircle/>} label="Chats" badge={String(chats.length)} />
          <NavButton active={view === 'projects'} onClick={() => setView('projects')} icon={<Folder/>} label="Projects" />
          <NavButton active={view === 'library'} onClick={() => setView('library')} icon={<Library/>} label="Library" />
          <NavButton active={view === 'files'} onClick={() => setView('files')} icon={<File/>} label="Files" />
          <NavButton active={view === 'schedules'} onClick={() => setView('schedules')} icon={<CalendarDays/>} label="Schedules" />
          <NavButton active={view === 'plugins'} onClick={() => setView('plugins')} icon={<Zap/>} label="Plugins" />
          <NavButton active={view === 'models'} onClick={() => setView('models')} icon={<BrainCircuit/>} label="AI Models" />
          <NavButton active={view === 'settings'} onClick={() => setView('settings')} icon={<Settings/>} label="Settings" />
        </nav>
        <div className="sidebar-divider" />
        <div className="side-section-head">RECENT CONVERSATIONS <button onClick={newChat} title="New chat"><Plus size={14}/></button></div>
        <div className="chat-list">{filteredChats.slice(0, 10).map(chat => <div className={`chat-row ${chat.id === activeId ? 'selected' : ''}`} key={chat.id}><button onClick={() => selectChat(chat.id)}><MessageSquare size={14}/><span>{chat.title}</span></button><button className="row-delete" title="Delete conversation" onClick={() => deleteChat(chat.id)}><X size={13}/></button></div>)}</div>
        <div className="sidebar-bottom">
          <div className="quick-launch-label">QUICK LAUNCH</div>
          <div className="quick-launch">
            <QuickLaunch label="VS Code" mark="</>" onClick={() => addActivity('VS Code launch requires the connected Windows control bridge', 'info')}/>
            <QuickLaunch label="Chrome" mark="◉" onClick={() => addActivity('Chrome launch requires the connected Windows control bridge', 'info')}/>
            <QuickLaunch label="YouTube" mark="▶" onClick={() => addActivity('YouTube opening requires the connected browser bridge', 'info')}/>
            <QuickLaunch label="WhatsApp" mark="◌" onClick={() => addActivity('WhatsApp access requires an authorized desktop connector', 'info')}/>
          </div>
          <div className="profile-card"><div className="avatar">F</div><div className="profile-info"><strong>Farhan</strong><span><i/> JARVIS Builder</span></div><button title="Settings" onClick={() => setView('settings')}><Settings size={17}/></button></div>
        </div>
      </aside>

      <main className="main-panel">
        {view === 'chat' ? <>
          <div className="conversation-header"><div><div className="eyebrow">PERSONAL AI WORKSPACE</div><h1>{activeChat?.title ?? 'New conversation'}</h1></div><div className="header-tools"><span className="provider-indicator"><span className={connected ? 'green-dot' : 'amber-dot'} />{connected ? providerLabel(provider) : 'Provider not connected'}</span><button className="icon-button" title="Toggle activity panel" onClick={() => setRightOpen(v => !v)}><SlidersHorizontal size={17}/></button><button className="icon-button" title="More options" onClick={() => addActivity('Conversation options opened', 'info')}><MoreHorizontal size={18}/></button></div></div>
          <div className="messages-scroll" ref={scrollRef}>
            {messages.length === 1 && <div className="welcome-block"><div className="welcome-orb"><div className="orb-inner"/></div><div className="eyebrow">JARVIS INTELLIGENCE</div><h2>How can I help you<br/><em>build something great?</em></h2><p>Ask a question, plan a project, analyze a file, or hand JARVIS a development task.</p><div className="suggestion-grid"><Suggestion icon={<Code2/>} title="Build a project" text="Plan and create a real application" onClick={() => setDraft('Help me plan and build a production-ready application. Start by analyzing the requirements.')} /><Suggestion icon={<BrainCircuit/>} title="Think it through" text="Explore an idea or solve a problem" onClick={() => setDraft('Help me think through an idea and make a practical plan.')} /><Suggestion icon={<FileText/>} title="Analyze files" text="Review documents, images, and code" onClick={() => setDraft('Please analyze the files I attach and summarize the important details.')} /><Suggestion icon={<Terminal/>} title="Code with JARVIS" text="Inspect, edit, and test a codebase" onClick={() => setDraft('Act as my development agent. First inspect the project and propose a safe implementation plan.')} /></div></div>}
            <div className="message-stack">{messages.map(message => <MessageBubble key={message.id} message={message} onSpeak={speak} />)}</div>
            {sending && <div className="typing-row"><div className="assistant-mark small"><span/></div><div className="typing-card"><span className="typing-dots"><i/><i/><i/></span><span>JARVIS is working…</span></div></div>}
          </div>
          <div className="composer-area">
            {files.length > 0 && <div className="attachment-tray">{files.map((file, i) => <div className="attachment-chip" key={`${file.name}-${i}`}><FileText size={14}/><span>{file.name}</span><button onClick={() => setFiles(prev => prev.filter((_, index) => index !== i))}><X size={13}/></button></div>)}</div>}
            <form className="composer" onSubmit={submit}>
              <label className="composer-add" title="Attach files"><Plus size={19}/><input hidden type="file" multiple onChange={handleFiles}/></label>
              <textarea ref={inputRef} value={draft} onChange={e => setDraft(e.target.value)} onKeyDown={handleInputKey} placeholder="Message JARVIS…" rows={1}/>
              <div className="composer-actions"><label title="Attach file"><Paperclip size={18}/><input hidden type="file" multiple onChange={handleFiles}/></label><label title="Add image"><Image size={18}/><input hidden type="file" accept="image/*" multiple onChange={handleFiles}/></label><label title="Add video"><Video size={18}/><input hidden type="file" accept="video/*" multiple onChange={handleFiles}/></label><button type="button" title={voiceEnabled ? 'Voice replies on' : 'Voice replies off'} className={voiceEnabled ? 'voice-on' : ''} onClick={() => setVoiceEnabled(v => !v)}><Volume2 size={18}/></button><button type="button" title={listening ? 'Stop voice input' : 'Speak'} className={listening ? 'voice-on' : ''} onClick={toggleMic}><Mic size={18}/></button><button className="send-button" type="submit" disabled={sending || (!draft.trim() && files.length === 0)} title="Send message"><ArrowUpRight size={20}/></button></div>
            </form>
            <div className="composer-footer"><span>JARVIS can make mistakes. Verify important actions before execution.</span><span><kbd>Enter</kbd> to send · <kbd>Shift + Enter</kbd> for new line</span></div>
            <div className="tool-pills"><button onClick={() => setDraft('Help me write or review code. First ask which project and files to inspect.') }><Code2 size={14}/> Code</button><button onClick={() => setDraft('Help me write a polished document. Ask for the purpose and audience if needed.') }><WandSparkles size={14}/> Write</button><button onClick={() => setView('files')}><Activity size={14}/> Analyze</button><button onClick={() => setDraft('Help me plan a production-ready website, including frontend, backend, database, authentication, testing and deployment.') }><Globe size={14}/> Build Website</button><button onClick={() => addActivity('Automation requests need the Windows control bridge connected', 'info')}><Zap size={14}/> Automate Task</button></div>
          </div>
        </> : <SecondaryView view={view} chats={chats} projects={projects} libraryItems={libraryItems} schedules={schedules} plugins={plugins} setPlugins={setPlugins} setView={setView} setModal={setModal} addActivity={addActivity} setProvider={setProvider} provider={provider} setModel={setModel} model={model} connected={connected} setConnected={setConnected} backendUrl={backendUrl} setBackendUrl={setBackendUrl}/>} 
      </main>

      {rightOpen && <aside className="right-panel">
        <section className="glass-card status-card"><div className="card-heading"><span><Gauge size={16}/> SYSTEM STATUS</span><span className="online"><i/> UI Online</span></div><div className="stat-grid"><Stat label="CPU" value="—" icon={<Cpu/>}/><Stat label="RAM" value="—" icon={<HardDrive/>}/><Stat label="GPU" value="—" icon={<Activity/>}/></div><div className="status-note">Live hardware metrics appear after the Windows system bridge is connected.</div></section>
        <section className="glass-card agents-card"><div className="card-heading"><span><BrainCircuit size={16}/> AGENT WORKSPACE</span><span className="tiny-label">LOCAL UI</span></div><AgentRow icon={<Bot/>} name="JARVIS Core" state="UI Ready"/><AgentRow icon={<Code2/>} name="Development Agent" state="Not connected" muted/><AgentRow icon={<Zap/>} name="Automation Agent" state="Not connected" muted/><AgentRow icon={<Music2/>} name="Media Agent" state="Module pending" muted/><AgentRow icon={<Monitor/>} name="System Agent" state="Bridge pending" muted/></section>
        <section className="glass-card activity-card"><div className="card-heading"><span><Activity size={16}/> LIVE ACTIVITY</span><button className="text-link" onClick={() => setActivities([])}>Clear</button></div><div className="activity-list">{activities.slice(0, 7).map(item => <div className="activity-line" key={item.id}><span className={`activity-icon ${item.kind}`}>{item.kind === 'done' ? <Check size={11}/> : item.kind === 'working' ? <LoaderCircle size={11}/> : <span>·</span>}</span><div><p>{item.text}</p><time>{item.time}</time></div></div>)}</div></section>
        <section className="glass-card provider-card"><div className="card-heading"><span><ShieldCheck size={16}/> AI CONNECTION</span><span className={connected ? 'online' : 'offline'}>{connected ? 'Connected' : 'Not configured'}</span></div><div className="provider-select"><select value={provider} onChange={e => { setProvider(e.target.value as Provider); setConnected(false) }}><option value="openai">OpenAI / ChatGPT</option><option value="anthropic">Anthropic / Claude</option><option value="gemini">Google Gemini</option></select><button onClick={() => setView('settings')}>Configure</button></div><div className="status-note">API credentials stay in the local backend environment, not in this browser UI.</div></section>
      </aside>}
    </div>}

    {modal && <Modal title={modal === 'schedule' ? 'Create schedule' : modal === 'plugin' ? 'Add connection' : 'Settings'} onClose={() => setModal(null)}>{modal === 'schedule' ? <div className="modal-form"><p className="modal-copy">Create a local reminder entry. Background delivery requires the JARVIS scheduler service.</p><label>Reminder title<input value={scheduleTitle} onChange={e => setScheduleTitle(e.target.value)} placeholder="e.g. Continue JARVIS coding agent" /></label><label>Date and time<input type="datetime-local" value={scheduleWhen} onChange={e => setScheduleWhen(e.target.value)} /></label><button className="primary-button" onClick={saveSchedule} disabled={!scheduleTitle.trim() || !scheduleWhen}>Save schedule</button></div> : <p className="modal-copy">Manage JARVIS workspace configuration.</p>}</Modal>}
  </div>
}

function providerLabel(provider: Provider) { return provider === 'openai' ? 'ChatGPT' : provider === 'anthropic' ? 'Claude' : 'Gemini' }
function ModeButton({ active, onClick, icon, label }: { active: boolean; onClick: () => void; icon: React.ReactNode; label: string }) { return <button className={`mode-button ${active ? 'active' : ''}`} onClick={onClick}>{icon}{label}</button> }
function NavButton({ active, onClick, icon, label, badge }: { active: boolean; onClick: () => void; icon: React.ReactNode; label: string; badge?: string }) { return <button className={`nav-button ${active ? 'active' : ''}`} onClick={onClick}>{icon}<span>{label}</span>{badge && <b>{badge}</b>}</button> }
function QuickLaunch({ label, mark, onClick }: { label: string; mark: string; onClick: () => void }) { return <button className="quick-app" title={`${label} — Windows bridge required`} onClick={onClick}>{mark}</button> }
function Stat({ label, value, icon }: { label: string; value: string; icon: React.ReactNode }) { return <div className="stat"><div className="stat-icon">{icon}</div><strong>{value}</strong><span>{label}</span></div> }
function AgentRow({ icon, name, state, muted }: { icon: React.ReactNode; name: string; state: string; muted?: boolean }) { return <div className={`agent-row ${muted ? 'muted' : ''}`}><span className="agent-icon">{icon}</span><span>{name}</span><small>{state}</small></div> }
function Suggestion({ icon, title, text, onClick }: { icon: React.ReactNode; title: string; text: string; onClick: () => void }) { return <button className="suggestion" onClick={onClick}><span className="suggestion-icon">{icon}</span><strong>{title}</strong><small>{text}</small></button> }
function MessageBubble({ message, onSpeak }: { message: Message; onSpeak: (text: string) => void }) { return <article className={`message ${message.role}`}><div className="message-avatar">{message.role === 'assistant' ? <div className="assistant-mark"><span/></div> : <span>F</span>}</div><div className="message-content"><div className="message-meta"><strong>{message.role === 'assistant' ? 'JARVIS' : 'You'}</strong><time>{message.time}</time></div><div className="message-text">{message.content}</div>{message.files?.length ? <div className="message-files">{message.files.map((f, i) => <div key={i}><FileText size={13}/>{f.name}</div>)}</div> : null}{message.role === 'assistant' && <div className="message-tools"><button onClick={() => onSpeak(message.content)} title="Read aloud"><Volume2 size={14}/> Listen</button><button onClick={() => navigator.clipboard?.writeText(message.content)} title="Copy response"><Command size={13}/> Copy</button></div>}</div></article> }

function SecondaryView(props: any) {
  const { view, projects, libraryItems, schedules, plugins, setPlugins, setView, setModal, addActivity, setProvider, provider, setModel, model, connected, setConnected, backendUrl, setBackendUrl } = props
  const titleMap: Record<View, string> = { chat: 'Chats', projects: 'Projects', library: 'Library', files: 'Files', schedules: 'Schedules', plugins: 'Plugins & Connections', models: 'AI Models', settings: 'Settings' }
  return <div className="secondary-view"><div className="secondary-head"><div><div className="eyebrow">JARVIS WORKSPACE</div><h1>{titleMap[view as View]}</h1></div>{view === 'schedules' && <button className="primary-button" onClick={() => setModal('schedule')}><Plus size={16}/> New schedule</button>}</div>
    {view === 'projects' && <div className="content-grid">{projects.map((p: any) => <div className="content-card" key={p.name}><div className="content-card-icon"><FolderOpen/></div><h3>{p.name}</h3><p>{p.detail}</p><span className="status-badge">{p.status}</span><button className="subtle-button" onClick={() => addActivity(`${p.name}: source integration is pending`, 'info')}>Open project <ArrowUpRight size={14}/></button></div>)}</div>}
    {view === 'library' && <div className="content-card wide"><div className="empty-state-icon"><Library/></div><h3>Your JARVIS Library</h3><p>Files attached in this workspace are listed here for the current browser session. Persistent indexing and semantic search will be connected to the JARVIS backend.</p>{libraryItems.length === 0 ? <span className="status-badge">No files added yet</span> : libraryItems.map((f: Attachment, i: number) => <div className="file-row" key={i}><FileText size={16}/><span>{f.name}</span><small>{(f.size / 1024).toFixed(1)} KB</small><a href={f.url} download={f.name}><Download size={14}/></a></div>)}</div>}
    {view === 'files' && <div className="content-card wide"><div className="empty-state-icon"><Upload/></div><h3>File workspace</h3><p>Attach files in Chat Mode to review them here. This scaffold records attachment metadata locally; project-folder access and file writes require the Windows permission bridge.</p><button className="primary-button" onClick={() => setView('chat')}><Paperclip size={15}/> Go to chat attachments</button></div>}
    {view === 'schedules' && <div className="content-card wide"><div className="empty-state-icon"><CalendarDays/></div><h3>Schedules & reminders</h3><p>Reminder entries created here are stored in this UI session. Reliable background notifications require the JARVIS scheduler service.</p>{schedules.length === 0 ? <span className="status-badge">No schedules created</span> : schedules.map((s: any) => <div className="schedule-row" key={s.id}><CalendarDays size={16}/><span>{s.title}</span><time>{new Date(s.when).toLocaleString()}</time><span className="green-text">{s.active ? 'Active' : 'Paused'}</span></div>)}</div>}
    {view === 'plugins' && <div className="settings-list">{plugins.map((p: any, i: number) => <div className="setting-row" key={p.name}><div className="setting-icon"><Zap size={18}/></div><div className="setting-text"><strong>{p.name}</strong><small>{p.detail}</small></div><span className={p.enabled ? 'green-text' : 'muted-text'}>{p.enabled ? 'Enabled' : 'Not connected'}</span><button className={`toggle ${p.enabled ? 'on' : ''}`} onClick={() => { setPlugins((prev: any[]) => prev.map((x, j) => j === i ? { ...x, enabled: !x.enabled } : x)); addActivity(`${p.name} connection preference changed. Backend credentials and connector still required.`, 'info') }}><i/></button></div>)}</div>}
    {view === 'models' && <div className="content-card wide"><div className="empty-state-icon"><BrainCircuit/></div><h3>Choose your AI provider</h3><p>Model routing is handled by the local JARVIS backend. Select a provider and model; API keys belong in the backend environment file, never in frontend source.</p><div className="form-grid"><label>Provider<select value={provider} onChange={e => { setProvider(e.target.value as Provider); setConnected(false) }}><option value="openai">OpenAI / ChatGPT</option><option value="anthropic">Anthropic / Claude</option><option value="gemini">Google Gemini</option></select></label><label>Model<input value={model} onChange={e => setModel(e.target.value)} placeholder="Model identifier"/></label></div><div className="button-row"><button className="primary-button" onClick={() => setView('settings')}>Configure backend</button><span className="status-badge">{connected ? 'Connection checked' : 'Not connected'}</span></div></div>}
    {view === 'settings' && <div className="content-card wide"><div className="empty-state-icon"><Settings/></div><h3>Backend connection</h3><p>Chat Mode sends requests to a local JARVIS backend. Keep provider API keys on the backend machine. Do not paste private API keys into this browser page.</p><div className="form-grid"><label>Chat API endpoint<input value={backendUrl} onChange={e => setBackendUrl(e.target.value)} /></label><label>Selected provider<select value={provider} onChange={e => { setProvider(e.target.value as Provider); setConnected(false) }}><option value="openai">OpenAI / ChatGPT</option><option value="anthropic">Anthropic / Claude</option><option value="gemini">Google Gemini</option></select></label><label>Model identifier<input value={model} onChange={e => setModel(e.target.value)}/></label></div><div className="button-row"><button className="primary-button" onClick={async () => { try { const health = backendUrl.replace(/\/api\/chat\/?$/, '/api/health'); const r = await fetch(health); if (!r.ok) throw new Error(`HTTP ${r.status}`); setConnected(true); addActivity('Local JARVIS backend health check passed', 'done') } catch { setConnected(false); addActivity('Backend health check failed. Start backend/server.py and verify the endpoint.', 'info') } }}>Test backend connection</button><span className={connected ? 'green-text' : 'muted-text'}>{connected ? 'Backend reachable' : 'Not verified'}</span></div><div className="notice"><ShieldCheck size={16}/> JARVIS Local Brain uses your existing brain.py. Optional cloud-provider keys stay on the backend, never in this browser.</div></div>}
  </div>
}
function IntegrationView({ type, onBack }: { type: 'os' | 'music'; onBack: () => void }) { return <div className="integration-view"><div className="integration-card"><div className="integration-icon">{type === 'os' ? <Monitor size={28}/> : <Music2 size={28}/>}</div><div className="eyebrow">JARVIS {type.toUpperCase()} MODE</div><h1>{type === 'os' ? 'Primary OS Core' : 'Music Core'}</h1><p>{type === 'os' ? 'This mode is reserved for your existing primary JARVIS Core dashboard. The original Core JSX and its control bridge must be connected here; this workspace does not replace it.' : 'This mode is reserved for your existing Music Core JSX and playback engine. Connect the original Music Core module here to preserve its current functionality.'}</p><div className="integration-state"><span className="amber-dot"/> Existing source module required for integration</div><button className="primary-button" onClick={onBack}>Return to Chat Mode <ArrowUpRight size={15}/></button></div></div> }
function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) { return <div className="modal-backdrop" onClick={onClose}><div className="modal-card" onClick={e => e.stopPropagation()}><div className="modal-head"><h2>{title}</h2><button onClick={onClose}><X size={17}/></button></div>{children}</div></div> }

export default App
