import { NextRequest, NextResponse } from 'next/server'

const MATCHING_API_URL = process.env.MATCHING_API_URL || 'https://matching-api.quietloop.dev'

export async function POST(request: NextRequest) {
  try {
    const token = request.headers.get('authorization')
    if (!token) {
      return NextResponse.json({ error: 'No token provided' }, { status: 401 })
    }

    const response = await fetch(`${MATCHING_API_URL}/api/admin/logout`, {
      method: 'POST',
      headers: {
        'Authorization': token,
      },
    })

    if (!response.ok) {
      return NextResponse.json(
        { error: 'Logout failed' },
        { status: response.status }
      )
    }

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Error in /api/admin/logout:', error)
    return NextResponse.json(
      { error: 'Logout failed' },
      { status: 500 }
    )
  }
}
