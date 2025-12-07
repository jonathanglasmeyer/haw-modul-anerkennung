'use client';

import React, { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { adminService, type Module, type Unit } from '@/lib/admin-service';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import Link from 'next/link';
import { type Studiengang, matchesStudiengang } from '@/lib/studiengang';
import { StudiengangFilter as StudiengangFilterComponent } from '@/components/StudiengangFilter';

type StudiengangFilter = 'all' | Studiengang;

export default function AdminModulesPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [modules, setModules] = useState<Module[]>([]);
  const [units, setUnits] = useState<Unit[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [selectedModule, setSelectedModule] = useState<Module | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [formData, setFormData] = useState<Partial<Module>>({});
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [filterStudiengang, setFilterStudiengang] = useState<StudiengangFilter>('all');

  const loadModules = async () => {
    try {
      setLoading(true);
      setError('');
      const [modulesData, unitsData] = await Promise.all([
        adminService.getModules(),
        adminService.getUnits(),
      ]);
      setModules(modulesData);
      setUnits(unitsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load modules');
    } finally {
      setLoading(false);
    }
  };

  const openCreate = () => {
    setSelectedModule(null);
    setEditMode(true);
    setFormData({
      module_id: '',
      title: '',
      credits: undefined,
      sws: undefined,
      semester: undefined,
      lernziele: '',
      pruefungsleistung: '',
    });
    setFormError('');
    setSidebarOpen(true);
  };

  const openView = (module: Module) => {
    setSelectedModule(module);
    setEditMode(false);
    setFormData({
      module_id: module.module_id,
      title: module.title,
      credits: module.credits ?? undefined,
      sws: module.sws ?? undefined,
      semester: module.semester ?? undefined,
      lernziele: module.lernziele || '',
      pruefungsleistung: module.pruefungsleistung || '',
    });
    setFormError('');
    setSidebarOpen(true);
    router.push(`/admin/modules?id=${module.id}`);
  };

  const closeSidebar = () => {
    setSidebarOpen(false);
    setSelectedModule(null);
    setEditMode(false);
    router.push('/admin/modules');
  };

  const startEdit = () => {
    setEditMode(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.module_id?.trim() || !formData.title?.trim()) {
      setFormError('Modul ID und Titel sind erforderlich');
      return;
    }

    try {
      setSubmitting(true);
      setFormError('');

      if (selectedModule) {
        await adminService.updateModule(selectedModule.id, formData);
      } else {
        await adminService.createModule(formData);
      }

      await loadModules();
      closeSidebar();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Failed to save');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Modul wirklich löschen? Alle zugehörigen Units verlieren ihre Modul-Zuordnung.')) return;

    try {
      setDeletingId(id);
      await adminService.deleteModule(id);
      await loadModules();
      closeSidebar();
    } catch (err) {
      alert(`Fehler: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setDeletingId(null);
    }
  };

  useEffect(() => {
    loadModules();
  }, []);

  // Open module from query parameter
  useEffect(() => {
    const moduleId = searchParams.get('id');
    if (moduleId && modules.length > 0) {
      const module = modules.find(m => m.id === parseInt(moduleId));
      if (module) {
        setSelectedModule(module);
        setEditMode(false);
        setFormData({
          module_id: module.module_id,
          title: module.title,
          credits: module.credits ?? undefined,
          sws: module.sws ?? undefined,
          semester: module.semester ?? undefined,
          lernziele: module.lernziele || '',
          pruefungsleistung: module.pruefungsleistung || '',
        });
        setFormError('');
        setSidebarOpen(true);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, modules]);

  if (loading) {
    return (
      <div className="space-y-6 pb-8">
        <div className="flex items-start justify-between border-b pb-6">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight mb-2">
              Module
            </h1>
            <p className="text-sm text-muted-foreground">Lädt...</p>
          </div>
        </div>
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="animate-pulse text-muted-foreground">Lädt Module...</div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="space-y-6 pb-8">
        {/* Header */}
        <div className="flex items-start justify-between pb-6">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">
              Module
            </h1>
          </div>
          <Button
            onClick={openCreate}
            size="sm"
          >
            + Neues Modul
          </Button>
        </div>

        {/* Studiengang Filter */}
        <div className="space-y-4">
          <StudiengangFilterComponent
            value={filterStudiengang}
            onChange={setFilterStudiengang}
          />

          <p className="text-sm text-muted-foreground">
            {modules.filter(module => {
              if (filterStudiengang === 'all') return true;
              return matchesStudiengang(module.module_id, filterStudiengang);
            }).length} {modules.length === 1 ? 'Modul' : 'Module'}
          </p>
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
                <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Modul ID
                </th>
                <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Titel
                </th>
                <th className="text-center px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Credits
                </th>
                <th className="text-center px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  SWS
                </th>
                <th className="text-center px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Sem
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {modules
                .filter(module => {
                  if (filterStudiengang === 'all') return true;
                  return matchesStudiengang(module.module_id, filterStudiengang);
                })
                .map((module) => (
                <tr
                  key={module.id}
                  onClick={() => openView(module)}
                  className="hover:bg-muted/50 transition-colors cursor-pointer"
                >
                  <td className="px-4 py-4">
                    <span className="font-mono text-xs bg-muted px-2 py-1 rounded">
                      {module.module_id}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-sm font-medium">
                      {module.title}
                    </span>
                  </td>
                  <td className="px-4 py-4 text-center">
                    <span className="text-sm">
                      {module.credits ?? '—'}
                    </span>
                  </td>
                  <td className="px-4 py-4 text-center">
                    <span className="text-sm">
                      {module.sws ?? '—'}
                    </span>
                  </td>
                  <td className="px-4 py-4 text-center">
                    <span className="text-sm">
                      {module.semester ?? '—'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {modules.length === 0 && (
            <div className="text-center py-12 text-muted-foreground">
              <p className="text-sm">Keine Module gefunden</p>
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
            onClick={closeSidebar}
          />

          {/* Sidebar Panel */}
          <div className="sidebar-enter fixed top-0 right-0 h-full w-full max-w-2xl bg-card shadow-2xl z-50 border-l">
            <div className="h-full flex flex-col">
              {/* Header */}
              <div className="px-8 py-6 border-b">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-2xl font-semibold">
                      {editMode
                        ? (selectedModule ? 'Modul bearbeiten' : 'Neues Modul')
                        : selectedModule?.title
                      }
                    </h2>
                    {!editMode && selectedModule && (
                      <p className="mt-1 text-sm font-mono text-muted-foreground">
                        {selectedModule.module_id}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={closeSidebar}
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
                {!editMode && selectedModule ? (
                  // View Mode
                  <div className="space-y-6">
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-muted-foreground mb-2">
                          Credits
                        </label>
                        <div className="text-sm">{selectedModule.credits ?? '—'}</div>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-muted-foreground mb-2">
                          SWS
                        </label>
                        <div className="text-sm">{selectedModule.sws ?? '—'}</div>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-muted-foreground mb-2">
                          Semester
                        </label>
                        <div className="text-sm">{selectedModule.semester ?? '—'}</div>
                      </div>
                    </div>
                    {selectedModule.lernziele && (
                      <div>
                        <label className="block text-sm font-medium text-muted-foreground mb-2">
                          Lernziele
                        </label>
                        <div className="text-sm text-muted-foreground [&_h1]:text-sm [&_h1]:font-semibold [&_h1]:mb-1 [&_h2]:text-sm [&_h2]:font-semibold [&_h2]:mb-1 [&_h3]:text-sm [&_h3]:font-semibold [&_h3]:mb-1 [&_ul]:list-disc [&_ul]:ml-4 [&_li]:mb-0.5 [&_table]:border-collapse [&_table]:w-full [&_table]:my-2 [&_th]:border [&_th]:border-border [&_th]:px-2 [&_th]:py-1 [&_th]:bg-muted/50 [&_th]:text-left [&_th]:text-xs [&_th]:font-medium [&_td]:border [&_td]:border-border [&_td]:px-2 [&_td]:py-1 [&_td]:text-xs">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{selectedModule.lernziele}</ReactMarkdown>
                        </div>
                      </div>
                    )}
                    {selectedModule.pruefungsleistung && (
                      <div>
                        <label className="block text-sm font-medium text-muted-foreground mb-2">
                          Prüfungsleistung
                        </label>
                        <div className="text-sm text-muted-foreground [&_h1]:text-sm [&_h1]:font-semibold [&_h1]:mb-1 [&_h2]:text-sm [&_h2]:font-semibold [&_h2]:mb-1 [&_h3]:text-sm [&_h3]:font-semibold [&_h3]:mb-1 [&_ul]:list-disc [&_ul]:ml-4 [&_li]:mb-0.5 [&_table]:border-collapse [&_table]:w-full [&_table]:my-2 [&_th]:border [&_th]:border-border [&_th]:px-2 [&_th]:py-1 [&_th]:bg-muted/50 [&_th]:text-left [&_th]:text-xs [&_th]:font-medium [&_td]:border [&_td]:border-border [&_td]:px-2 [&_td]:py-1 [&_td]:text-xs">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{selectedModule.pruefungsleistung}</ReactMarkdown>
                        </div>
                      </div>
                    )}
                    {/* Units zugeordnet zu diesem Modul */}
                    {(() => {
                      const moduleUnits = units.filter(u => u.module_id === selectedModule.id);
                      return moduleUnits.length > 0 && (
                        <div>
                          <label className="block text-sm font-medium text-muted-foreground mb-2">
                            Units ({moduleUnits.length})
                          </label>
                          <div className="space-y-2">
                            {moduleUnits.map(unit => (
                              <Link
                                key={unit.id}
                                href={`/admin/units?id=${unit.id}`}
                                prefetch={true}
                                className="block px-3 py-2 rounded-md border hover:bg-muted/50 transition-colors"
                              >
                                <div className="flex items-center justify-between">
                                  <div>
                                    <div className="text-sm font-medium">{unit.title}</div>
                                    <div className="text-xs font-mono text-muted-foreground">{unit.unit_id}</div>
                                  </div>
                                  <svg className="w-4 h-4 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                  </svg>
                                </div>
                              </Link>
                            ))}
                          </div>
                        </div>
                      );
                    })()}
                  </div>
                ) : (
                  // Edit/Create Mode
                  <form onSubmit={handleSubmit} className="space-y-6">
                    {formError && (
                      <Alert variant="destructive">
                        <AlertDescription>{formError}</AlertDescription>
                      </Alert>
                    )}

                    <div className="grid grid-cols-2 gap-6">
                      <div>
                        <label htmlFor="module_id" className="block text-sm font-medium mb-2">
                          Modul ID *
                        </label>
                        <Input
                          id="module_id"
                          value={formData.module_id || ''}
                          onChange={(e) => setFormData({ ...formData, module_id: e.target.value })}
                          placeholder="z.B. BAPuMa_M19P"
                          className="font-mono"
                        />
                      </div>

                      <div>
                        <label htmlFor="title" className="block text-sm font-medium mb-2">
                          Titel *
                        </label>
                        <Input
                          id="title"
                          value={formData.title || ''}
                          onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                          placeholder="z.B. Verwaltungsinformatik"
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <label htmlFor="credits" className="block text-sm font-medium mb-2">
                          Credits
                        </label>
                        <Input
                          id="credits"
                          type="number"
                          value={formData.credits ?? ''}
                          onChange={(e) => setFormData({ ...formData, credits: e.target.value ? parseInt(e.target.value) : undefined })}
                          placeholder="6"
                        />
                      </div>

                      <div>
                        <label htmlFor="sws" className="block text-sm font-medium mb-2">
                          SWS
                        </label>
                        <Input
                          id="sws"
                          type="number"
                          value={formData.sws ?? ''}
                          onChange={(e) => setFormData({ ...formData, sws: e.target.value ? parseInt(e.target.value) : undefined })}
                          placeholder="4"
                        />
                      </div>

                      <div>
                        <label htmlFor="semester" className="block text-sm font-medium mb-2">
                          Semester
                        </label>
                        <Input
                          id="semester"
                          type="number"
                          value={formData.semester ?? ''}
                          onChange={(e) => setFormData({ ...formData, semester: e.target.value ? parseInt(e.target.value) : undefined })}
                          placeholder="5"
                        />
                      </div>
                    </div>

                    <div>
                      <label htmlFor="lernziele" className="block text-sm font-medium mb-2">
                        Lernziele
                      </label>
                      <Textarea
                        id="lernziele"
                        value={formData.lernziele || ''}
                        onChange={(e) => setFormData({ ...formData, lernziele: e.target.value })}
                        placeholder="Die Studierenden können..."
                        rows={6}
                        className="resize-none"
                      />
                    </div>

                    <div>
                      <label htmlFor="pruefungsleistung" className="block text-sm font-medium mb-2">
                        Prüfungsleistung
                      </label>
                      <Textarea
                        id="pruefungsleistung"
                        value={formData.pruefungsleistung || ''}
                        onChange={(e) => setFormData({ ...formData, pruefungsleistung: e.target.value })}
                        placeholder="Klausur (90 Minuten)"
                        rows={4}
                        className="resize-none"
                      />
                    </div>
                  </form>
                )}
              </div>

              {/* Footer */}
              <div className="px-8 py-6 border-t bg-muted/30">
                {!editMode && selectedModule ? (
                  // View Mode Actions
                  <div className="space-y-3">
                    <Button
                      onClick={startEdit}
                      className="w-full"
                    >
                      Bearbeiten
                    </Button>
                    <Button
                      onClick={() => handleDelete(selectedModule.id)}
                      disabled={deletingId === selectedModule.id}
                      variant="destructive"
                      className="w-full"
                    >
                      {deletingId === selectedModule.id ? 'Löscht...' : 'Löschen'}
                    </Button>
                  </div>
                ) : (
                  // Edit Mode Actions
                  <div className="flex items-center justify-end gap-3">
                    <Button
                      type="button"
                      onClick={() => {
                        if (selectedModule) {
                          setEditMode(false);
                          setFormData({
                            module_id: selectedModule.module_id,
                            title: selectedModule.title,
                            credits: selectedModule.credits ?? undefined,
                            sws: selectedModule.sws ?? undefined,
                            semester: selectedModule.semester ?? undefined,
                            lernziele: selectedModule.lernziele || '',
                            pruefungsleistung: selectedModule.pruefungsleistung || '',
                          });
                        } else {
                          closeSidebar();
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
