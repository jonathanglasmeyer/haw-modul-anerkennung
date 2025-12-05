'use client'

import { useState } from 'react'
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
}

interface CompareResult {
  unit_id: string
  unit_title: string
  empfehlung: 'vollständig' | 'teilweise' | 'keine'
  lernziele_match: number
  begründung: string
}

interface ParsedModule {
  title: string
  credits: number
  learning_goals: string[]
}

type Step = 'input' | 'matches' | 'results'

export default function Home() {
  const [step, setStep] = useState<Step>('input')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [moduleText, setModuleText] = useState('')
  const [parsedModule, setParsedModule] = useState<ParsedModule | null>(null)
  const [matches, setMatches] = useState<Match[]>([])
  const [selectedUnitIds, setSelectedUnitIds] = useState<string[]>([])
  const [compareResults, setCompareResults] = useState<CompareResult[]>([])

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
      setParsedModule(parseData.module)

      const matchRes = await fetch('/api/match', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: moduleText, limit: 10 }),
      })
      const matchData = await matchRes.json()
      if (matchData.error) throw new Error(matchData.error)

      setMatches(matchData.matches || [])
      setSelectedUnitIds([])
      setStep('matches')
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

      setCompareResults(data.results || [])
      setStep('results')
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
    setStep('input')
    setModuleText('')
    setParsedModule(null)
    setMatches([])
    setSelectedUnitIds([])
    setCompareResults([])
    setError(null)
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
                onClick={() => step !== 'input' && reset()}
                className={`w-full text-left px-4 py-3 border-b hover:bg-muted ${step === 'input' ? 'bg-muted font-medium' : ''}`}
              >
                1. Modul eingeben
              </button>
              <button
                onClick={() => (step === 'results') && setStep('matches')}
                disabled={step === 'input'}
                className={`w-full text-left px-4 py-3 border-b ${step === 'matches' ? 'bg-muted font-medium' : ''} ${step === 'input' ? 'text-muted-foreground cursor-not-allowed' : 'hover:bg-muted cursor-pointer'}`}
              >
                2. Units auswählen
              </button>
              <button
                disabled={step !== 'results'}
                className={`w-full text-left px-4 py-3 ${step === 'results' ? 'bg-muted font-medium' : ''} ${step !== 'results' ? 'text-muted-foreground cursor-not-allowed' : 'hover:bg-muted'}`}
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
                      <p><strong>Credits:</strong> {parsedModule.credits}</p>
                      <p className="mt-2"><strong>Lernziele:</strong></p>
                      <ul className="list-disc list-inside ml-2 text-muted-foreground">
                        {parsedModule.learning_goals.map((goal, i) => (
                          <li key={i}>{goal}</li>
                        ))}
                      </ul>
                    </CardContent>
                  </Card>
                )}

                <Card>
                  <CardHeader className="bg-muted/50">
                    <CardTitle className="text-base">{matches.length} passende Units gefunden</CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    <div className="divide-y">
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
                              ID: {match.unit_id} | Ähnlichkeit: {(match.similarity * 100).toFixed(0)}%
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
                      </CardHeader>
                      <CardContent>
                        <div className="text-sm text-muted-foreground prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-li:my-0">
                          <ReactMarkdown>{result.begründung}</ReactMarkdown>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>

                <div className="mt-6 flex gap-3">
                  <Button variant="outline" onClick={reset}>
                    Neue Suche
                  </Button>
                  <Button variant="outline" onClick={() => setStep('matches')}>
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
