from app.core.redis import RedisCache


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.ttls = {}

    def get(self, key):
        return self.values.get(key)

    def setex(self, key, ttl, value):
        self.ttls[key] = ttl
        self.values[key] = value

    def delete(self, *keys):
        for key in keys:
            self.values.pop(key, None)

    def ping(self):
        return True


def test_redis_cache_round_trip_and_ttl():
    cache = RedisCache(url="redis://fake", ttl_seconds=17)
    fake = FakeRedis()
    cache._client = fake

    assert cache.set_json("tasks:1", {"value": 1}) is True
    assert cache.get_json("tasks:1") == {"value": 1}
    assert fake.ttls["tasks:1"] == 17
    assert cache.ping() is True

    assert cache.delete("tasks:1") is True
    assert cache.get_json("tasks:1") is None


def test_redis_cache_bypasses_when_unconfigured():
    cache = RedisCache(url=None)

    assert cache.get_json("missing") is None
    assert cache.set_json("missing", {"value": 1}) is False
    assert cache.delete("missing") is False
    assert cache.ping() is False