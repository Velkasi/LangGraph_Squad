import { useEffect, useRef, useState, useCallback } from 'react'
import mermaid from 'mermaid'
import ReactMarkdown from 'react-markdown'

// ── Types ─────────────────────────────────────────────────────────────────────

interface TraceEvent {
  ts: string
  kind: string
  agent: string
  payload: Record<string, unknown>
}

interface Message {
  role: 'user' | 'assistant'
  node?: string
  content: string
}

interface RunState {
  events: TraceEvent[]
  mermaid: string
  recordJson: string
  messages: Message[]
  files: string[]
  tokens: { prompt: number; completion: number; total: number }
  exportMsg: string
}

type Tab = 'chat' | 'diagram' | 'trace' | 'log'

const ICONS: Record<string, string> = {
  planner: '📋', architect: '🏗️', dev: '💻', test: '🧪',
  debug: '🐛', reviewer: '🔍', writeup: '📝', analyst: '📊', supervisor: '🎯',
}

const KIND_ICONS: Record<string, string> = {
  llm_call: '🔵', llm_response: '🟢', tool_call: '🟡', tool_result: '🟠',
  memory_op: '🟣', supervisor_route: '🎯', agent_start: '▶', agent_done: '✅', error: '❌',
}

mermaid.initialize({ startOnLoad: false, theme: 'dark' })

// ── Mermaid component ─────────────────────────────────────────────────────────

function MermaidDiagram({ chart }: { chart: string }) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current || !chart.trim()) return
    const id = 'mermaid-' + Date.now()
    mermaid.render(id, chart).then(({ svg }) => {
      if (ref.current) ref.current.innerHTML = svg
    }).catch(() => {})
  }, [chart])

  if (!chart.trim()) return null
  return <div ref={ref} className="w-full overflow-auto" />
}

// ── Live panel ────────────────────────────────────────────────────────────────

function LivePanel({ currentNode, tools, files, tokens, step, mermaidStr }: {
  currentNode: string; tools: string[]; files: string[]
  tokens: { prompt: number; completion: number; total: number }
  step: number; mermaidStr: string
}) {
  return (
    <div className="grid grid-cols-3 gap-4 mt-4 p-4 bg-gray-900 rounded-lg border border-gray-700">
      <div className="space-y-3">
        <div className="text-sm font-semibold text-gray-400">Agent actif</div>
        <div className="text-lg font-mono">
          {ICONS[currentNode] ?? '🤖'} <span className="text-purple-400">{currentNode}</span>
        </div>
        {tools.length > 0 && (
          <div>
            <div className="text-xs text-gray-500 mb-1">Outils</div>
            {tools.slice(-5).map(t => <div key={t} className="text-xs font-mono text-yellow-400">• {t}</div>)}
          </div>
        )}
        {files.length > 0 && (
          <div>
            <div className="text-xs text-gray-500 mb-1">Fichiers ({files.length})</div>
            {files.map(f => <div key={f} className="text-xs font-mono text-green-400 truncate">• {f}</div>)}
          </div>
        )}
        <div className="text-xs text-gray-400">
          Tokens — in: <span className="text-blue-400">{tokens.prompt.toLocaleString()}</span>{' '}
          out: <span className="text-green-400">{tokens.completion.toLocaleString()}</span>{' '}
          total: <span className="text-white font-bold">{tokens.total.toLocaleString()}</span>
        </div>
        <div className="text-xs text-gray-600">Étape {step}</div>
      </div>
      <div className="col-span-2">
        <div className="text-xs text-gray-500 mb-2">Sequence diagram (live)</div>
        <div className="bg-gray-800 rounded p-2 overflow-auto max-h-80">
          <MermaidDiagram chart={mermaidStr} />
        </div>
      </div>
    </div>
  )
}

// ── Main App ──────────────────────────────────────────────────────────────────

export default function App() {
  const [tab, setTab] = useState<Tab>('chat')
  const [prompt, setPrompt] = useState('')
  const [running, setRunning] = useState(false)
  const [currentNode, setCurrentNode] = useState('')
  const [step, setStep] = useState(0)
  const [liveTools, setLiveTools] = useState<string[]>([])
  const [liveFiles, setLiveFiles] = useState<string[]>([])
  const [liveTokens, setLiveTokens] = useState({ prompt: 0, completion: 0, total: 0 })
  const [liveMermaid, setLiveMermaid] = useState('')
  const [chatMessages, setChatMessages] = useState<Message[]>([])
  const [runState, setRunState] = useState<RunState | null>(null)
  const [threadId] = useState(() => crypto.randomUUID())
  const [filterAgents, setFilterAgents] = useState<string[]>([])
  const [filterKinds, setFilterKinds] = useState<string[]>([])
  const [expandedEvent, setExpandedEvent] = useState<number | null>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)
  const liveTokensRef = useRef(liveTokens)
  liveTokensRef.current = liveTokens

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  const sendPrompt = useCallback(() => {
    if (!prompt.trim() || running) return
    const p = prompt.trim()
    setPrompt('')
    setRunning(true)
    setStep(0)
    setLiveTools([])
    setLiveFiles([])
    setLiveTokens({ prompt: 0, completion: 0, total: 0 })
    setLiveMermaid('')
    setCurrentNode('')
    setRunState(null)
    setChatMessages(prev => [...prev, { role: 'user', content: p }])

    const wsUrl = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`
    const ws = new WebSocket(wsUrl)

    ws.onopen = () => ws.send(JSON.stringify({ prompt: p, thread_id: threadId }))

    ws.onmessage = (evt) => {
      const msg = JSON.parse(evt.data as string)
      console.log('[WS]', msg.type, msg)

      if (msg.type === 'step') {
        setCurrentNode(msg.node)
        setStep(s => s + 1)
        setLiveFiles(msg.files ?? [])
        setLiveMermaid(msg.mermaid ?? '')
        const u = msg.token_usage ?? {}
        setLiveTokens(prev => ({
          prompt:     prev.prompt     + (Number(u.prompt_tokens)     || 0),
          completion: prev.completion + (Number(u.completion_tokens) || 0),
          total:      prev.total      + (Number(u.total_tokens)      || 0),
        }))
        const events: TraceEvent[] = msg.events ?? []
        const toolCalls = events
          .filter(e => e.kind === 'tool_call')
          .map(e => String(e.payload.tool ?? ''))
          .filter(Boolean)
        setLiveTools(toolCalls)
        for (const m of msg.messages ?? []) {
          setChatMessages(prev => [...prev, m as Message])
        }
        // Update trace tabs live with cumulative events from each step
        if (events.length > 0) {
          setRunState(prev => ({
            events,
            mermaid: msg.mermaid ?? '',
            recordJson: prev?.recordJson ?? '',
            messages: prev?.messages ?? [],
            files: msg.files ?? [],
            tokens: liveTokensRef.current,
            exportMsg: prev?.exportMsg ?? '',
          }))
        }
      }

      if (msg.type === 'done') {
        console.log('[WS] done signal — thread:', msg.thread_id, 'events:', msg.event_count, 'export:', msg.export_msg)
        // Fetch full result via HTTP to avoid WebSocket buffer limits
        fetch(`/result/${msg.thread_id}`)
          .then(r => r.json())
          .then(data => {
            console.log('[HTTP] result — events:', data.events?.length, 'mermaid:', data.mermaid?.length, 'record:', data.record_json?.length)
            setRunState({
              events: data.events ?? [],
              mermaid: data.mermaid ?? '',
              recordJson: data.record_json ?? '',
              messages: data.messages ?? [],
              files: data.files ?? [],
              tokens: liveTokensRef.current,
              exportMsg: data.export_msg ?? '',
            })
            setFilterAgents([])
            setFilterKinds([])
          })
          .catch(err => console.error('[HTTP] result fetch failed:', err))
          .finally(() => setRunning(false))
      }

      if (msg.type === 'error') {
        setChatMessages(prev => [...prev, { role: 'assistant', content: `[error] ${msg.message}` }])
        setRunning(false)
      }
    }

    ws.onerror = () => {
      setChatMessages(prev => [...prev, { role: 'assistant', content: '[error] WebSocket connection failed — is the server running on port 8000?' }])
      setRunning(false)
    }
  }, [prompt, running, threadId])

  // ── Derived for log tab ────────────────────────────────────────────────────
  const allEvents = runState?.events ?? []
  const allAgents = [...new Set(allEvents.map(e => e.agent))]
  const allKinds  = [...new Set(allEvents.map(e => e.kind))]
  const activeAgents = filterAgents.length > 0 ? filterAgents : allAgents
  const activeKinds  = filterKinds.length  > 0 ? filterKinds  : allKinds
  const filteredEvents = allEvents.filter(e => activeAgents.includes(e.agent) && activeKinds.includes(e.kind))

  const recordDict = (() => {
    try { return runState?.recordJson ? JSON.parse(runState.recordJson) : null }
    catch { return null }
  })()

  const tabs: { id: Tab; label: string }[] = [
    { id: 'chat',    label: '💬 Chat' },
    { id: 'diagram', label: '📊 Sequence Diagram' },
    { id: 'trace',   label: '🔬 Agent Trace (v1)' },
    { id: 'log',     label: '📋 Event Log' },
  ]

  return (
    <div className="flex h-screen bg-gray-950 text-gray-200">
      {/* Sidebar */}
      <aside className="w-56 shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col p-4 gap-4">
        <div className="font-bold text-lg text-purple-400">Team Agent</div>
        <div className="text-xs text-gray-500">LangGraph · React</div>
        <hr className="border-gray-800" />
        <div className="text-xs text-gray-400">
          <div className="font-semibold mb-1">Session</div>
          <code className="text-purple-300 text-xs">{threadId.slice(0, 8)}…</code>
        </div>
        <div className="text-xs text-gray-400">
          Trace events: <span className="text-white font-bold">{runState?.events.length ?? 0}</span>
        </div>
        {runState?.exportMsg && (
          <div className="text-xs text-green-400 break-all">{runState.exportMsg}</div>
        )}
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Tab bar */}
        <div className="flex border-b border-gray-800 bg-gray-900 shrink-0">
          {tabs.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={`px-5 py-3 text-sm font-medium transition-colors ${
                tab === t.id
                  ? 'border-b-2 border-purple-500 text-purple-400'
                  : 'text-gray-500 hover:text-gray-300'
              }`}>
              {t.label}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-auto">

          {/* ── Chat ── */}
          {tab === 'chat' && (
            <div className="flex flex-col h-full">
              <div className="flex-1 overflow-auto p-4 space-y-3">
                {chatMessages.map((m, i) => (
                  <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-2xl rounded-lg px-4 py-2 text-sm ${
                      m.role === 'user' ? 'bg-purple-700 text-white' : 'bg-gray-800 text-gray-200'
                    }`}>
                      {m.role === 'assistant' && m.node && (
                        <span className="text-xs text-gray-500 block mb-1">{ICONS[m.node] ?? '🤖'} {m.node}</span>
                      )}
                      <div className="md-content">
                        <ReactMarkdown>{m.content}</ReactMarkdown>
                      </div>
                    </div>
                  </div>
                ))}
                <div ref={chatEndRef} />
              </div>

              {running && (
                <div className="px-4">
                  <LivePanel
                    currentNode={currentNode} tools={liveTools} files={liveFiles}
                    tokens={liveTokens} step={step} mermaidStr={liveMermaid}
                  />
                </div>
              )}

              <div className="p-4 border-t border-gray-800 flex gap-2">
                <input
                  className="flex-1 bg-gray-800 rounded-lg px-4 py-2 text-sm text-gray-200 outline-none focus:ring-2 focus:ring-purple-500 disabled:opacity-50"
                  placeholder="Describe the task for the team…"
                  value={prompt}
                  onChange={e => setPrompt(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendPrompt()}
                  disabled={running}
                />
                <button onClick={sendPrompt} disabled={running || !prompt.trim()}
                  className="px-4 py-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-40 rounded-lg text-sm font-medium transition-colors">
                  {running ? '⏳' : 'Envoyer'}
                </button>
              </div>
            </div>
          )}

          {/* ── Sequence Diagram ── */}
          {tab === 'diagram' && (
            <div className="p-6">
              <h2 className="text-xl font-semibold mb-4">Sequence Diagram</h2>
              {!runState ? (
                <p className="text-gray-500">Lancez une tâche dans l'onglet Chat.</p>
              ) : (
                <>
                  <p className="text-sm text-gray-400 mb-4">{runState.events.length} événements</p>
                  <div className="bg-gray-900 rounded-lg p-4 overflow-auto">
                    <MermaidDiagram chart={runState.mermaid} />
                  </div>
                  <details className="mt-4">
                    <summary className="text-sm text-gray-500 cursor-pointer">Source Mermaid</summary>
                    <pre className="mt-2 text-xs bg-gray-900 p-4 rounded overflow-auto text-gray-400">{runState.mermaid}</pre>
                  </details>
                  <a href={`data:text/markdown;charset=utf-8,${encodeURIComponent('```mermaid\n' + runState.mermaid + '\n```')}`}
                    download="sequence_diagram.md"
                    className="mt-4 inline-block text-xs text-purple-400 hover:underline">
                    Télécharger .md
                  </a>
                </>
              )}
            </div>
          )}

          {/* ── Agent Trace v1 ── */}
          {tab === 'trace' && (
            <div className="p-6">
              <h2 className="text-xl font-semibold mb-1">Agent Trace Record — v1</h2>
              <p className="text-xs text-gray-500 mb-4">
                Format: <a href="https://github.com/Velkasi/TracerIA" className="text-purple-400 hover:underline" target="_blank">github.com/Velkasi/TracerIA</a>
              </p>
              {!recordDict ? (
                <p className="text-gray-500">Lancez une tâche dans l'onglet Chat.</p>
              ) : (
                <>
                  <div className="grid grid-cols-4 gap-4 mb-6">
                    {([
                      ['Fichiers', recordDict.files?.length ?? 0],
                      ['Ranges', (recordDict.files ?? []).reduce((acc: number, f: {sessions?: {ranges?: unknown[]}[]}) =>
                        acc + (f.sessions ?? []).reduce((a: number, s) => a + (s.ranges ?? []).length, 0), 0)],
                      ['Tokens', (runState?.tokens.total ?? 0).toLocaleString()],
                      ['Git SHA', (recordDict.git?.revision ?? '—').slice(0, 12)],
                    ] as [string, string|number][]).map(([label, value]) => (
                      <div key={label} className="bg-gray-900 rounded-lg p-4 border border-gray-800">
                        <div className="text-xs text-gray-500">{label}</div>
                        <div className="text-2xl font-bold text-white mt-1">{value}</div>
                      </div>
                    ))}
                  </div>

                  {recordDict.metadata?.token_summary && (
                    <div className="mb-6">
                      <h3 className="text-sm font-semibold text-gray-400 mb-2">Tokens par agent</h3>
                      <table className="w-full text-sm text-left">
                        <thead>
                          <tr className="text-xs text-gray-500 border-b border-gray-800">
                            {['Agent','Modèle','Appels','Prompt','Completion','Total'].map(h =>
                              <th key={h} className="py-2 pr-4">{h}</th>)}
                          </tr>
                        </thead>
                        <tbody>
                          {Object.entries(recordDict.metadata.token_summary).map(([agent, d]) => {
                            const data = d as Record<string, unknown>
                            return (
                              <tr key={agent} className="border-b border-gray-900 hover:bg-gray-900">
                                <td className="py-2 pr-4 font-mono text-purple-400">{agent}</td>
                                <td className="py-2 pr-4 text-gray-400">{String(data.model ?? '?')}</td>
                                <td className="py-2 pr-4">{String(data.calls ?? 0)}</td>
                                <td className="py-2 pr-4">{Number(data.prompt ?? 0).toLocaleString()}</td>
                                <td className="py-2 pr-4">{Number(data.completion ?? 0).toLocaleString()}</td>
                                <td className="py-2 font-bold">{Number(data.total ?? 0).toLocaleString()}</td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}

                  <div className="flex justify-between items-center mb-2">
                    <h3 className="text-sm font-semibold text-gray-400">JSON brut</h3>
                    <a href={`data:application/json;charset=utf-8,${encodeURIComponent(runState?.recordJson ?? '')}`}
                      download="agent_trace.json" className="text-xs text-purple-400 hover:underline">
                      Télécharger trace.json
                    </a>
                  </div>
                  <pre className="text-xs bg-gray-900 p-4 rounded overflow-auto max-h-96 text-gray-400">
                    {JSON.stringify(recordDict, null, 2)}
                  </pre>
                </>
              )}
            </div>
          )}

          {/* ── Event Log ── */}
          {tab === 'log' && (
            <div className="p-6">
              <h2 className="text-xl font-semibold mb-4">Full Event Log</h2>
              {allEvents.length === 0 ? (
                <p className="text-gray-500">Lancez une tâche dans l'onglet Chat.</p>
              ) : (
                <>
                  <div className="flex gap-6 mb-4 flex-wrap">
                    <div>
                      <div className="text-xs text-gray-500 mb-1">Agents</div>
                      <div className="flex gap-2 flex-wrap">
                        {allAgents.map(a => (
                          <button key={a}
                            onClick={() => setFilterAgents(prev => prev.includes(a) ? prev.filter(x => x !== a) : [...prev, a])}
                            className={`text-xs px-2 py-1 rounded border transition-colors ${
                              activeAgents.includes(a) ? 'border-purple-500 text-purple-400 bg-purple-950' : 'border-gray-700 text-gray-600'
                            }`}>
                            {ICONS[a] ?? ''} {a}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-500 mb-1">Types</div>
                      <div className="flex gap-2 flex-wrap">
                        {allKinds.map(k => (
                          <button key={k}
                            onClick={() => setFilterKinds(prev => prev.includes(k) ? prev.filter(x => x !== k) : [...prev, k])}
                            className={`text-xs px-2 py-1 rounded border transition-colors ${
                              activeKinds.includes(k) ? 'border-blue-500 text-blue-400 bg-blue-950' : 'border-gray-700 text-gray-600'
                            }`}>
                            {KIND_ICONS[k] ?? '•'} {k}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                  <p className="text-xs text-gray-500 mb-3">{filteredEvents.length} / {allEvents.length} événements</p>
                  <div className="space-y-0">
                    {filteredEvents.map((ev, i) => {
                      const p = ev.payload
                      let detail = ''
                      if (ev.kind === 'llm_call') {
                        detail = `${p.model} | iter=${p.iteration} | in=${Number(p.prompt_tokens??0).toLocaleString()} out=${Number(p.completion_tokens??0).toLocaleString()} tot=${Number(p.total_tokens??0).toLocaleString()}`
                        if (p.prompt_preview) detail += ` | "${String(p.prompt_preview).slice(0,60)}…"`
                      }
                      else if (ev.kind === 'llm_response') {
                        detail = p.has_tool_calls ? '→ tool calls' : 'text'
                        if (p.response_preview) detail += ` | "${String(p.response_preview).slice(0,80)}…"`
                      }
                      else if (ev.kind === 'tool_call') detail = `${p.tool} — ${p.args_summary ?? ''}`
                      else if (ev.kind === 'tool_result') detail = `${p.tool} → ${String(p.result ?? '').slice(0, 100)}`
                      else if (ev.kind === 'memory_op') {
                        detail = `${p.operation} [${p.layer}]`
                        if (p.query) detail += ` query="${String(p.query).slice(0,60)}"`
                        if (p.results_count) detail += ` → ${p.results_count} docs`
                        if (p.summary && !p.query) detail += ` ${String(p.summary).slice(0,80)}`
                      }
                      else if (ev.kind === 'supervisor_route') detail = `→ ${p.target}`
                      else if (ev.kind === 'agent_done') detail = `${Number(p.duration_ms).toLocaleString()}ms`
                      else if (ev.kind === 'error') detail = String(p.message ?? '')
                      const isExpanded = expandedEvent === i
                      return (
                        <div key={i} className="border-b border-gray-900">
                          <div
                            className="flex gap-3 text-xs font-mono py-1 hover:bg-gray-900 px-2 rounded cursor-pointer"
                            onClick={() => setExpandedEvent(isExpanded ? null : i)}
                          >
                            <span className="text-gray-600 w-8 shrink-0">{String(i+1).padStart(3,'0')}</span>
                            <span className="text-gray-600 w-20 shrink-0">{ev.ts}</span>
                            <span className="w-5 shrink-0">{KIND_ICONS[ev.kind] ?? '•'}</span>
                            <span className="text-purple-400 w-24 shrink-0">{ev.agent}</span>
                            <span className="text-blue-400 w-28 shrink-0">{ev.kind}</span>
                            <span className="text-gray-400 flex-1 truncate">{detail}</span>
                            <span className="text-gray-600 shrink-0">{isExpanded ? '▲' : '▼'}</span>
                          </div>
                          {isExpanded && (
                            <div className="mx-2 mb-2 bg-gray-950 rounded p-3 text-xs font-mono text-gray-300 overflow-auto max-h-96 whitespace-pre-wrap break-all">
                              {JSON.stringify(ev.payload, null, 2)}
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </>
              )}
            </div>
          )}

        </div>
      </div>
    </div>
  )
}
