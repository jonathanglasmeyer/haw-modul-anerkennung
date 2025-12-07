import { NextRequest, NextResponse } from 'next/server'

const MATCHING_API_URL = process.env.MATCHING_API_URL || 'https://matching-api.quietloop.dev'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()

    const response = await fetch(`${MATCHING_API_URL}/api/admin/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      return NextResponse.json(
        { error: 'Invalid password' },
        { status: response.status }
      )
    }

    return NextResponse.json(await response.json())
  } catch (error) {
    console.error('Error in /api/admin/login:', error)
    return NextResponse.json(
      { error: 'Login failed' },
      { status: 500 }
    )
  }
}
