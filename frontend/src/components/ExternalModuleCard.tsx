import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface ParsedModule {
  title: string;
  credits?: number | null;
  workload?: string | null;
  level?: string | null;
  assessment?: string | null;
  institution?: string | null;
  learning_goals?: string[];
}

interface ExternalModuleCardProps {
  module: ParsedModule;
  sticky?: boolean;
}

export function ExternalModuleCard({ module, sticky = false }: ExternalModuleCardProps) {
  const content = (
    <Card className="border-l-4 border-l-primary">
      <CardHeader>
        <CardTitle className="text-base">Externes Modul</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div>
          <div className="text-muted-foreground">Titel</div>
          <div className="font-medium">{module.title}</div>
        </div>
        {module.credits !== undefined && module.credits !== null && (
          <div>
            <div className="text-muted-foreground">Credits</div>
            <div className="font-medium">{module.credits}</div>
          </div>
        )}
        {module.workload && (
          <div>
            <div className="text-muted-foreground">Workload</div>
            <div className="font-medium">{module.workload}</div>
          </div>
        )}
        {(module.learning_goals || []).length > 0 && (
          <div>
            <div className="text-muted-foreground mb-1">Lernziele</div>
            <ul className="list-disc list-inside text-muted-foreground space-y-1">
              {module.learning_goals!.map((goal, i) => (
                <li key={i} className="text-xs">{goal}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );

  if (sticky) {
    return <div className="sticky top-36">{content}</div>;
  }

  return content;
}
