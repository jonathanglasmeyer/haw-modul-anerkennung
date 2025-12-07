import { NextRequest, NextResponse } from 'next/server'

const MATCHING_API_URL = process.env.MATCHING_API_URL || 'https://matching-api.quietloop.dev'

export async function GET(request: NextRequest) {
  try {
    const token = request.headers.get('authorization')
    if (!token) {
      return NextResponse.json({ error: 'Not authenticated' }, { status: 401 })
    }

    const response = await fetch(`${MATCHING_API_URL}/api/admin/personen`, {
      headers: {
        'Authorization': token,
      },
    })

    if (!response.ok) {
      return NextResponse.json(
        { error: 'Failed to fetch personen' },
        { status: response.status }
      )
    }

    return NextResponse.json(await response.json())
  } catch (error) {
    console.error('Error in /api/admin/personen GET:', error)
    return NextResponse.json(
      { error: 'Failed to fetch personen' },
      { status: 500 }
    )
  }
}

export async function POST(request: NextRequest) {
  try {
    const token = request.headers.get('authorization')
    if (!token) {
      return NextResponse.json({ error: 'Not authenticated' }, { status: 401 })
    }

    const body = await request.json()

    const response = await fetch(`${MATCHING_API_URL}/api/admin/personen`, {
      method: 'POST',
      headers: {
        'Authorization': token,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      return NextResponse.json(
        { error: 'Failed to create person' },
        { status: response.status }
      )
    }

    return NextResponse.json(await response.json())
  } catch (error) {
    console.error('Error in /api/admin/personen POST:', error)
    return NextResponse.json(
      { error: 'Failed to create person' },
      { status: 500 }
    )
  }
}
