import json
from datetime import datetime, timezone

import pytest

from farescout.bridge import BrowserBridge
from farescout.models import Event, Goal, Turn
from farescout.safety import SourceFailure


def test_late_receipt_preserves_observation_and_matches_turn(tmp_path):
    bridge = BrowserBridge(tmp_path)
    timestamp = '2026-09-29T12:01:00+00:00'
    request = {'id': 'r1', 'query': '香港便宜机票', 'requested_at': timestamp}
    path = tmp_path / 'r1.request.json'
    path.write_text(json.dumps(request))
    response = {'request_id': 'r1', 'query': request['query'], 'observed_at': timestamp,
                'notes': [{'note': {'note_id': '1234567890', 'content': '香港飞大阪，刚买过机票。', 'title': '机票'}}]}
    (tmp_path / 'r1.response.json').write_text(json.dumps(response))
    turn = Turn(id='t', user_input='test', goal=Goal(date_from='2026-10-01', date_to='2026-11-01'),
                started_at='2026-09-29T12:00:00Z', finished_at='2026-09-29T12:10:00Z',
                events=[Event(source=bridge.name, stage='community_search', status='info', detail='只读搜索：香港便宜机票')])
    records = list(bridge.recover(turn))[0][2]
    assert records[0].observed_at == datetime.fromisoformat(timestamp)
    turn.events = []
    assert not list(bridge.recover(turn))
    response['query'] = 'unrelated'
    (tmp_path / 'r1.response.json').write_text(json.dumps(response))
    with pytest.raises(SourceFailure):
        bridge.read_receipt(path)
