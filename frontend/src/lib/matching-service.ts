const MATCHING_API_URL = process.env.MATCHING_API_URL || 'https://matching-api.quietloop.dev'
const MATCHING_API_KEY = process.env.MATCHING_API_KEY || ''

export class MatchingServiceError extends Error {
  constructor(message: string, public status: number) {
    super(message)
    this.name = 'MatchingServiceError'
  }
}

async function fetchAPI(endpoint: string, options: RequestInit = {}) {
  const url = `${MATCHING_API_URL}${endpoint}`
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': MATCHING_API_KEY,
      ...options.headers,
    },
  })

  if (!response.ok) {
    throw new MatchingServiceError(
      `API request failed: ${response.statusText}`,
      response.status
    )
  }

  return response.json()
}

export const matchingService = {
  async match(text: string, limit = 5, studiengang?: string) {
    return fetchAPI('/match', {
      method: 'POST',
      body: JSON.stringify({ text, limit, studiengang }),
    })
  },

  async parse(text: string) {
    return fetchAPI('/parse', {
      method: 'POST',
      body: JSON.stringify({ text }),
    })
  },

  async compareMultiple(externalModule: Record<string, unknown>, unitIds: string[], studiengang?: string) {
    return fetchAPI('/compare-multiple', {
      method: 'POST',
      body: JSON.stringify({
        external_module: externalModule,
        unit_ids: unitIds,
        studiengang,
      }),
    })
  },

  async health() {
    return fetchAPI('/health')
  },
}
