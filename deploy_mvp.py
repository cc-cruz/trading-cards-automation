#!/usr/bin/env python3
"""
MVP Deployment Script for FlipHero
Starts both backend and frontend for user onboarding.
"""

import subprocess
import time
import sys
import os
import signal
from pathlib import Path

def check_port(port):
    """Check if a port is available"""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result != 0  # Port is available if connection failed
    except:
        return True

def start_backend(port=8001):
    """Start the FastAPI backend"""
    print(f"🚀 Starting backend on port {port}...")
    
    if not check_port(port):
        print(f"⚠️  Port {port} is busy, trying {port+1}")
        port += 1
    
    try:
        proc = subprocess.Popen([
            sys.executable, "-m", "uvicorn", 
            "src.main:app", 
            "--reload", 
            "--host", "0.0.0.0", 
            "--port", str(port)
        ])
        
        # Give it time to start
        time.sleep(3)
        
        # Check if it's running
        if proc.poll() is None:
            print(f"✅ Backend running on http://localhost:{port}")
            print(f"📚 API Docs: http://localhost:{port}/docs")
            return proc, port
        else:
            print("❌ Backend failed to start")
            return None, None
            
    except Exception as e:
        print(f"❌ Error starting backend: {e}")
        return None, None

def start_frontend(port=3000):
    """Start the Next.js frontend"""
    print(f"🎨 Starting frontend on port {port}...")
    
    # Check if package.json exists
    if not Path("package.json").exists():
        print("⚠️  No package.json found, skipping frontend")
        return None, None
    
    if not check_port(port):
        print(f"⚠️  Port {port} is busy, trying {port+1}")
        port += 1
    
    try:
        # First install dependencies if needed
        if not Path("node_modules").exists():
            print("📦 Installing frontend dependencies...")
            npm_install = subprocess.run(["npm", "install"], capture_output=True, text=True)
            if npm_install.returncode != 0:
                print(f"❌ npm install failed: {npm_install.stderr}")
                return None, None
        
        # Start development server
        proc = subprocess.Popen([
            "npm", "run", "dev", "--", "--port", str(port)
        ], env=dict(os.environ, PORT=str(port)))
        
        # Give it time to start
        time.sleep(5)
        
        # Check if it's running
        if proc.poll() is None:
            print(f"✅ Frontend running on http://localhost:{port}")
            return proc, port
        else:
            print("❌ Frontend failed to start")
            return None, None
            
    except FileNotFoundError:
        print("⚠️  npm not found, skipping frontend")
        return None, None
    except Exception as e:
        print(f"❌ Error starting frontend: {e}")
        return None, None

def print_user_instructions(backend_port, frontend_port=None):
    """Print instructions for users"""
    print("\n" + "="*50)
    print("🎉 FLIPHERO MVP READY FOR USERS")
    print("="*50)
    
    if frontend_port:
        print(f"🌐 Main App: http://localhost:{frontend_port}")
    
    print(f"🔧 API Backend: http://localhost:{backend_port}")
    print(f"📚 API Docs: http://localhost:{backend_port}/docs")
    
    print("\n📋 User Onboarding Checklist:")
    print("1. Open the main app URL above")
    print("2. Create an account / login")
    print("3. Create a collection called 'My Cards'")
    print("4. Upload a card image") 
    print("5. Review extracted details (edit if needed)")
    print("6. Export CSV for eBay")
    
    print("\n⚠️  Known Issues:")
    print("- OCR sometimes captures too much in 'set' field")
    print("- Users should review all fields before export")
    print("- Card numbers occasionally missed")
    
    print("\n🛠️  Support Commands:")
    print("- Check logs: tail -f logs/*.log")
    print("- Restart backend: Ctrl+C then rerun this script")
    print("- View database: sqlite3 carddealer.db")
    
    print("\n🚀 Ready for your first 3 users!")

def cleanup_handler(backend_proc, frontend_proc):
    """Clean shutdown handler"""
    def signal_handler(sig, frame):
        print("\n🛑 Shutting down FlipHero...")
        
        if backend_proc and backend_proc.poll() is None:
            print("⏹️  Stopping backend...")
            backend_proc.terminate()
            
        if frontend_proc and frontend_proc.poll() is None:
            print("⏹️  Stopping frontend...")
            frontend_proc.terminate()
            
        print("✅ Shutdown complete")
        sys.exit(0)
    
    return signal_handler

def main():
    """Deploy the MVP"""
    print("🃏 FlipHero MVP Deployment")
    print("="*50)
    
    # Run quick test first
    print("🔍 Running pre-deployment check...")
    test_result = subprocess.run([sys.executable, "quick_test.py"], capture_output=True)
    
    if test_result.returncode != 0:
        print("❌ Pre-deployment check failed!")
        print("Run 'python quick_test.py' to debug")
        return False
    
    print("✅ Pre-deployment check passed")
    
    # Start services
    backend_proc, backend_port = start_backend()
    if not backend_proc:
        print("❌ Cannot proceed without backend")
        return False
    
    frontend_proc, frontend_port = start_frontend()
    
    # Setup signal handlers for clean shutdown
    signal.signal(signal.SIGINT, cleanup_handler(backend_proc, frontend_proc))
    signal.signal(signal.SIGTERM, cleanup_handler(backend_proc, frontend_proc))
    
    # Show user instructions
    print_user_instructions(backend_port, frontend_port)
    
    # Keep running
    try:
        while True:
            time.sleep(1)
            
            # Check if backend died
            if backend_proc.poll() is not None:
                print("❌ Backend stopped unexpectedly")
                break
                
            # Check if frontend died (but don't fail if no frontend)
            if frontend_proc and frontend_proc.poll() is not None:
                print("⚠️  Frontend stopped unexpectedly")
                frontend_proc = None
                
    except KeyboardInterrupt:
        cleanup_handler(backend_proc, frontend_proc)(None, None)
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 