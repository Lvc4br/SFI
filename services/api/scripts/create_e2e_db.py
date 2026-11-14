import asyncio

from sfi_api.database import _engine
from sfi_api.models import Base


async def main() -> None:
    if _engine is None:
        raise RuntimeError("SFI_DATABASE_URL must point to an isolated test database.")
    async with _engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await _engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
