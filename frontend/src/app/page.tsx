"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import { Button } from "@/components/ui/button";
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

interface Match {
  unit_id: string;
  unit_title: string;
  module_title: string;
  similarity: number;
  credits?: number;
  sws?: number;
  workload?: string;
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

export default function Home() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const step = (searchParams.get("step") as Step) || "input";

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [moduleText, setModuleText] = useState("");
  const [parsedModule, setParsedModule] = useState<ParsedModule | null>(null);
  const [matches, setMatches] = useState<Match[]>([]);
  const [selectedUnitIds, setSelectedUnitIds] = useState<string[]>([]);
  const [compareResults, setCompareResults] = useState<CompareResult[]>([]);
  const hasRestored = useRef(false);

  const handleSearch = async () => {
    if (!moduleText.trim()) return;
    setLoading(true);
    setError(null);
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
        body: JSON.stringify({ text: moduleText, limit: 10 }),
      });
      const matchData = await matchRes.json();
      if (matchData.error) throw new Error(matchData.error);
      console.log("[Timing] Match:", matchData.timing);

      setMatches(matchData.matches || []);
      setSelectedUnitIds([]);
      router.push("/?step=matches", { scroll: false });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler bei der Suche");
    } finally {
      setLoading(false);
    }
  };

  const handleCompare = async () => {
    if (!parsedModule || selectedUnitIds.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/compare-multiple", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          external_module: parsedModule,
          unit_ids: selectedUnitIds,
        }),
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      console.log("[Timing] Compare:", data.timing);

      setCompareResults(data.results || []);
      router.push("/?step=results", { scroll: false });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler beim Vergleich");
    } finally {
      setLoading(false);
    }
  };

  const toggleUnit = (unitId: string) => {
    setSelectedUnitIds((prev) =>
      prev.includes(unitId)
        ? prev.filter((id) => id !== unitId)
        : [...prev, unitId],
    );
  };

  const reset = () => {
    setModuleText("");
    setParsedModule(null);
    setMatches([]);
    setSelectedUnitIds([]);
    setCompareResults([]);
    setError(null);
    router.push("/", { scroll: false });
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

  const ProgressBar = ({ value }: { value: number }) => (
    <div className="h-2 rounded-full bg-muted overflow-hidden">
      <div
        className="h-full bg-gradient-to-r from-green-500 via-lime-400 to-emerald-500"
        style={{ width: `${Math.min(Math.max(value, 0), 100)}%` }}
      />
    </div>
  );

  // Restore state from sessionStorage on mount
  useEffect(() => {
    if (hasRestored.current) return;
    hasRestored.current = true;

    const saved = sessionStorage.getItem(SESSION_KEY);
    if (saved) {
      try {
        const state = JSON.parse(saved);
        setModuleText(state.moduleText || "");
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
        parsedModule,
        matches,
        selectedUnitIds,
        compareResults,
      }),
    );
  }, [moduleText, parsedModule, matches, selectedUnitIds, compareResults]);

  return (
    <div className="min-h-screen bg-background pt-32">
      {/* Header - Fixed */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-primary text-primary-foreground border-b border-primary-foreground/10">
        <div className="max-w-7xl mx-auto px-6 py-5">
          <div className="flex items-center gap-3">
            <img src="/haw-logo.svg" alt="HAW Hamburg" className="h-7" />
            <div className="text-lg font-bold">Modulanerkennung</div>
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
            <h2 className="text-xl font-bold mb-2">Externes Modul eingeben</h2>
            <p className="text-muted-foreground mb-6">
              Geben Sie die Modulbeschreibung ein, um passende interne Units zu
              finden.
            </p>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">
                  Modulbeschreibung
                </label>
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
                  disabled={loading || !moduleText.trim()}
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
                {parsedModule && (
                  <div className="sticky top-36">
                    <Card className="border-l-4 border-l-primary">
                      <CardHeader>
                        <CardTitle className="text-base">Externes Modul</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-3 text-sm">
                        <div>
                          <div className="text-muted-foreground">Titel</div>
                          <div className="font-medium">{parsedModule.title}</div>
                        </div>
                        {parsedModule.credits !== undefined &&
                          parsedModule.credits !== null && (
                            <div>
                              <div className="text-muted-foreground">Credits</div>
                              <div className="font-medium">{parsedModule.credits}</div>
                            </div>
                          )}
                        {parsedModule.workload && (
                          <div>
                            <div className="text-muted-foreground">Workload</div>
                            <div className="font-medium">{parsedModule.workload}</div>
                          </div>
                        )}
                        {(parsedModule.learning_goals || []).length > 0 && (
                          <div>
                            <div className="text-muted-foreground mb-1">Lernziele</div>
                            <ul className="list-disc list-inside text-muted-foreground space-y-1">
                              {parsedModule.learning_goals!.map((goal, i) => (
                                <li key={i} className="text-xs">{goal}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  </div>
                )}
              </div>

              {/* Right Column: Unit List */}
              <div className="col-span-8">
                <Card>
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div>
                        <CardTitle className="text-base">
                          Vorauswahl: {matches.length} ähnlichste Units
                        </CardTitle>
                        <CardDescription className="mt-1">
                          Basierend auf Textähnlichkeit. Wähle Units für die fachliche Prüfung aus.
                        </CardDescription>
                      </div>
                      <Button
                        onClick={handleCompare}
                        disabled={loading || selectedUnitIds.length === 0}
                        className="ml-4"
                      >
                        {loading
                          ? "Vergleiche..."
                          : selectedUnitIds.length === 0
                            ? "Units vergleichen"
                            : `${selectedUnitIds.length} Units vergleichen`}
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent className="p-0">
                    <div className="max-h-[70vh] overflow-y-auto divide-y">
                      {matches.map((match) => (
                        <label
                          key={match.unit_id}
                          className={`flex items-start gap-4 p-4 cursor-pointer hover:bg-muted/50 transition-colors ${
                            selectedUnitIds.includes(match.unit_id)
                              ? "bg-primary/5"
                              : ""
                          }`}
                        >
                          <Checkbox
                            checked={selectedUnitIds.includes(match.unit_id)}
                            onCheckedChange={() => toggleUnit(match.unit_id)}
                            className="mt-1"
                          />
                          <div className="flex-1">
                            <div className="font-medium">{match.unit_title}</div>
                            <div className="text-sm text-muted-foreground">
                              {match.module_title}
                            </div>
                            <div className="text-xs text-muted-foreground mt-1">
                              ID: {match.unit_id} | Textähnlichkeit:{" "}
                              {(match.similarity * 100).toFixed(0)}%
                            </div>
                          </div>
                        </label>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </section>
        )}

        {/* Step 3: Results */}
        {step === "results" && (
          <section>
            <h2 className="text-xl font-bold mb-2">Vergleichsergebnisse</h2>
            <p className="text-muted-foreground mb-6">
              Empfehlungen für die Anerkennung der ausgewählten Units.
            </p>

            {parsedModule && (
              <Card className="mb-6 border border-primary/40">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">
                    Externes Modul (Referenz)
                  </CardTitle>
                  <CardDescription>{parsedModule.title}</CardDescription>
                </CardHeader>
                <CardContent className="grid md:grid-cols-3 gap-3 text-sm">
                  {parsedModule.credits !== undefined &&
                    parsedModule.credits !== null && (
                      <div>
                        <span className="text-muted-foreground">Credits</span>
                        <div className="font-medium">
                          {parsedModule.credits}
                        </div>
                      </div>
                    )}
                  {parsedModule.level && (
                    <div>
                      <span className="text-muted-foreground">Niveau</span>
                      <div className="font-medium">{parsedModule.level}</div>
                    </div>
                  )}
                  {parsedModule.assessment && (
                    <div>
                      <span className="text-muted-foreground">Prüfung</span>
                      <div className="font-medium">
                        {parsedModule.assessment}
                      </div>
                    </div>
                  )}
                  {parsedModule.workload && (
                    <div>
                      <span className="text-muted-foreground">Workload</span>
                      <div className="font-medium">{parsedModule.workload}</div>
                    </div>
                  )}
                  {(parsedModule.learning_goals || []).length > 0 && (
                    <div className="md:col-span-3">
                      <span className="text-muted-foreground">Lernziele</span>
                      <ul className="list-disc list-inside ml-2 text-muted-foreground">
                        {parsedModule.learning_goals!.map((g, i) => (
                          <li key={i}>{g}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            <div className="space-y-4">
              {compareResults.map((result) => (
                <Card
                  key={result.unit_id}
                  className={getResultBorderClass(result.empfehlung)}
                >
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base">
                        {result.unit_title}
                      </CardTitle>
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
                        <div className="text-muted-foreground">
                          Lernziele Match
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold">
                            {result.lernziele_match}%
                          </span>
                        </div>
                        <ProgressBar value={result.lernziele_match} />
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
                    </div>

                    <div className="space-y-3 text-sm">
                      <div>
                        <div className="font-semibold">Lernziel-Abgleich</div>
                        <ul className="list-disc list-inside text-muted-foreground">
                          {result.lernziele.map((lz, i) => (
                            <li key={i}>
                              <span className="font-medium">{lz.status} </span>
                              <span className="font-semibold">
                                {lz.ziel}:
                              </span>{" "}
                              {lz.note}
                            </li>
                          ))}
                        </ul>
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

                    {result.unit_content && (
                      <div className="mt-4 rounded-md bg-muted/60 p-3 text-sm text-muted-foreground">
                        <div className="font-semibold text-foreground mb-1">
                          Interne Unit (Auszug)
                        </div>
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
              <Button
                variant="outline"
                onClick={() => router.push("/?step=matches", { scroll: false })}
              >
                Andere Units wählen
              </Button>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
