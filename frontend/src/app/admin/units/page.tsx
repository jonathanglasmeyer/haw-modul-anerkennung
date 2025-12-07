'use client';

import React, { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { adminService, type Unit, type Module as ModuleType, type Person } from '@/lib/admin-service';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { type Studiengang, matchesStudiengang } from '@/lib/studiengang';
import { StudiengangFilter as StudiengangFilterComponent } from '@/components/StudiengangFilter';

type StudiengangFilter = 'all' | Studiengang;

export default function AdminUnitsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [units, setUnits] = useState<Unit[]>([]);
  const [modules, setModules] = useState<ModuleType[]>([]);
  const [personen, setPersonen] = useState<Person[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [selectedUnit, setSelectedUnit] = useState<Unit | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [formData, setFormData] = useState<Partial<Unit> & { verantwortliche_ids?: number[] }>({});
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [filterStudiengang, setFilterStudiengang] = useState<StudiengangFilter>('all');

  const loadData = async () => {
    try {
      setLoading(true);
      setError('');
      const [unitsData, modulesData, personenData] = await Promise.all([
        adminService.getUnits(),
        adminService.getModules(),
        adminService.getPersonen(),
      ]);
      setUnits(unitsData);
      setModules(modulesData);
      setPersonen(personenData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const openCreate = () => {
    setSelectedUnit(null);
    setEditMode(true);
    setFormData({
      unit_id: '',
      title: '',
      module_id: undefined,
      semester: undefined,
      sws: undefined,
      workload: '',
      lehrsprache: '',
      lernziele: '',
      inhalte: '',
      verantwortliche_ids: [],
    });
    setFormError('');
    setSidebarOpen(true);
  };

  const openView = (unit: Unit) => {
    setSelectedUnit(unit);
    setEditMode(false);
    setFormData({
      unit_id: unit.unit_id,
      title: unit.title,
      module_id: unit.module_id ?? undefined,
      semester: unit.semester ?? undefined,
      sws: unit.sws ?? undefined,
      workload: unit.workload || '',
      lehrsprache: unit.lehrsprache || '',
      lernziele: unit.lernziele || '',
      inhalte: unit.inhalte || '',
      verantwortliche_ids: unit.verantwortliche?.map(v => v.id) || [],
    });
    setFormError('');
    setSidebarOpen(true);
    router.push(`/admin/units?id=${unit.id}`);
  };

  const closeSidebar = () => {
    setSidebarOpen(false);
    setSelectedUnit(null);
    setEditMode(false);
    router.push('/admin/units');
  };

  // Open unit from query parameter
  useEffect(() => {
    const unitId = searchParams.get('id');
    if (unitId && units.length > 0) {
      const unit = units.find(u => u.id === parseInt(unitId));
      if (unit) {
        openView(unit);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, units]);

  const startEdit = () => {
    setEditMode(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.unit_id?.trim() || !formData.title?.trim() || !formData.module_id) {
      setFormError('Unit ID, Titel und Modul sind erforderlich');
      return;
    }

    try {
      setSubmitting(true);
      setFormError('');

      if (selectedUnit) {
        await adminService.updateUnit(selectedUnit.id, formData);
      } else {
        await adminService.createUnit(formData);
      }

      await loadData();
      closeSidebar();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Failed to save');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Unit wirklich löschen?')) return;

    try {
      setDeletingId(id);
      await adminService.deleteUnit(id);
      await loadData();
      closeSidebar();
    } catch (err) {
      alert(`Fehler: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setDeletingId(null);
    }
  };

  const toggleVerantwortliche = (personId: number) => {
    const current = formData.verantwortliche_ids || [];
    if (current.includes(personId)) {
      setFormData({
        ...formData,
        verantwortliche_ids: current.filter(id => id !== personId),
      });
    } else {
      setFormData({
        ...formData,
        verantwortliche_ids: [...current, personId],
      });
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="space-y-6 pb-8">
        <div className="flex items-start justify-between border-b pb-6">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight mb-2">
              Units
            </h1>
            <p className="text-sm text-muted-foreground">Lädt...</p>
          </div>
        </div>
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="animate-pulse text-muted-foreground">Lädt Units...</div>
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
              Units
            </h1>
          </div>
          <Button
            onClick={openCreate}
            size="sm"
          >
            + Neue Unit
          </Button>
        </div>

        {/* Studiengang Filter */}
        <div className="space-y-4">
          <StudiengangFilterComponent
            value={filterStudiengang}
            onChange={setFilterStudiengang}
          />

          <p className="text-sm text-muted-foreground">
            {units.filter(unit => {
              if (filterStudiengang === 'all') return true;
              return matchesStudiengang(unit.unit_id, filterStudiengang);
            }).length} {units.length === 1 ? 'Unit' : 'Units'}
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
                  Unit ID
                </th>
                <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Titel
                </th>
                <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Modul
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
              {units
                .filter(unit => {
                  if (filterStudiengang === 'all') return true;
                  return matchesStudiengang(unit.unit_id, filterStudiengang);
                })
                .map((unit) => (
                <tr
                  key={unit.id}
                  onClick={() => openView(unit)}
                  className="hover:bg-muted/50 transition-colors cursor-pointer"
                >
                  <td className="px-4 py-4">
                    <span className="font-mono text-xs bg-muted px-2 py-1 rounded">
                      {unit.unit_id}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-sm font-medium">
                      {unit.title}
                    </span>
                  </td>
                  <td className="px-4 py-4">
                    <span className="text-xs text-muted-foreground">
                      {unit.module_title || '—'}
                    </span>
                  </td>
                  <td className="px-4 py-4 text-center">
                    <span className="text-sm">
                      {unit.sws ?? '—'}
                    </span>
                  </td>
                  <td className="px-4 py-4 text-center">
                    <span className="text-sm">
                      {unit.semester ?? '—'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {units.length === 0 && (
            <div className="text-center py-12 text-muted-foreground">
              <p className="text-sm">Keine Units gefunden</p>
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
          <div className="sidebar-enter fixed top-0 right-0 h-full w-full max-w-3xl bg-card shadow-2xl z-50 border-l">
            <div className="h-full flex flex-col">
              {/* Header */}
              <div className="px-8 py-6 border-b">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-2xl font-semibold">
                      {editMode
                        ? (selectedUnit ? 'Unit bearbeiten' : 'Neue Unit')
                        : selectedUnit?.title
                      }
                    </h2>
                    {!editMode && selectedUnit && (
                      <p className="mt-1 text-sm font-mono text-muted-foreground">
                        {selectedUnit.unit_id}
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
                {!editMode && selectedUnit ? (
                  // View Mode
                  <div className="space-y-6">
                    <div>
                      <label className="block text-sm font-medium text-muted-foreground mb-2">
                        Modul
                      </label>
                      <div className="text-sm">{selectedUnit.module_title || '—'}</div>
                    </div>
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-muted-foreground mb-2">
                          SWS
                        </label>
                        <div className="text-sm">{selectedUnit.sws ?? '—'}</div>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-muted-foreground mb-2">
                          Semester
                        </label>
                        <div className="text-sm">{selectedUnit.semester ?? '—'}</div>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-muted-foreground mb-2">
                          Workload
                        </label>
                        <div className="text-sm">{selectedUnit.workload || '—'}</div>
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-muted-foreground mb-2">
                        Lehrsprache
                      </label>
                      <div className="text-sm">{selectedUnit.lehrsprache || '—'}</div>
                    </div>
                    {selectedUnit.verantwortliche && selectedUnit.verantwortliche.length > 0 && (
                      <div>
                        <label className="block text-sm font-medium text-muted-foreground mb-2">
                          Verantwortliche
                        </label>
                        <div className="text-sm">
                          {selectedUnit.verantwortliche.map(v => v.name).join(', ')}
                        </div>
                      </div>
                    )}
                    {selectedUnit.lernziele && (
                      <div>
                        <label className="block text-sm font-medium text-muted-foreground mb-2">
                          Lernziele
                        </label>
                        <div className="text-sm text-muted-foreground [&_h1]:text-sm [&_h1]:font-semibold [&_h1]:mb-1 [&_h2]:text-sm [&_h2]:font-semibold [&_h2]:mb-1 [&_h3]:text-sm [&_h3]:font-semibold [&_h3]:mb-1 [&_ul]:list-disc [&_ul]:ml-4 [&_li]:mb-0.5 [&_table]:border-collapse [&_table]:w-full [&_table]:my-2 [&_th]:border [&_th]:border-border [&_th]:px-2 [&_th]:py-1 [&_th]:bg-muted/50 [&_th]:text-left [&_th]:text-xs [&_th]:font-medium [&_td]:border [&_td]:border-border [&_td]:px-2 [&_td]:py-1 [&_td]:text-xs">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{selectedUnit.lernziele}</ReactMarkdown>
                        </div>
                      </div>
                    )}
                    {selectedUnit.inhalte && (
                      <div>
                        <label className="block text-sm font-medium text-muted-foreground mb-2">
                          Inhalte
                        </label>
                        <div className="text-sm text-muted-foreground [&_h1]:text-sm [&_h1]:font-semibold [&_h1]:mb-1 [&_h2]:text-sm [&_h2]:font-semibold [&_h2]:mb-1 [&_h3]:text-sm [&_h3]:font-semibold [&_h3]:mb-1 [&_ul]:list-disc [&_ul]:ml-4 [&_li]:mb-0.5 [&_table]:border-collapse [&_table]:w-full [&_table]:my-2 [&_th]:border [&_th]:border-border [&_th]:px-2 [&_th]:py-1 [&_th]:bg-muted/50 [&_th]:text-left [&_th]:text-xs [&_th]:font-medium [&_td]:border [&_td]:border-border [&_td]:px-2 [&_td]:py-1 [&_td]:text-xs">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{selectedUnit.inhalte}</ReactMarkdown>
                        </div>
                      </div>
                    )}
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
                        <label htmlFor="unit_id" className="block text-sm font-medium mb-2">
                          Unit ID *
                        </label>
                        <Input
                          id="unit_id"
                          value={formData.unit_id || ''}
                          onChange={(e) => setFormData({ ...formData, unit_id: e.target.value })}
                          placeholder="z.B. BAPuMa_M19P_U1"
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
                          placeholder="z.B. Vorlesung"
                        />
                      </div>
                    </div>

                    <div>
                      <label htmlFor="module" className="block text-sm font-medium mb-2">
                        Modul *
                      </label>
                      <Select
                        value={formData.module_id?.toString()}
                        onValueChange={(value) => setFormData({ ...formData, module_id: parseInt(value) })}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Modul auswählen..." />
                        </SelectTrigger>
                        <SelectContent>
                          {modules.map((module) => (
                            <SelectItem key={module.id} value={module.id.toString()}>
                              {module.module_id} - {module.title}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <label htmlFor="sws" className="block text-sm font-medium mb-2">
                          SWS
                        </label>
                        <Input
                          id="sws"
                          type="number"
                          value={formData.sws ?? ''}
                          onChange={(e) => setFormData({ ...formData, sws: e.target.value ? parseInt(e.target.value) : undefined })}
                          placeholder="2"
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

                      <div>
                        <label htmlFor="workload" className="block text-sm font-medium mb-2">
                          Workload
                        </label>
                        <Input
                          id="workload"
                          value={formData.workload || ''}
                          onChange={(e) => setFormData({ ...formData, workload: e.target.value })}
                          placeholder="60h"
                        />
                      </div>
                    </div>

                    <div>
                      <label htmlFor="lehrsprache" className="block text-sm font-medium mb-2">
                        Lehrsprache
                      </label>
                      <Input
                        id="lehrsprache"
                        value={formData.lehrsprache || ''}
                        onChange={(e) => setFormData({ ...formData, lehrsprache: e.target.value })}
                        placeholder="Deutsch"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-3">
                        Verantwortliche
                      </label>
                      <div className="space-y-2 max-h-40 overflow-y-auto border rounded-md p-3">
                        {personen.map((person) => (
                          <div key={person.id} className="flex items-center space-x-2">
                            <Checkbox
                              id={`person-${person.id}`}
                              checked={(formData.verantwortliche_ids || []).includes(person.id)}
                              onCheckedChange={() => toggleVerantwortliche(person.id)}
                            />
                            <label
                              htmlFor={`person-${person.id}`}
                              className="text-sm cursor-pointer flex-1"
                            >
                              {person.name}
                            </label>
                          </div>
                        ))}
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
                      <label htmlFor="inhalte" className="block text-sm font-medium mb-2">
                        Inhalte
                      </label>
                      <Textarea
                        id="inhalte"
                        value={formData.inhalte || ''}
                        onChange={(e) => setFormData({ ...formData, inhalte: e.target.value })}
                        placeholder="Themen der Unit..."
                        rows={6}
                        className="resize-none"
                      />
                    </div>
                  </form>
                )}
              </div>

              {/* Footer */}
              <div className="px-8 py-6 border-t bg-muted/30">
                {!editMode && selectedUnit ? (
                  // View Mode Actions
                  <div className="space-y-3">
                    <Button
                      onClick={startEdit}
                      className="w-full"
                    >
                      Bearbeiten
                    </Button>
                    <Button
                      onClick={() => handleDelete(selectedUnit.id)}
                      disabled={deletingId === selectedUnit.id}
                      variant="destructive"
                      className="w-full"
                    >
                      {deletingId === selectedUnit.id ? 'Löscht...' : 'Löschen'}
                    </Button>
                  </div>
                ) : (
                  // Edit Mode Actions
                  <div className="flex items-center justify-end gap-3">
                    <Button
                      type="button"
                      onClick={() => {
                        if (selectedUnit) {
                          setEditMode(false);
                          setFormData({
                            unit_id: selectedUnit.unit_id,
                            title: selectedUnit.title,
                            module_id: selectedUnit.module_id ?? undefined,
                            semester: selectedUnit.semester ?? undefined,
                            sws: selectedUnit.sws ?? undefined,
                            workload: selectedUnit.workload || '',
                            lehrsprache: selectedUnit.lehrsprache || '',
                            lernziele: selectedUnit.lernziele || '',
                            inhalte: selectedUnit.inhalte || '',
                            verantwortliche_ids: selectedUnit.verantwortliche?.map(v => v.id) || [],
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
