#!/bin/bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}==================================${NC}"
echo -e "${GREEN}AI Document Processor${NC}"
echo -e "${GREEN}==================================${NC}"
echo ""

# Create virtual environment if doesn't exist
if [ ! -d "entry-env" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv entry-env
fi

echo -e "${YELLOW}Activating virtual environment...${NC}"
source entry-env/bin/activate

# Check .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}.env file not found!${NC}"
    echo -e "${YELLOW}Creating template .env file...${NC}"
    cat > .env << 'EOF'
OPENAI_API_KEY=your-key-here
DATABASE_URL=sqlite+aiosqlite:///./data/document_processor.db
UPLOAD_DIR=./data/uploads
PROCESSED_DIR=./data/processed
EXPORT_DIR=./data/exports
EOF
    echo -e "${RED}Please edit .env and add your OpenAI API key!${NC}"
    exit 1
fi

# Install/update dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -q -r requirements.txt
pip install -q aiosqlite  # Ensure async sqlite is installed

# Create directories
echo -e "${YELLOW}Creating directories...${NC}"
mkdir -p data/uploads data/processed data/exports logs backend/logs

# Copy .env to backend if needed
cp .env backend/.env 2>/dev/null || true

# Start backend
echo -e "${GREEN}Starting backend server...${NC}"
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
cd ..

echo $BACKEND_PID > .backend.pid
sleep 3

if ps -p $BACKEND_PID > /dev/null; then
    echo -e "${GREEN}✓ Backend started (PID: $BACKEND_PID)${NC}"
else
    echo -e "${RED}✗ Backend failed to start${NC}"
    echo -e "${YELLOW}Check logs:${NC}"
    tail -20 logs/backend.log
    exit 1
fi

# Start frontend
echo -e "${GREEN}Starting frontend server...${NC}"
cd frontend
python3 -m http.server 3000 > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

echo $FRONTEND_PID > .frontend.pid
sleep 2

if ps -p $FRONTEND_PID > /dev/null; then
    echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID)${NC}"
else
    echo -e "${RED}✗ Frontend failed${NC}"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

echo ""
echo -e "${GREEN}==================================${NC}"
echo -e "${GREEN}Application Started!${NC}"
echo -e "${GREEN}==================================${NC}"
echo ""
echo -e "Frontend: ${GREEN}http://localhost:3000${NC}"
echo -e "Backend:  ${GREEN}http://localhost:8000${NC}"
echo -e "API Docs: ${GREEN}http://localhost:8000/docs${NC}"
echo ""
echo -e "Stop with: ${YELLOW}./stop.sh${NC}"
echo ""
