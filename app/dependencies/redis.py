from redis.asyncio import Redis


async def get_redis() -> Redis:
    client = Redis(host="redis", port=6379, db=0)
    try:
        yield client
    finally:
        await client.aclose()
