"""
Main FastAPI application entry point for the 2id8 backend.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import time
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.logging import logger
from app.database.base import engine, Base
from app.utils.llm_handler import llm_call_handler

# Import routers
from app.routes.onboarding import router as onboarding_router
from app.routes.idea_generation import router as idea_generation_router
from app.routes.evaluation import router as evaluation_router
from app.routes.iteration import router as iteration_router
from app.routes.feedback import router as feedback_router
from app.routes.llm_logs import router as llm_logs_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting 2id8 Backend Application")
    
    # Create database tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
    
    # Start LLM call handler
    try:
        await llm_call_handler.start_processing()
        logger.info("LLM call handler started successfully")
    except Exception as e:
        logger.error(f"Error starting LLM call handler: {e}")
    
    logger.info("Application startup completed")
    
    yield
    
    # Shutdown
    logger.info("Shutting down 2id8 Backend Application")
    
    # Stop LLM call handler
    try:
        await llm_call_handler.stop_processing()
        logger.info("LLM call handler stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping LLM call handler: {e}")
    
    logger.info("Application shutdown completed")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered idea generation and evaluation platform backend",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.debug else ["localhost", "127.0.0.1"]
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header to responses."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log request
    logger.info(
        f"{request.method} {request.url.path} - "
        f"{response.status_code} - {process_time:.3f}s"
    )
    
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error" if not settings.debug else str(exc),
            "type": "internal_server_error"
        }
    )


# HTTP exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with consistent format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "type": "http_exception"
        }
    )


# Include routers
app.include_router(onboarding_router, prefix="/api/v1")
app.include_router(idea_generation_router, prefix="/api/v1")
app.include_router(evaluation_router, prefix="/api/v1")
app.include_router(iteration_router, prefix="/api/v1")
app.include_router(feedback_router, prefix="/api/v1")
app.include_router(llm_logs_router, prefix="/api/v1")


# Health check endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": settings.app_version
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with system information."""
    try:
        # Check database connection
        from app.database.session import get_db
        db = next(get_db())
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    # Check LLM handler status
    try:
        llm_stats = await llm_call_handler.get_system_stats()
        llm_status = "healthy"
    except Exception as e:
        llm_stats = {}
        llm_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "healthy" and llm_status == "healthy" else "degraded",
        "timestamp": time.time(),
        "version": settings.app_version,
        "services": {
            "database": db_status,
            "llm_handler": llm_status
        },
        "llm_stats": llm_stats,
        "config": {
            "debug": settings.debug,
            "openai_model": settings.openai_model,
            "cors_origins": settings.cors_origins
        }
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to 2id8 Backend API",
        "version": settings.app_version,
        "docs_url": "/docs" if settings.debug else "Documentation not available in production",
        "endpoints": {
            "health": "/health",
            "detailed_health": "/health/detailed",
            "api_v1": "/api/v1"
        }
    }


# API information endpoint
@app.get("/api/v1")
async def api_info():
    """API v1 information and available endpoints."""
    return {
        "version": "1.0",
        "description": "2id8 API v1 - AI-powered idea generation and evaluation",
        "endpoints": {
            "onboarding": {
                "register": "POST /api/v1/onboarding/register",
                "login": "POST /api/v1/onboarding/login",
                "verify_email": "GET /api/v1/onboarding/verify-email/{token}"
            },
            "idea_generation": {
                "generate": "POST /api/v1/idea-generation/generate",
                "iterate": "POST /api/v1/idea-generation/iterate/{idea_id}",
                "batch_generate": "GET /api/v1/idea-generation/batch-generate"
            },
            "evaluation": {
                "evaluate": "POST /api/v1/evaluation/evaluate/{idea_id}",
                "compare": "POST /api/v1/evaluation/compare",
                "update_evaluation": "PUT /api/v1/evaluation/update-evaluation/{idea_id}",
                "batch_evaluate": "GET /api/v1/evaluation/batch-evaluate"
            },
            "iteration": {
                "refine": "POST /api/v1/iteration/refine/{idea_id}",
                "apply_refinement": "POST /api/v1/iteration/apply-refinement/{idea_id}",
                "history": "GET /api/v1/iteration/history/{idea_id}",
                "revert": "POST /api/v1/iteration/revert/{idea_id}/{iteration_id}",
                "branch": "POST /api/v1/iteration/branch/{idea_id}"
            },
            "feedback": {
                "create": "POST /api/v1/feedback/create",
                "get_idea_feedback": "GET /api/v1/feedback/idea/{idea_id}",
                "summary": "GET /api/v1/feedback/summary/{idea_id}",
                "update": "PUT /api/v1/feedback/update/{feedback_id}",
                "delete": "DELETE /api/v1/feedback/delete/{feedback_id}"
            },
            "llm_logs": {
                "list": "GET /api/v1/llm-logs/",
                "detail": "GET /api/v1/llm-logs/{log_id}",
                "idea_logs": "GET /api/v1/llm-logs/idea/{idea_id}",
                "usage_analytics": "GET /api/v1/llm-logs/analytics/usage",
                "cost_analytics": "GET /api/v1/llm-logs/analytics/costs",
                "delete": "DELETE /api/v1/llm-logs/{log_id}"
            }
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )