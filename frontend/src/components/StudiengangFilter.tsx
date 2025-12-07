import { type Studiengang, STUDIENGAENGE } from "@/lib/studiengang";

type StudiengangFilter = 'all' | Studiengang;

interface StudiengangFilterProps {
  value: StudiengangFilter;
  onChange: (value: StudiengangFilter) => void;
}

export function StudiengangFilter({ value, onChange }: StudiengangFilterProps) {
  return (
    <div className="inline-flex border border-border rounded-sm p-1 gap-1 bg-muted/30">
      <button
        onClick={() => onChange('all')}
        className={`px-3 py-1.5 text-xs font-medium rounded-sm transition-colors ${
          value === 'all'
            ? 'bg-primary text-primary-foreground shadow-sm'
            : 'bg-transparent text-muted-foreground hover:bg-background/50 hover:text-foreground'
        }`}
      >
        Alle
      </button>
      {(Object.keys(STUDIENGAENGE) as Studiengang[]).map((key) => (
        <button
          key={key}
          onClick={() => onChange(key)}
          className={`px-3 py-1.5 text-xs font-medium rounded-sm transition-colors ${
            value === key
              ? 'bg-primary text-primary-foreground shadow-sm'
              : 'bg-transparent text-muted-foreground hover:bg-background/50 hover:text-foreground'
          }`}
        >
          {STUDIENGAENGE[key]}
        </button>
      ))}
    </div>
  );
}
