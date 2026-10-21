"""Word by word (`glosses`): stored on the drill as JSON and returned as such."""
import json
from test_api import client


def test_glosses_round_trip():
    g = [{"shi": "ur", "tif": "ⵓⵔ", "ca": "no"}, {"shi": "ssinɣ", "tif": "ⵙⵙⵉⵏⵖ", "ca": "ho sé"}]
    d = client.post("/drills/", json={"text_catalan": "no ho sé", "text_tachelhit": "ur ssinɣ", "glosses": json.dumps(g, ensure_ascii=False)}).json()
    back = json.loads(client.get(f"/drills/{d['id']}").json()["glosses"])
    assert back[1]["ca"] == "ho sé" and back[0]["tif"] == "ⵓⵔ"
    client.put(f"/drills/{d['id']}", json={"glosses": None})
    assert client.get(f"/drills/{d['id']}").json()["glosses"] is None
