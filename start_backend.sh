#!/bin/bash
echo "🚀 Starting FlipHero Backend on port 8001..."
source .env.development
python3 -m uvicorn src.main:app --reload --host $HOST --port 8001
