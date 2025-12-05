import { NextRequest, NextResponse } from 'next/server'
import { matchingService, MatchingServiceError } from '@/lib/matching-service'

export async function POST(request: NextRequest) {
  try {
    const { external_module, unit_ids } = await request.json()

    if (!external_module || !unit_ids || !Array.isArray(unit_ids)) {
      return NextResponse.json(
        { error: 'external_module and unit_ids are required' },
        { status: 400 }
      )
    }

    const data = await matchingService.compareMultiple(external_module, unit_ids)
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error in /api/compare-multiple:', error)

    if (error instanceof MatchingServiceError) {
      return NextResponse.json({ error: error.message }, { status: error.status })
    }

    return NextResponse.json(
      { error: 'Failed to compare modules' },
      { status: 500 }
    )
  }
}
