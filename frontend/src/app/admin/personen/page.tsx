'use client';

import { useEffect, useState } from 'react';
import { adminService, type Person } from '@/lib/admin-service';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Input } from '@/components/ui/input';

export default function AdminPersonenPage() {
  const [personen, setPersonen] = useState<Person[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [selectedPerson, setSelectedPerson] = useState<Person | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [formData, setFormData] = useState<Partial<Person>>({});
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const loadPersonen = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await adminService.getPersonen();
      setPersonen(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load personen');
    } finally {
      setLoading(false);
    }
  };

  const openCreate = () => {
    setSelectedPerson(null);
    setEditMode(true);
    setFormData({ name: '' });
    setFormError('');
    setSidebarOpen(true);
  };

  const openView = (person: Person) => {
    setSelectedPerson(person);
    setEditMode(false);
    setFormData({ name: person.name });
    setFormError('');
    setSidebarOpen(true);
  };

  const startEdit = () => {
    setEditMode(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name?.trim()) {
      setFormError('Name ist erforderlich');
      return;
    }

    try {
      setSubmitting(true);
      setFormError('');

      if (selectedPerson) {
        await adminService.updatePerson(selectedPerson.id, formData);
      } else {
        await adminService.createPerson(formData);
      }

      await loadPersonen();
      setSidebarOpen(false);
      setSelectedPerson(null);
      setEditMode(false);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Failed to save');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Person wirklich löschen? Diese wird aus allen Unit-Zuordnungen entfernt.')) return;

    try {
      setDeletingId(id);
      await adminService.deletePerson(id);
      await loadPersonen();
      setSidebarOpen(false);
      setSelectedPerson(null);
    } catch (err) {
      alert(`Fehler: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setDeletingId(null);
    }
  };

  useEffect(() => {
    loadPersonen();
  }, []);

  if (loading) {
    return (
      <div className="space-y-6 pb-8">
        <div className="flex items-start justify-between border-b pb-6">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight mb-2">
              Personen
            </h1>
            <p className="text-sm text-muted-foreground">Lädt...</p>
          </div>
        </div>
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="animate-pulse text-muted-foreground">Lädt Personen...</div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="space-y-6 pb-8">
        {/* Header */}
        <div className="flex items-start justify-between border-b pb-6">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight mb-2">
              Personen
            </h1>
            <p className="text-sm text-muted-foreground">
              {personen.length} {personen.length === 1 ? 'Person' : 'Personen'}
            </p>
          </div>
          <div className="flex gap-3">
            <Button
              onClick={loadPersonen}
              variant="outline"
              size="sm"
            >
              Reload
            </Button>
            <Button
              onClick={openCreate}
              size="sm"
            >
              + Neue Person
            </Button>
          </div>
        </div>

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Table */}
        <div className="bg-card border rounded-lg overflow-hidden shadow-sm">
          <table className="w-full">
            <thead>
              <tr className="bg-muted/50 border-b">
                <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  ID
                </th>
                <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Name
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {personen.map((person) => (
                <tr
                  key={person.id}
                  onClick={() => openView(person)}
                  className="hover:bg-muted/50 transition-colors cursor-pointer"
                >
                  <td className="px-6 py-4">
                    <span className="font-mono text-sm text-muted-foreground">
                      {person.id}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-sm font-medium">
                      {person.name}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {personen.length === 0 && (
            <div className="text-center py-12 text-muted-foreground">
              <p className="text-sm">Keine Personen gefunden</p>
            </div>
          )}
        </div>
      </div>

      {/* Sidebar */}
      {sidebarOpen && (
        <>
          <style jsx>{`
            @keyframes slideIn {
              from { transform: translateX(100%); }
              to { transform: translateX(0); }
            }
            @keyframes fadeIn {
              from { opacity: 0; }
              to { opacity: 1; }
            }
            .sidebar-enter {
              animation: slideIn 0.15s cubic-bezier(0.4, 0, 0.2, 1);
            }
            .backdrop-enter {
              animation: fadeIn 0.15s ease;
            }
          `}</style>

          {/* Backdrop */}
          <div
            className="backdrop-enter fixed inset-0 bg-black/50 z-40"
            onClick={() => setSidebarOpen(false)}
          />

          {/* Sidebar Panel */}
          <div className="sidebar-enter fixed top-0 right-0 h-full w-full max-w-lg bg-card shadow-2xl z-50 border-l">
            <div className="h-full flex flex-col">
              {/* Header */}
              <div className="px-8 py-6 border-b">
                <div className="flex items-center justify-between">
                  <h2 className="text-2xl font-semibold">
                    {editMode ? (selectedPerson ? 'Person bearbeiten' : 'Neue Person') : 'Person Details'}
                  </h2>
                  <button
                    onClick={() => setSidebarOpen(false)}
                    className="text-muted-foreground hover:text-foreground transition-colors"
                  >
                    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>

              {/* Content */}
              <div className="flex-1 overflow-y-auto px-8 py-6">
                {!editMode && selectedPerson ? (
                  // View Mode
                  <div className="space-y-6">
                    <div>
                      <label className="block text-sm font-medium text-muted-foreground mb-2">
                        ID
                      </label>
                      <div className="font-mono text-sm">{selectedPerson.id}</div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-muted-foreground mb-2">
                        Name
                      </label>
                      <div className="text-sm">{selectedPerson.name}</div>
                    </div>
                  </div>
                ) : (
                  // Edit/Create Mode
                  <form onSubmit={handleSubmit} className="space-y-6">
                    {formError && (
                      <Alert variant="destructive">
                        <AlertDescription>{formError}</AlertDescription>
                      </Alert>
                    )}

                    <div>
                      <label htmlFor="name" className="block text-sm font-medium mb-2">
                        Name *
                      </label>
                      <Input
                        id="name"
                        value={formData.name || ''}
                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                        placeholder="z.B. Prof. Dr. Schmidt"
                        autoFocus
                      />
                      <p className="mt-2 text-xs text-muted-foreground">
                        Der vollständige Name der verantwortlichen Person
                      </p>
                    </div>
                  </form>
                )}
              </div>

              {/* Footer */}
              <div className="px-8 py-6 border-t bg-muted/30">
                {!editMode && selectedPerson ? (
                  // View Mode Actions
                  <div className="space-y-3">
                    <Button
                      onClick={startEdit}
                      className="w-full"
                    >
                      Bearbeiten
                    </Button>
                    <Button
                      onClick={() => handleDelete(selectedPerson.id)}
                      disabled={deletingId === selectedPerson.id}
                      variant="destructive"
                      className="w-full"
                    >
                      {deletingId === selectedPerson.id ? 'Löscht...' : 'Löschen'}
                    </Button>
                  </div>
                ) : (
                  // Edit Mode Actions
                  <div className="flex items-center justify-end gap-3">
                    <Button
                      type="button"
                      onClick={() => {
                        if (selectedPerson) {
                          setEditMode(false);
                          setFormData({ name: selectedPerson.name });
                        } else {
                          setSidebarOpen(false);
                        }
                      }}
                      variant="outline"
                    >
                      Abbrechen
                    </Button>
                    <Button
                      onClick={handleSubmit}
                      disabled={submitting}
                    >
                      {submitting ? 'Speichert...' : 'Speichern'}
                    </Button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
}
