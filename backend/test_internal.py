import asyncio
import traceback
from app.api.routes_chat import stream_chat_sesion
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings

async def main():
    try:
        # Mock payload and db
        class MockPayload:
            def get(self, key, default):
                if key == 'mensaje': return 'hola'
                if key == 'fuentes_ids': return []
                if key == 'history': return []
                return default

        settings = get_settings()
        engine = create_async_engine(settings.DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            response = await stream_chat_sesion(1, MockPayload(), db)
            print("Response:", response)
    except Exception as e:
        print("EXCEPTION OCCURRED:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
