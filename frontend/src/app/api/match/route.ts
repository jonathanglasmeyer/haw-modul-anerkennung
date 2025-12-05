import { NextRequest, NextResponse } from 'next/server'
import { matchingService, MatchingServiceError } from '@/lib/matching-service'

export async function POST(request: NextRequest) {
  try {
    const { text, limit } = await request.json()

    if (!text) {
      return NextResponse.json(
        { error: 'text is required' },
        { status: 400 }
      )
    }

    const data = await matchingService.match(text, limit)
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error in /api/match:', error)

    if (error instanceof MatchingServiceError) {
      return NextResponse.json({ error: error.message }, { status: error.status })
    }

    return NextResponse.json(
      { error: 'Failed to match modules' },
      { status: 500 }
    )
  }
}
