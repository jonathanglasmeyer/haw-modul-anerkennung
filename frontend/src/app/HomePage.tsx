"use client";

import { useEffect, useRef, useState, useMemo, memo, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { ExternalModuleCard } from "@/components/ExternalModuleCard";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { ChevronDown, Check, Copy } from "lucide-react";
import { type Studiengang, STUDIENGAENGE } from "@/lib/studiengang";

interface Match {
  unit_id: string;
  unit_title: string;
  module_title: string;
  similarity: number;
  credits?: number;
  sws?: number;
  workload?: string;
  semester?: string;
  verantwortliche?: string;
  doc: string;
}

interface CompareResult {
  unit_id: string;
  unit_title: string;
  module_title?: string;
  empfehlung: "vollständig" | "teilweise" | "keine";
  lernziele_match: number;
  lernziele: { ziel: string; status: string; note: string }[];
  credits: {
    extern?: number | null;
    intern?: number | null;
    bewertung: string;
  };
  niveau: string;
  pruefung: string;
  workload: string;
  defizite: string[];
  fazit: string;
  unit_credits?: number;
  unit_sws?: number | string;
  unit_workload?: string;
  unit_content?: string;
  verantwortliche?: string;
}

interface ParsedModule {
  title: string;
  credits?: number | null;
  workload?: string | null;
  level?: string | null;
  assessment?: string | null;
  institution?: string | null;
  learning_goals?: string[];
}

type Step = "input" | "matches" | "results";

const SESSION_KEY = "matching-ui-state";

// Pre-process match content outside render
function cleanMatchDoc(doc: string): string {
  return doc.split(/\n(?=Lernziele:)/)[1] || doc;
}

// Memoized MatchItem component
const MatchItem = memo(({
  match,
  isSelected,
  onToggle
}: {
  match: Match;
  isSelected: boolean;
  onToggle: () => void;
}) => {
  const cleanedContent = useMemo(() => cleanMatchDoc(match.doc), [match.doc]);
  const [isOpen, setIsOpen] = useState(false);

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className="group">
      <div className={isSelected ? "bg-primary/5" : ""}>
        {/* Checkbox + Basic Info */}
        <div className="flex items-stretch hover:bg-muted/50 relative">
          <label className="cursor-pointer flex flex-col items-center w-12 py-4 hover:bg-muted/30 rounded-l">
            <Checkbox
              checked={isSelected}
              onCheckedChange={onToggle}
              className="mt-1"
            />
          </label>
          <CollapsibleTrigger className="flex-1 pl-2 pr-4 py-4 text-left cursor-pointer">
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1">
                <div className="font-medium flex items-center gap-2">
                  {match.unit_title}
                  <ChevronDown className="h-4 w-4 shrink-0 transition-transform duration-200 group-data-[state=open]:rotate-180" />
                </div>
                <div className="text-sm text-muted-foreground">
                  {match.module_title}
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  ID: {match.unit_id} | Textähnlichkeit:{" "}
                  {(match.similarity * 100).toFixed(0)}%
                </div>
              </div>
            </div>
          </CollapsibleTrigger>
        </div>

        {/* Collapsible Details - only render when open */}
        <CollapsibleContent className="px-4 pb-4">
          <div className="ml-8 space-y-2 text-sm">
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
              {match.credits && (
                <div className="text-left">
                  <span className="text-muted-foreground">Credits:</span>{" "}
                  <span className="font-medium">{match.credits}</span>
                </div>
              )}
              {match.sws && (
                <div className="text-left">
                  <span className="text-muted-foreground">SWS:</span>{" "}
                  <span className="font-medium">{match.sws}</span>
                </div>
              )}
              {match.workload && (
                <div className="text-left">
                  <span className="text-muted-foreground">Workload:</span>{" "}
                  <span className="font-medium">{match.workload}</span>
                </div>
              )}
              {match.semester && (
                <div className="text-left">
                  <span className="text-muted-foreground">Semester:</span>{" "}
                  <span className="font-medium">{match.semester}</span>
                </div>
              )}
              {match.verantwortliche && (
                <div className="text-left col-span-2">
                  <span className="text-muted-foreground">Verantwortliche:</span>{" "}
                  <span className="font-medium">{match.verantwortliche}</span>
                </div>
              )}
            </div>
            {isOpen && cleanedContent && (
              <div className="pt-2 border-t text-left">
                <div className="text-xs leading-relaxed text-muted-foreground [&_h1]:text-xs [&_h1]:font-semibold [&_h1]:mb-1 [&_h2]:text-xs [&_h2]:font-semibold [&_h2]:mb-1 [&_h3]:text-xs [&_h3]:font-semibold [&_h3]:mb-1 [&_ul]:list-disc [&_ul]:ml-4 [&_li]:mb-0.5">
                  <ReactMarkdown>{cleanedContent}</ReactMarkdown>
                </div>
              </div>
            )}
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  );
});

MatchItem.displayName = 'MatchItem';

export default function Home() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const step = (searchParams.get("step") as Step) || "input";

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [moduleText, setModuleText] = useState("");
  const [studiengang, setStudiengang] = useState<Studiengang | null>(null);
  const [parsedModule, setParsedModule] = useState<ParsedModule | null>(null);
  const [matches, setMatches] = useState<Match[]>([]);
  const [selectedUnitIds, setSelectedUnitIds] = useState<string[]>([]);
  const [compareResults, setCompareResults] = useState<CompareResult[]>([]);
  const [compareProgress, setCompareProgress] = useState(0);
  const [emailCopied, setEmailCopied] = useState(false);
  const hasRestored = useRef(false);

  // Clear matches when studiengang changes
  const handleStudiengangChange = (newStudiengang: Studiengang) => {
    setStudiengang(newStudiengang);
    // Clear matches and results from previous studiengang
    setMatches([]);
    setSelectedUnitIds([]);
    setCompareResults([]);
    // Go back to step 1 if user was on other steps
    if (step !== "input") {
      router.push("/", { scroll: false });
    }
  };

  const handleSearch = async () => {
    if (!moduleText.trim() || !studiengang) return;
    setLoading(true);
    setError(null);
    // Clear old results
    setMatches([]);
    setSelectedUnitIds([]);
    setCompareResults([]);

    try {
      const parseRes = await fetch("/api/parse", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: moduleText }),
      });
      const parseData = await parseRes.json();
      if (parseData.error) throw new Error(parseData.error);
      console.log("[Timing] Parse:", parseData.timing);
      setParsedModule(parseData.module);

      const matchRes = await fetch("/api/match", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: moduleText, limit: 10, studiengang }),
      });
      const matchData = await matchRes.json();
      if (matchData.error) throw new Error(matchData.error);
      console.log("[Timing] Match:", matchData.timing);

      setMatches(matchData.matches || []);
      router.push("/?step=matches", { scroll: false });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler bei der Suche");
    } finally {
      setLoading(false);
    }
  };

  const handleCompare = async () => {
    if (!parsedModule || selectedUnitIds.length === 0 || !studiengang) return;
    setLoading(true);
    setError(null);
    setCompareProgress(0);

    // Animate progress over estimated 8 seconds
    const estimatedTime = 8000; // ms
    const intervalTime = 50; // update every 50ms
    const increment = (100 / estimatedTime) * intervalTime;

    const progressInterval = setInterval(() => {
      setCompareProgress((prev) => {
        const next = prev + increment;
        return next >= 95 ? 95 : next; // Cap at 95%, finish on actual completion
      });
    }, intervalTime);

    try {
      const res = await fetch("/api/compare-multiple", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          external_module: parsedModule,
          unit_ids: selectedUnitIds,
          studiengang,
        }),
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      console.log("[Timing] Compare:", data.timing);

      clearInterval(progressInterval);
      setCompareProgress(100);

      setCompareResults(data.results || []);

      // Small delay to show 100% before transitioning
      setTimeout(() => {
        router.push("/?step=results", { scroll: false });
        setCompareProgress(0);
      }, 300);
    } catch (err) {
      clearInterval(progressInterval);
      setCompareProgress(0);
      setError(err instanceof Error ? err.message : "Fehler beim Vergleich");
    } finally {
      setLoading(false);
    }
  };

  const toggleUnit = useCallback((unitId: string) => {
    setSelectedUnitIds((prev) =>
      prev.includes(unitId)
        ? prev.filter((id) => id !== unitId)
        : [...prev, unitId],
    );
  }, []);

  const reset = () => {
    setModuleText("");
    setStudiengang(null);
    setParsedModule(null);
    setMatches([]);
    setSelectedUnitIds([]);
    setCompareResults([]);
    setError(null);
    router.push("/", { scroll: false });
  };

  const exportToPDF = async (download = false) => {
    if (!parsedModule) return;

    try {
      const response = await fetch('/api/export-pdf', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          external_module: parsedModule,
          results: compareResults,
        }),
      });

      if (!response.ok) {
        throw new Error('PDF export failed');
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);

      // Generate descriptive filename
      const units = compareResults.map(r => r.unit_id).join('-');
      const filename = `Anerkennung_${parsedModule.title.replace(/[^a-zA-Z0-9äöüÄÖÜß]/g, '_')}_${units}.pdf`;

      if (download) {
        // Download PDF
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        return blob;
      } else {
        // Open in new tab (no download attribute)
        window.open(url, '_blank');
        // Don't revoke URL immediately
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      }
    } catch (err) {
      console.error('PDF export error:', err);
      setError('PDF-Export fehlgeschlagen');
    }
  };

  // Generate email content
  const emailContent = useMemo(() => {
    if (!parsedModule || compareResults.length === 0) return null;

    // Collect all responsible persons
    const verantwortliche = compareResults
      .map(r => r.verantwortliche)
      .filter(Boolean)
      .join(', ');

    // Create subject
    const subject = `Anerkennung - ${parsedModule.title} - ${verantwortliche}`;

    // Create email body
    const units = compareResults.map((r, idx) =>
      `${idx + 1}. ${r.unit_title}\n   Verantwortliche: ${r.verantwortliche || 'N/A'}\n   Empfehlung: ${r.empfehlung}`
    ).join('\n\n');

    const body = `Sehr geehrte Damen und Herren,

anbei finden Sie meinen Antrag auf Anerkennung für folgende Units:

${units}

Details siehe beigefügtes PDF.

Mit freundlichen Grüßen`;

    return { subject, body, to: 'pruefungsbuero@haw-hamburg.de' };
  }, [parsedModule, compareResults]);

  const copyEmailToClipboard = async () => {
    if (!emailContent) return;

    const text = `An: ${emailContent.to}
Betreff: ${emailContent.subject}

${emailContent.body}`;

    await navigator.clipboard.writeText(text);
    setEmailCopied(true);
    setTimeout(() => setEmailCopied(false), 2000);
  };

  const getEmpfehlungVariant = (
    empfehlung: string,
  ): "default" | "secondary" | "destructive" => {
    switch (empfehlung) {
      case "vollständig":
        return "default";
      case "teilweise":
        return "secondary";
      default:
        return "destructive";
    }
  };

  const getResultBorderClass = (empfehlung: string) => {
    switch (empfehlung) {
      case "vollständig":
        return "border-l-4 border-l-green-500";
      case "teilweise":
        return "border-l-4 border-l-yellow-500";
      default:
        return "border-l-4 border-l-red-500";
    }
  };


  // Restore state from sessionStorage on mount
  useEffect(() => {
    if (hasRestored.current) return;
    hasRestored.current = true;

    const saved = sessionStorage.getItem(SESSION_KEY);
    if (saved) {
      try {
        const state = JSON.parse(saved);
        setModuleText(state.moduleText || "");
        setStudiengang(state.studiengang || null);
        setParsedModule(state.parsedModule || null);
        setMatches(state.matches || []);
        setSelectedUnitIds(state.selectedUnitIds || []);
        setCompareResults(state.compareResults || []);
      } catch {
        // ignore parse errors
      }
    }
  }, []);

  // Save state to sessionStorage whenever it changes
  useEffect(() => {
    if (!hasRestored.current) return;

    sessionStorage.setItem(
      SESSION_KEY,
      JSON.stringify({
        moduleText,
        studiengang,
        parsedModule,
        matches,
        selectedUnitIds,
        compareResults,
      }),
    );
  }, [moduleText, studiengang, parsedModule, matches, selectedUnitIds, compareResults]);

  return (
    <div className="min-h-screen bg-background pt-32">
      {/* Header - Fixed */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-primary text-primary-foreground border-b border-primary-foreground/10">
        <div className="max-w-7xl mx-auto px-6 py-5">
          <div className="flex items-center">
            <button onClick={() => router.push("/", { scroll: false })} className="hover:opacity-80 transition-opacity mr-[32px]">
              <img src="/haw-logo.svg" alt="HAW Hamburg" className="h-7" />
            </button>
            <div className="text-lg font-bold">Modulanerkennung</div>
            <div className="px-2.5 py-1 bg-primary-foreground/15 text-primary-foreground text-xs font-medium rounded-sm border border-primary-foreground/20 ml-3">
              BETA
            </div>
          </div>
        </div>
      </header>

      {/* Progress Stepper - Fixed */}
      <div className="fixed top-16 left-0 right-0 z-40 border-b bg-background">
        <div className="max-w-7xl mx-auto px-6 pt-3.5 pb-2.5">
          <div className="flex items-center gap-1">
            {/* Step 1 */}
            <button
              onClick={() =>
                step !== "input" && router.push("/", { scroll: false })
              }
              className={`flex items-center gap-2.5 px-3 py-1.5 rounded-md transition-colors ${
                step === "input"
                  ? "text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <span
                className={`flex items-center justify-center w-7 h-7 rounded-full text-sm font-semibold transition-all ${
                  step === "input"
                    ? "bg-primary text-primary-foreground"
                    : "border-2 border-muted-foreground hover:border-foreground"
                }`}
              >
                1
              </span>
              <span className="text-sm">Modul eingeben</span>
            </button>

            <div className="mx-2 text-muted-foreground text-sm">→</div>

            {/* Step 2 */}
            <button
              onClick={() =>
                step !== "matches" &&
                matches.length > 0 &&
                router.push("/?step=matches", { scroll: false })
              }
              disabled={matches.length === 0}
              className={`flex items-center gap-2.5 px-3 py-1.5 rounded-md transition-colors ${
                step === "matches"
                  ? "text-foreground"
                  : matches.length === 0
                    ? "text-muted-foreground/40 cursor-not-allowed"
                    : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <span
                className={`flex items-center justify-center w-7 h-7 rounded-full text-sm font-semibold transition-all ${
                  step === "matches"
                    ? "bg-primary text-primary-foreground"
                    : matches.length === 0
                      ? "border-2 border-muted-foreground/40"
                      : "border-2 border-muted-foreground hover:border-foreground"
                }`}
              >
                2
              </span>
              <span className="text-sm">Units auswählen</span>
            </button>

            <div className="mx-2 text-muted-foreground text-sm">→</div>

            {/* Step 3 */}
            <button
              onClick={() =>
                step !== "results" &&
                compareResults.length > 0 &&
                router.push("/?step=results", { scroll: false })
              }
              disabled={compareResults.length === 0}
              className={`flex items-center gap-2.5 px-3 py-1.5 rounded-md transition-colors ${
                step === "results"
                  ? "text-foreground"
                  : compareResults.length === 0
                    ? "text-muted-foreground/40 cursor-not-allowed"
                    : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <span
                className={`flex items-center justify-center w-7 h-7 rounded-full text-sm font-semibold transition-all ${
                  step === "results"
                    ? "bg-primary text-primary-foreground"
                    : compareResults.length === 0
                      ? "border-2 border-muted-foreground/40"
                      : "border-2 border-muted-foreground hover:border-foreground"
                }`}
              >
                3
              </span>
              <span className="text-sm">Ergebnis</span>
            </button>
          </div>
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Step 1: Input */}
        {step === "input" && (
          <section className="max-w-4xl">
            <h2 className="text-xl font-bold mb-4">So funktioniert die Modulanerkennung</h2>
            <ol className="space-y-2 mb-3 list-decimal list-inside">
              <li>Geben Sie die Modulbeschreibung Ihrer externen Studienleistung ein.</li>
              <li>Das System schlägt mithilfe intelligenter Textanalyse passende HAW-Units vor. Wählen Sie die relevanten aus.</li>
              <li>Das System erstellt eine detaillierte KI-Analyse, die Sie als PDF exportieren oder per E-Mail versenden können.</li>
            </ol>

            <p className="text-sm mb-6">
              Es besteht kein Rechtsanspruch auf Anerkennung in der von der KI geprüften Form. Bitte geben Sie keine persönlichen Daten ein.
            </p>

            <div className="space-y-5">
              <div>
                <h3 className="text-lg font-semibold mb-3">
                  Studiengang
                </h3>
                <div className="flex gap-2">
                  {(Object.keys(STUDIENGAENGE) as Studiengang[]).map(key => (
                    <button
                      key={key}
                      onClick={() => handleStudiengangChange(key)}
                      className={`px-4 py-2 text-sm font-medium rounded-md transition-all ${
                        studiengang === key
                          ? 'bg-primary text-primary-foreground shadow-sm'
                          : 'border border-border bg-background text-muted-foreground hover:bg-muted hover:text-foreground'
                      }`}
                    >
                      {STUDIENGAENGE[key]}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <h3 className="text-lg font-semibold mb-3">
                  Externes Modul
                </h3>
                <Textarea
                  value={moduleText}
                  onChange={(e) => setModuleText(e.target.value)}
                  placeholder="Titel, Credits, Lernziele des externen Moduls eingeben..."
                  className="min-h-64 resize-none"
                />
              </div>
              <div className="flex justify-end">
                <Button
                  onClick={handleSearch}
                  disabled={loading || !moduleText.trim() || !studiengang}
                >
                  {loading ? "Suche läuft..." : "Passende Units finden"}
                </Button>
              </div>
            </div>
          </section>
        )}

        {/* Step 2: Select matches - 3 Column Layout */}
        {step === "matches" && (
          <section>
            <h2 className="text-xl font-bold mb-2">Units auswählen</h2>
            <p className="text-muted-foreground mb-6">
              Wählen Sie die Units aus, die Sie mit dem externen Modul vergleichen möchten.
            </p>

            <div className="grid grid-cols-12 gap-6 items-start">
              {/* Left Column: External Module (Sticky) */}
              <div className="col-span-4">
                {parsedModule && <ExternalModuleCard module={parsedModule} sticky />}
              </div>

              {/* Right Column: Unit List */}
              <div className="col-span-8">
                <Card>
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div>
                        <CardTitle className="text-base">
                          Vorauswahl: {matches.length} ähnlichste Units{studiengang && ` aus ${STUDIENGAENGE[studiengang]}`}
                        </CardTitle>
                        <CardDescription className="mt-1">
                          Basierend auf Textähnlichkeit. Wählen Sie Units für die KI-Analyse aus.
                        </CardDescription>
                      </div>
                      <Button
                        onClick={handleCompare}
                        disabled={loading || selectedUnitIds.length === 0}
                        className="ml-4 relative overflow-hidden"
                      >
                        {/* Progress Bar Background */}
                        {loading && (
                          <div
                            className="absolute inset-0 bg-primary-foreground/20 transition-all duration-100"
                            style={{ width: `${compareProgress}%` }}
                          />
                        )}
                        <span className="relative z-10">
                          {loading
                            ? "Vergleiche..."
                            : selectedUnitIds.length === 0
                              ? "Units vergleichen"
                              : `${selectedUnitIds.length} Units vergleichen`}
                        </span>
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent className="p-0">
                    <div className="max-h-[70vh] overflow-y-auto divide-y">
                      {matches.map((match) => (
                        <MatchItem
                          key={match.unit_id}
                          match={match}
                          isSelected={selectedUnitIds.includes(match.unit_id)}
                          onToggle={() => toggleUnit(match.unit_id)}
                        />
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </section>
        )}

        {/* Step 3: Results - 3 Column Layout */}
        {step === "results" && (
          <section>
            <div className="flex items-center gap-3 mb-2">
              <h2 className="text-xl font-bold">Vergleichsergebnisse</h2>
              {studiengang && (
                <Badge variant="outline" className="text-xs">
                  {STUDIENGAENGE[studiengang]}
                </Badge>
              )}
            </div>
            <p className="text-muted-foreground mb-6">
              Empfehlungen für die Anerkennung der ausgewählten Units.
            </p>

            <div className="grid grid-cols-12 gap-6 items-start">
              {/* Left Column: External Module (Sticky) */}
              <div className="col-span-4">
                {parsedModule && <ExternalModuleCard module={parsedModule} sticky />}
              </div>

              {/* Right Column: Results */}
              <div className="col-span-8">
                <div className="space-y-4">
              {compareResults.map((result) => (
                <Card
                  key={result.unit_id}
                  className={getResultBorderClass(result.empfehlung)}
                >
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle className="text-base">
                          {result.unit_title}
                        </CardTitle>
                        {result.module_title && (
                          <CardDescription>{result.module_title}</CardDescription>
                        )}
                      </div>
                      <div className="shrink-0 self-start">
                        <Badge
                          variant={getEmpfehlungVariant(result.empfehlung)}
                          className={result.empfehlung === "vollständig" ? "bg-green-600 hover:bg-green-700" : ""}
                        >
                          {result.empfehlung === "vollständig" && "Vollständige Anerkennung"}
                          {result.empfehlung === "teilweise" && "Teilweise Anerkennung"}
                          {result.empfehlung === "keine" && "Keine Anerkennung"}
                        </Badge>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="grid md:grid-cols-3 gap-4 text-sm mb-3">
                      <div>
                        <div className="text-muted-foreground">
                          Lernziele Match
                        </div>
                        <div className="font-semibold">
                          {result.lernziele_match}%
                        </div>
                      </div>
                      {result.unit_credits !== undefined && (
                        <div>
                          <div className="text-muted-foreground">
                            Credits (intern)
                          </div>
                          <div className="font-semibold">
                            {result.unit_credits}
                          </div>
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
                          <div className="font-semibold">
                            {result.unit_workload}
                          </div>
                        </div>
                      )}
                      {result.verantwortliche && (
                        <div>
                          <div className="text-muted-foreground">Verantwortliche</div>
                          <div className="font-semibold">
                            {result.verantwortliche}
                          </div>
                        </div>
                      )}
                    </div>

                    <div className="space-y-3 text-sm">
                      <div>
                        <div className="font-semibold mb-2">Lernziel-Abgleich</div>
                        <div className="space-y-1.5 text-muted-foreground">
                          {result.lernziele.map((lz, i) => (
                            <div key={i}>
                              <span className="font-medium">{lz.status}</span>{" "}
                              <span className="font-semibold text-foreground">
                                {lz.ziel}:
                              </span>{" "}
                              {lz.note}
                            </div>
                          ))}
                        </div>
                      </div>
                      <div>
                        <div className="font-semibold">Credits</div>
                        <p className="text-muted-foreground">
                          Extern: {result.credits.extern ?? "n/a"} | Intern:{" "}
                          {result.credits.intern ?? "n/a"} —{" "}
                          {result.credits.bewertung}
                        </p>
                      </div>
                      {result.niveau && (
                        <div>
                          <div className="font-semibold">Niveau</div>
                          <p className="text-muted-foreground">
                            {result.niveau}
                          </p>
                        </div>
                      )}
                      {result.pruefung && (
                        <div>
                          <div className="font-semibold">Prüfung</div>
                          <p className="text-muted-foreground">
                            {result.pruefung}
                          </p>
                        </div>
                      )}
                      {result.workload && (
                        <div>
                          <div className="font-semibold">Workload</div>
                          <p className="text-muted-foreground">
                            {result.workload}
                          </p>
                        </div>
                      )}
                      {result.defizite.length > 0 && (
                        <div>
                          <div className="font-semibold">Defizite</div>
                          <ul className="list-disc list-inside text-muted-foreground">
                            {result.defizite.map((d, i) => (
                              <li key={i}>{d}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      <div>
                        <div className="font-semibold">Fazit</div>
                        <p className="text-muted-foreground">{result.fazit}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
                </div>

                <div className="mt-6 space-y-3">
                  <div className="text-sm text-muted-foreground">
                    <strong>Nächste Schritte:</strong> 1. Email-Inhalt kopieren · 2. PDF herunterladen · 3. In deinem Email-Client einfügen und PDF anhängen
                  </div>
                  <div className="flex gap-3">
                    <Button onClick={copyEmailToClipboard} disabled={emailCopied} className="w-52">
                      {emailCopied ? (
                        <>
                          <Check className="mr-2 h-4 w-4" />
                          Kopiert!
                        </>
                      ) : (
                        <>
                          <Copy className="mr-2 h-4 w-4" />
                          Email-Inhalt kopieren
                        </>
                      )}
                    </Button>
                    <Button variant="outline" onClick={() => exportToPDF(true)}>
                      PDF herunterladen
                    </Button>
                    <Button variant="outline" onClick={reset}>
                      Neue Suche
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => router.push("/?step=matches", { scroll: false })}
                    >
                      Andere Units wählen
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
