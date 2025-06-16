#!/usr/bin/env python3
"""
FastAPI Server Entry Point
Handles proper module imports and server startup for the trading cards automation MVP.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path for proper imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """Main server startup function"""
    try:
        # Import the FastAPI app from src
        from src.main import app
        
        print("🚀 Starting FlipHero API Server...")
        print("📍 Server will be available at: http://localhost:8000")
        print("📖 API Documentation at: http://localhost:8000/docs")
        print("🔄 Press Ctrl+C to stop the server")
        
        # Start the server
        import uvicorn
        uvicorn.run(
            "src.main:app", 
            host="0.0.0.0", 
            port=8000,
            reload=True,  # Enable auto-reload for development
            log_level="info"
        )
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("💡 Make sure all dependencies are installed: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Server startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 