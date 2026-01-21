#!/usr/bin/env python3
"""Check OpenAPI documentation for response models."""
import json

with open('/tmp/openapi_response.json', 'r') as f:
    data = json.load(f)

schemas = data.get('components', {}).get('schemas', {})
print(f'Total schemas: {len(schemas)}')
print('\nResponse model schemas:')
for name in sorted(schemas.keys()):
    print(f'  - {name}')

# Check for expected response models from our implementation
expected_models = [
    # research.py
    'ResearchPromptResponse',
    'CurrentResearchResponse',
    'LatestResearchResponse',
    'GenerateResearchResponse',
    'ResearchStatusResponse',
    'ResearchHistoryResponse',
    'VerifyResearchResponse',
    'ResearchReportResponse',
    'LatestGraphsResponse',
    'LatestDataPackageResponse',
    # council.py
    'CouncilDecisionResponse',
    'SynthesizeCouncilResponse',
    # pitches.py
    'PMPitch',
    'CurrentPitchesResponse',
    'GeneratePitchesResponse',
    'PitchStatusResponse',
    'ApprovePitchResponse',
    # market.py
    'MarketSnapshotResponse',
    'MarketMetricsResponse',
    'CurrentPricesResponse',
    # monitor.py
    'PositionItem',
    'AccountSummary',
    # trades.py
    'PendingTrade',
    'ExecuteTradesResponse',
    # conversations.py
    'ConversationMetadata',
    'Conversation',
    'CouncilResponse',
]

print('\n\nChecking for expected response models:')
missing = []
for model in expected_models:
    if model in schemas:
        print(f'  ✓ {model}')
    else:
        print(f'  ✗ {model} (MISSING)')
        missing.append(model)

if missing:
    print(f'\n⚠️  Missing {len(missing)} expected models')
else:
    print(f'\n✓ All {len(expected_models)} expected models are present!')

print(f'\n✓ OpenAPI documentation generated successfully with {len(schemas)} schemas')
