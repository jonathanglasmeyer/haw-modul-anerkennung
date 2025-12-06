'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import ReactMarkdown from 'react-markdown'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Textarea } from '@/components/ui/textarea'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'

interface Match {
  unit_id: string
  unit_title: string
  module_title: string
  similarity: number
  credits?: number
  sws?: number
  workload?: string
}

interface CompareResult {
  unit_id: string
  unit_title: string
  module_title?: string
  empfehlung: 'vollständig' | 'teilweise' | 'keine'
  lernziele_match: number
  lernziele: { ziel: string; status: string; note: string }[]
  credits: { extern?: number | null; intern?: number | null; bewertung: string }
  niveau: string
  pruefung: string
  workload: string
  defizite: string[]
  fazit: string
  unit_credits?: number
  unit_sws?: number | string
  unit_workload?: string
  unit_content?: string
}

interface ParsedModule {
  title: string
  credits?: number | null
  workload?: string | null
  level?: string | null
  assessment?: string | null
  institution?: string | null
  learning_goals?: string[]
}

type Step = 'input' | 'matches' | 'results'

const SESSION_KEY = 'matching-ui-state'

export default function Home() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const step = (searchParams.get('step') as Step) || 'input'

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [moduleText, setModuleText] = useState('')
  const [parsedModule, setParsedModule] = useState<ParsedModule | null>(null)
  const [matches, setMatches] = useState<Match[]>([])
  const [selectedUnitIds, setSelectedUnitIds] = useState<string[]>([])
  const [compareResults, setCompareResults] = useState<CompareResult[]>([])
  const hasRestored = useRef(false)

  const handleSearch = async () => {
    if (!moduleText.trim()) return
    setLoading(true)
    setError(null)
    try {
      const parseRes = await fetch('/api/parse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: moduleText }),
      })
      const parseData = await parseRes.json()
      if (parseData.error) throw new Error(parseData.error)
      console.log('[Timing] Parse:', parseData.timing)
      setParsedModule(parseData.module)

      const matchRes = await fetch('/api/match', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: moduleText, limit: 10 }),
      })
      const matchData = await matchRes.json()
      if (matchData.error) throw new Error(matchData.error)
      console.log('[Timing] Match:', matchData.timing)

      setMatches(matchData.matches || [])
      setSelectedUnitIds([])
      router.push('/?step=matches', { scroll: false })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler bei der Suche')
    } finally {
      setLoading(false)
    }
  }

  const handleCompare = async () => {
    if (!parsedModule || selectedUnitIds.length === 0) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/compare-multiple', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          external_module: parsedModule,
          unit_ids: selectedUnitIds,
        }),
      })
      const data = await res.json()
      if (data.error) throw new Error(data.error)
      console.log('[Timing] Compare:', data.timing)

      setCompareResults(data.results || [])
      router.push('/?step=results', { scroll: false })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Vergleich')
    } finally {
      setLoading(false)
    }
  }

  const toggleUnit = (unitId: string) => {
    setSelectedUnitIds(prev =>
      prev.includes(unitId)
        ? prev.filter(id => id !== unitId)
        : [...prev, unitId]
    )
  }

  const reset = () => {
    setModuleText('')
    setParsedModule(null)
    setMatches([])
    setSelectedUnitIds([])
    setCompareResults([])
    setError(null)
    router.push('/', { scroll: false })
  }

  const getEmpfehlungVariant = (empfehlung: string): 'default' | 'secondary' | 'destructive' => {
    switch (empfehlung) {
      case 'vollständig': return 'default'
      case 'teilweise': return 'secondary'
      default: return 'destructive'
    }
  }

  const getResultBorderClass = (empfehlung: string) => {
    switch (empfehlung) {
      case 'vollständig': return 'border-l-4 border-l-green-500'
      case 'teilweise': return 'border-l-4 border-l-yellow-500'
      default: return 'border-l-4 border-l-red-500'
    }
  }

  const ProgressBar = ({ value }: { value: number }) => (
    <div className="h-2 rounded-full bg-muted overflow-hidden">
      <div
        className="h-full bg-gradient-to-r from-green-500 via-lime-400 to-emerald-500"
        style={{ width: `${Math.min(Math.max(value, 0), 100)}%` }}
      />
    </div>
  )

  // Restore state from sessionStorage on mount
  useEffect(() => {
    if (hasRestored.current) return
    hasRestored.current = true

    const saved = sessionStorage.getItem(SESSION_KEY)
    if (saved) {
      try {
        const state = JSON.parse(saved)
        setModuleText(state.moduleText || '')
        setParsedModule(state.parsedModule || null)
        setMatches(state.matches || [])
        setSelectedUnitIds(state.selectedUnitIds || [])
        setCompareResults(state.compareResults || [])
      } catch {
        // ignore parse errors
      }
    }
  }, [])

  // Save state to sessionStorage whenever it changes
  useEffect(() => {
    if (!hasRestored.current) return

    sessionStorage.setItem(SESSION_KEY, JSON.stringify({
      moduleText,
      parsedModule,
      matches,
      selectedUnitIds,
      compareResults,
    }))
  }, [moduleText, parsedModule, matches, selectedUnitIds, compareResults])

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="bg-primary text-primary-foreground">
        <div className="max-w-6xl mx-auto px-6 py-4">
          <div className="text-sm opacity-80">HAW Hamburg</div>
          <h1 className="text-2xl font-bold">Modulanerkennung</h1>
        </div>
      </header>

      {/* Breadcrumb */}
      <nav className="bg-card border-b">
        <div className="max-w-6xl mx-auto px-6 py-3 text-sm text-muted-foreground">
          Startseite — <span className="text-foreground">Modulanerkennung</span>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto px-6 py-8">
        <div className="flex gap-8">
          {/* Sidebar */}
          <aside className="w-64 shrink-0">
            <div className="bg-primary text-primary-foreground p-4 font-medium">
              Modulanerkennung
            </div>
            <nav className="bg-card border border-t-0 overflow-hidden">
              <button
                onClick={() => step !== 'input' && router.push('/', { scroll: false })}
                className={`w-full text-left px-4 py-3 border-b hover:bg-muted ${step === 'input' ? 'bg-muted font-medium' : ''}`}
              >
                1. Modul eingeben
              </button>
              <button
                onClick={() => step !== 'matches' && matches.length > 0 && router.push('/?step=matches', { scroll: false })}
                disabled={matches.length === 0}
                className={`w-full text-left px-4 py-3 border-b ${step === 'matches' ? 'bg-muted font-medium' : ''} ${matches.length === 0 ? 'text-muted-foreground cursor-not-allowed' : 'hover:bg-muted cursor-pointer'}`}
              >
                2. Units auswählen
              </button>
              <button
                onClick={() => step !== 'results' && compareResults.length > 0 && router.push('/?step=results', { scroll: false })}
                disabled={compareResults.length === 0}
                className={`w-full text-left px-4 py-3 ${step === 'results' ? 'bg-muted font-medium' : ''} ${compareResults.length === 0 ? 'text-muted-foreground cursor-not-allowed' : 'hover:bg-muted'}`}
              >
                3. Ergebnis
              </button>
            </nav>
          </aside>

          {/* Content */}
          <div className="flex-1">
            {error && (
              <Alert variant="destructive" className="mb-6">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* Step 1: Input */}
            {step === 'input' && (
              <section>
                <h2 className="text-xl font-bold mb-2">Externes Modul eingeben</h2>
                <p className="text-muted-foreground mb-6">
                  Geben Sie die Modulbeschreibung ein, um passende interne Units zu finden.
                </p>
                <Card>
                  <CardContent className="pt-6">
                    <label className="block text-sm font-medium mb-2">
                      Modulbeschreibung
                    </label>
                    <Textarea
                      value={moduleText}
                      onChange={(e) => setModuleText(e.target.value)}
                      placeholder="Titel, Credits, Lernziele des externen Moduls eingeben..."
                      className="h-48 resize-none"
                    />
                    <div className="mt-4 flex justify-end">
                      <Button
                        onClick={handleSearch}
                        disabled={loading || !moduleText.trim()}
                      >
                        {loading ? 'Suche läuft...' : 'Passende Units finden'}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </section>
            )}

            {/* Step 2: Select matches */}
            {step === 'matches' && (
              <section>
                <h2 className="text-xl font-bold mb-2">Passende Units auswählen</h2>
                <p className="text-muted-foreground mb-6">
                  Wählen Sie die Units aus, mit denen das externe Modul verglichen werden soll.
                </p>

                {parsedModule && (
                  <Card className="mb-6 border-l-4 border-l-primary">
                    <CardHeader>
                      <CardTitle className="text-base">Externes Modul</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p><strong>Titel:</strong> {parsedModule.title}</p>
                      {parsedModule.credits !== undefined && parsedModule.credits !== null && (
                        <p><strong>Credits:</strong> {parsedModule.credits}</p>
                      )}
                      {parsedModule.workload && <p><strong>Workload:</strong> {parsedModule.workload}</p>}
                      <p className="mt-2"><strong>Lernziele:</strong></p>
                      <ul className="list-disc list-inside ml-2 text-muted-foreground">
                        {(parsedModule.learning_goals || []).map((goal, i) => (
                          <li key={i}>{goal}</li>
                        ))}
                        {(parsedModule.learning_goals || []).length === 0 && (
                          <li className="italic text-xs text-muted-foreground/80">Keine Lernziele erkannt</li>
                        )}
                      </ul>
                    </CardContent>
                  </Card>
                )}

                <Card>
                  <CardHeader className="bg-muted/50">
                    <CardTitle className="text-base">Vorauswahl: {matches.length} ähnlichste Units</CardTitle>
                    <CardDescription className="mt-1">
                      Basierend auf Textähnlichkeit. Wähle Units für die fachliche Prüfung aus.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-0">
                    <div className="max-h-[50vh] overflow-y-auto divide-y">
                      {matches.map((match) => (
                        <label
                          key={match.unit_id}
                          className={`flex items-start gap-4 p-4 cursor-pointer hover:bg-muted/50 ${
                            selectedUnitIds.includes(match.unit_id) ? 'bg-primary/5' : ''
                          }`}
                        >
                          <Checkbox
                            checked={selectedUnitIds.includes(match.unit_id)}
                            onCheckedChange={() => toggleUnit(match.unit_id)}
                            className="mt-1"
                          />
                          <div className="flex-1">
                            <div className="font-medium">{match.unit_title}</div>
                            <div className="text-sm text-muted-foreground">{match.module_title}</div>
                            <div className="text-xs text-muted-foreground mt-1">
                              ID: {match.unit_id} | Textähnlichkeit: {(match.similarity * 100).toFixed(0)}%
                            </div>
                          </div>
                        </label>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                <div className="mt-6 flex gap-3">
                  <Button variant="outline" onClick={reset}>
                    Zurück
                  </Button>
                  <Button
                    onClick={handleCompare}
                    disabled={loading || selectedUnitIds.length === 0}
                  >
                    {loading ? 'Vergleiche...' : `${selectedUnitIds.length} Units vergleichen`}
                  </Button>
                </div>
              </section>
            )}

            {/* Step 3: Results */}
            {step === 'results' && (
              <section>
                <h2 className="text-xl font-bold mb-2">Vergleichsergebnisse</h2>
                <p className="text-muted-foreground mb-6">
                  Empfehlungen für die Anerkennung der ausgewählten Units.
                </p>

                {parsedModule && (
                  <Card className="mb-6 border border-primary/40">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base">Externes Modul (Referenz)</CardTitle>
                      <CardDescription>{parsedModule.title}</CardDescription>
                    </CardHeader>
                    <CardContent className="grid md:grid-cols-3 gap-3 text-sm">
                      {parsedModule.credits !== undefined && parsedModule.credits !== null && (
                        <div><span className="text-muted-foreground">Credits</span><div className="font-medium">{parsedModule.credits}</div></div>
                      )}
                      {parsedModule.level && (
                        <div><span className="text-muted-foreground">Niveau</span><div className="font-medium">{parsedModule.level}</div></div>
                      )}
                      {parsedModule.assessment && (
                        <div><span className="text-muted-foreground">Prüfung</span><div className="font-medium">{parsedModule.assessment}</div></div>
                      )}
                      {parsedModule.workload && (
                        <div><span className="text-muted-foreground">Workload</span><div className="font-medium">{parsedModule.workload}</div></div>
                      )}
                      {(parsedModule.learning_goals || []).length > 0 && (
                        <div className="md:col-span-3">
                          <span className="text-muted-foreground">Lernziele</span>
                          <ul className="list-disc list-inside ml-2 text-muted-foreground">
                            {parsedModule.learning_goals!.map((g, i) => <li key={i}>{g}</li>)}
                          </ul>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )}

                <div className="space-y-4">
                  {compareResults.map((result) => (
                    <Card key={result.unit_id} className={getResultBorderClass(result.empfehlung)}>
                      <CardHeader>
                        <div className="flex items-center justify-between">
                          <CardTitle className="text-base">{result.unit_title}</CardTitle>
                          <Badge variant={getEmpfehlungVariant(result.empfehlung)}>
                            {result.empfehlung} ({result.lernziele_match}%)
                          </Badge>
                        </div>
                        {result.module_title && (
                          <CardDescription>{result.module_title}</CardDescription>
                        )}
                      </CardHeader>
                      <CardContent>
                        <div className="grid md:grid-cols-3 gap-4 text-sm mb-3">
                          <div>
                            <div className="text-muted-foreground">Lernziele Match</div>
                            <div className="flex items-center gap-2">
                              <span className="font-semibold">{result.lernziele_match}%</span>
                            </div>
                            <ProgressBar value={result.lernziele_match} />
                          </div>
                          {result.unit_credits !== undefined && (
                            <div>
                              <div className="text-muted-foreground">Credits (intern)</div>
                              <div className="font-semibold">{result.unit_credits}</div>
                            </div>
                          )}
                          {result.unit_sws !== undefined && (
                            <div>
                              <div className="text-muted-foreground">SWS</div>
                              <div className="font-semibold">{result.unit_sws}</div>
                            </div>
                          )}
                        {result.unit_workload && (
                          <div>
                            <div className="text-muted-foreground">Workload</div>
                            <div className="font-semibold">{result.unit_workload}</div>
                          </div>
                        )}
                      </div>

                        <div className="space-y-3 text-sm">
                          <div>
                            <div className="font-semibold">Lernziel-Abgleich</div>
                            <ul className="list-disc list-inside text-muted-foreground">
                              {result.lernziele.map((lz, i) => (
                                <li key={i}>
                                  <span className="font-medium">{lz.status} </span>
                                  <span className="font-semibold">{lz.ziel}:</span> {lz.note}
                                </li>
                              ))}
                            </ul>
                          </div>
                          <div>
                            <div className="font-semibold">Credits</div>
                            <p className="text-muted-foreground">
                              Extern: {result.credits.extern ?? 'n/a'} | Intern: {result.credits.intern ?? 'n/a'} — {result.credits.bewertung}
                            </p>
                          </div>
                          {result.niveau && (
                            <div>
                              <div className="font-semibold">Niveau</div>
                              <p className="text-muted-foreground">{result.niveau}</p>
                            </div>
                          )}
                          {result.pruefung && (
                            <div>
                              <div className="font-semibold">Prüfung</div>
                              <p className="text-muted-foreground">{result.pruefung}</p>
                            </div>
                          )}
                          {result.workload && (
                            <div>
                              <div className="font-semibold">Workload</div>
                              <p className="text-muted-foreground">{result.workload}</p>
                            </div>
                          )}
                          {result.defizite.length > 0 && (
                            <div>
                              <div className="font-semibold">Defizite</div>
                              <ul className="list-disc list-inside text-muted-foreground">
                                {result.defizite.map((d, i) => <li key={i}>{d}</li>)}
                              </ul>
                            </div>
                          )}
                          <div>
                            <div className="font-semibold">Fazit</div>
                            <p className="text-muted-foreground">{result.fazit}</p>
                          </div>
                        </div>

                        {result.unit_content && (
                          <div className="mt-4 rounded-md bg-muted/60 p-3 text-sm text-muted-foreground">
                            <div className="font-semibold text-foreground mb-1">Interne Unit (Auszug)</div>
                            <p className="line-clamp-5">{result.unit_content}</p>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>

                <div className="mt-6 flex gap-3">
                  <Button variant="outline" onClick={reset}>
                    Neue Suche
                  </Button>
                  <Button variant="outline" onClick={() => router.push('/?step=matches', { scroll: false })}>
                    Andere Units wählen
                  </Button>
                </div>
              </section>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
