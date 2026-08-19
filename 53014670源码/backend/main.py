from app import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn

    from app.core.config import settings

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
