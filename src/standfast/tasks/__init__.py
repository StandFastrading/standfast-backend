"""Background jobs.

When the first job lands (e.g., nightly behavioral-pattern rollup), pick a runner —
arq (asyncio-native, Redis) is the default recommendation; celery if we already
have a worker fleet. Until then, FastAPI BackgroundTasks suffices for small,
fire-and-forget work.
"""
