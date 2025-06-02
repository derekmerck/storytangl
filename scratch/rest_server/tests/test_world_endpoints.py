

def test_world_info(client, world):
    response = client.get(f"world/{world.label}/info")
    assert response.status_code == 200
    update = response.json()
    print( update )
