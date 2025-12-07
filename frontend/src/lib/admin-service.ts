/**
 * Admin API client for managing Units, Modules, and Personen
 * All requests go through Next.js API routes (/api/admin/*) to keep API keys server-side
 */

const API_URL = '/api/admin';

export interface Unit {
  id: number;
  unit_id: string;
  title: string;
  module_id: number;
  module_title?: string;
  semester?: number;
  sws?: number;
  workload?: string;
  lehrsprache?: string;
  lernziele?: string;
  inhalte?: string;
  verantwortliche: { id: number; name: string }[];
  created_at: string;
  updated_at: string;
}

export interface Module {
  id: number;
  module_id: string;
  title: string;
  credits?: number;
  sws?: number;
  semester?: number;
  lernziele?: string;
  pruefungsleistung?: string;
  created_at: string;
  updated_at: string;
}

export interface Person {
  id: number;
  name: string;
  created_at: string;
  updated_at: string;
}

class AdminService {
  private getToken(): string | null {
    return sessionStorage.getItem('admin_token');
  }

  private setToken(token: string): void {
    sessionStorage.setItem('admin_token', token);
  }

  clearToken(): void {
    sessionStorage.removeItem('admin_token');
  }

  async login(password: string): Promise<{ token: string }> {
    const response = await fetch(`${API_URL}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    });

    if (!response.ok) {
      throw new Error('Invalid password');
    }

    const data = await response.json();
    this.setToken(data.token);
    return data;
  }

  async logout(): Promise<void> {
    const token = this.getToken();
    if (!token) return;

    try {
      await fetch(`${API_URL}/logout`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
      });
    } finally {
      this.clearToken();
    }
  }

  // Units
  async getUnits(): Promise<Unit[]> {
    const token = this.getToken();
    if (!token) throw new Error('Not authenticated');

    const response = await fetch(`${API_URL}/units`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });

    if (response.status === 401) {
      this.clearToken();
      throw new Error('Session expired');
    }

    if (!response.ok) {
      throw new Error('Failed to fetch units');
    }

    const data = await response.json();
    return data.units;
  }

  async createUnit(unit: Partial<Unit>): Promise<Unit> {
    const token = this.getToken();
    if (!token) throw new Error('Not authenticated');

    const response = await fetch(`${API_URL}/units`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(unit),
    });

    if (!response.ok) {
      throw new Error('Failed to create unit');
    }

    return response.json();
  }

  async updateUnit(id: number, unit: Partial<Unit>): Promise<Unit> {
    const token = this.getToken();
    if (!token) throw new Error('Not authenticated');

    const response = await fetch(`${API_URL}/units/${id}`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(unit),
    });

    if (!response.ok) {
      throw new Error('Failed to update unit');
    }

    return response.json();
  }

  async deleteUnit(id: number): Promise<void> {
    const token = this.getToken();
    if (!token) throw new Error('Not authenticated');

    const response = await fetch(`${API_URL}/units/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` },
    });

    if (!response.ok) {
      throw new Error('Failed to delete unit');
    }
  }

  // Modules
  async getModules(): Promise<Module[]> {
    const token = this.getToken();
    if (!token) throw new Error('Not authenticated');

    const response = await fetch(`${API_URL}/modules`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch modules');
    }

    const data = await response.json();
    return data.modules;
  }

  async createModule(module: Partial<Module>): Promise<Module> {
    const token = this.getToken();
    if (!token) throw new Error('Not authenticated');

    const response = await fetch(`${API_URL}/modules`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(module),
    });

    if (!response.ok) {
      throw new Error('Failed to create module');
    }

    return response.json();
  }

  async updateModule(id: number, module: Partial<Module>): Promise<Module> {
    const token = this.getToken();
    if (!token) throw new Error('Not authenticated');

    const response = await fetch(`${API_URL}/modules/${id}`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(module),
    });

    if (!response.ok) {
      throw new Error('Failed to update module');
    }

    return response.json();
  }

  async deleteModule(id: number): Promise<void> {
    const token = this.getToken();
    if (!token) throw new Error('Not authenticated');

    const response = await fetch(`${API_URL}/modules/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` },
    });

    if (!response.ok) {
      throw new Error('Failed to delete module');
    }
  }

  // Personen
  async getPersonen(): Promise<Person[]> {
    const token = this.getToken();
    if (!token) throw new Error('Not authenticated');

    const response = await fetch(`${API_URL}/personen`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch personen');
    }

    const data = await response.json();
    return data.personen;
  }

  async createPerson(person: Partial<Person>): Promise<Person> {
    const token = this.getToken();
    if (!token) throw new Error('Not authenticated');

    const response = await fetch(`${API_URL}/personen`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(person),
    });

    if (!response.ok) {
      throw new Error('Failed to create person');
    }

    return response.json();
  }

  async updatePerson(id: number, person: Partial<Person>): Promise<Person> {
    const token = this.getToken();
    if (!token) throw new Error('Not authenticated');

    const response = await fetch(`${API_URL}/personen/${id}`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(person),
    });

    if (!response.ok) {
      throw new Error('Failed to update person');
    }

    return response.json();
  }

  async deletePerson(id: number): Promise<void> {
    const token = this.getToken();
    if (!token) throw new Error('Not authenticated');

    const response = await fetch(`${API_URL}/personen/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` },
    });

    if (!response.ok) {
      throw new Error('Failed to delete person');
    }
  }

}

export const adminService = new AdminService();
