# Auto-Deployment Setup

Auto-Deploy bei push auf `main` via GitHub Actions.

## GitHub Secrets einrichten

Gehe zu: **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Füge folgende Secrets hinzu:

### 1. `SSH_PRIVATE_KEY`
Dein privater SSH-Key für den Hetzner Server.

```bash
# Key anzeigen (auf deinem Mac)
cat ~/.ssh/id_rsa
```

Kompletten Inhalt kopieren (inkl. `-----BEGIN OPENSSH PRIVATE KEY-----` und `-----END OPENSSH PRIVATE KEY-----`).

### 2. `SSH_HOST`
IP-Adresse oder Hostname deines Hetzner Servers.

Beispiel: `65.108.123.45` oder `hetzner-01.example.com`

### 3. `SSH_USER`
SSH-Username auf dem Hetzner Server.

Beispiel: `root` oder `deploy`

## Workflow

Bei jedem Push auf `main`:
1. GitHub Actions checkout Code
2. SSH zum Hetzner Server
3. `git pull origin main`
4. `docker compose up -d --build`
5. Health check auf `/health` endpoint

## Trigger nur bei matching-api Changes

Der Workflow läuft nur, wenn:
- `matching-api/**` Dateien geändert wurden
- `.github/workflows/deploy.yml` geändert wurde

Frontend-Changes triggern kein Deployment.

## Manueller Deploy

Falls GitHub Actions nicht läuft:

```bash
cd matching-api
./deploy.sh
```
