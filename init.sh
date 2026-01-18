#!/bin/bash

# =============================================================================
# Elevate CRM - Development Environment Setup Script
# =============================================================================
# This script sets up and starts the development environment for Elevate CRM.
#
# Prerequisites:
#   - Node.js 20+ (https://nodejs.org/)
#   - Python 3.10+ (https://www.python.org/)
#   - npm or yarn
#
# Usage:
#   ./init.sh           # Full setup and start
#   ./init.sh --backend # Start backend only
#   ./init.sh --frontend # Start frontend only
#   ./init.sh --install # Install dependencies only
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  Elevate CRM - Development Setup${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"

    # Check Node.js
    if ! command -v node &> /dev/null; then
        echo -e "${RED}Error: Node.js is not installed. Please install Node.js 20+${NC}"
        exit 1
    fi
    NODE_VERSION=$(node -v | sed 's/v//' | cut -d. -f1)
    if [ "$NODE_VERSION" -lt 18 ]; then
        echo -e "${RED}Error: Node.js version 18+ required. Found: $(node -v)${NC}"
        exit 1
    fi
    echo -e "${GREEN}  ✓ Node.js $(node -v)${NC}"

    # Check npm or yarn
    if command -v yarn &> /dev/null; then
        PACKAGE_MANAGER="yarn"
        echo -e "${GREEN}  ✓ Yarn $(yarn -v)${NC}"
    elif command -v npm &> /dev/null; then
        PACKAGE_MANAGER="npm"
        echo -e "${GREEN}  ✓ npm $(npm -v)${NC}"
    else
        echo -e "${RED}Error: npm or yarn is required${NC}"
        exit 1
    fi

    # Check Python
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo -e "${RED}Error: Python 3.10+ is required${NC}"
        exit 1
    fi
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | sed 's/Python //' | cut -d. -f1,2)
    echo -e "${GREEN}  ✓ Python $PYTHON_VERSION${NC}"

    echo ""
}

# Install backend dependencies
install_backend() {
    echo -e "${YELLOW}Setting up backend...${NC}"
    cd "$PROJECT_ROOT/backend"

    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        echo "  Creating Python virtual environment..."
        $PYTHON_CMD -m venv venv
    fi

    # Activate virtual environment and install dependencies
    echo "  Installing Python dependencies..."
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        # Windows
        source venv/Scripts/activate
    else
        # Unix/Linux/Mac
        source venv/bin/activate
    fi

    pip install -q --upgrade pip
    pip install -q -r requirements.txt

    # Create .env file if it doesn't exist
    if [ ! -f ".env" ]; then
        echo "  Creating backend .env file..."
        cat > .env << 'EOF'
# Elevate CRM Backend Configuration
DATABASE_URL=sqlite:///./elevatecrm.db
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# OpenAI API (for AI features)
OPENAI_API_KEY=your-openai-api-key

# Stripe (for payments)
STRIPE_SECRET_KEY=your-stripe-secret-key
STRIPE_WEBHOOK_SECRET=your-stripe-webhook-secret

# Twilio (for SMS)
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=your-twilio-phone-number

# SendGrid (for email)
SENDGRID_API_KEY=your-sendgrid-api-key

# Server settings
HOST=0.0.0.0
PORT=8000
DEBUG=true
EOF
    fi

    echo -e "${GREEN}  ✓ Backend setup complete${NC}"
    cd "$PROJECT_ROOT"
    echo ""
}

# Install frontend dependencies
install_frontend() {
    echo -e "${YELLOW}Setting up frontend...${NC}"
    cd "$PROJECT_ROOT/frontend"

    # Install dependencies
    echo "  Installing frontend dependencies..."
    if [ "$PACKAGE_MANAGER" == "yarn" ]; then
        yarn install --silent
    else
        npm install --silent
    fi

    # Create .env file if it doesn't exist
    if [ ! -f ".env" ]; then
        echo "  Creating frontend .env file..."
        cat > .env << 'EOF'
# Elevate CRM Frontend Configuration
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000/ws
EOF
    fi

    echo -e "${GREEN}  ✓ Frontend setup complete${NC}"
    cd "$PROJECT_ROOT"
    echo ""
}

# Start backend server
start_backend() {
    echo -e "${YELLOW}Starting backend server...${NC}"
    cd "$PROJECT_ROOT/backend"

    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        source venv/Scripts/activate
    else
        source venv/bin/activate
    fi

    echo -e "${GREEN}  Backend starting on http://localhost:8000${NC}"
    echo -e "${GREEN}  API docs available at http://localhost:8000/docs${NC}"
    $PYTHON_CMD server.py &
    BACKEND_PID=$!
    cd "$PROJECT_ROOT"
}

# Start frontend server
start_frontend() {
    echo -e "${YELLOW}Starting frontend server...${NC}"
    cd "$PROJECT_ROOT/frontend"

    echo -e "${GREEN}  Frontend starting on http://localhost:3000${NC}"
    if [ "$PACKAGE_MANAGER" == "yarn" ]; then
        yarn start &
    else
        npm start &
    fi
    FRONTEND_PID=$!
    cd "$PROJECT_ROOT"
}

# Cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down servers...${NC}"
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    echo -e "${GREEN}Done.${NC}"
}

# Main execution
main() {
    trap cleanup EXIT INT TERM

    case "${1:-}" in
        --backend)
            check_prerequisites
            install_backend
            start_backend
            wait
            ;;
        --frontend)
            check_prerequisites
            install_frontend
            start_frontend
            wait
            ;;
        --install)
            check_prerequisites
            install_backend
            install_frontend
            echo -e "${GREEN}============================================${NC}"
            echo -e "${GREEN}  Installation complete!${NC}"
            echo -e "${GREEN}============================================${NC}"
            echo ""
            echo "To start the development servers, run:"
            echo "  ./init.sh"
            ;;
        *)
            check_prerequisites
            install_backend
            install_frontend

            echo -e "${BLUE}============================================${NC}"
            echo -e "${BLUE}  Starting Elevate CRM...${NC}"
            echo -e "${BLUE}============================================${NC}"
            echo ""

            start_backend
            sleep 3  # Wait for backend to start
            start_frontend

            echo ""
            echo -e "${GREEN}============================================${NC}"
            echo -e "${GREEN}  Elevate CRM is running!${NC}"
            echo -e "${GREEN}============================================${NC}"
            echo ""
            echo "  Frontend:  http://localhost:3000"
            echo "  Backend:   http://localhost:8000"
            echo "  API Docs:  http://localhost:8000/docs"
            echo ""
            echo "Press Ctrl+C to stop all servers."
            echo ""

            wait
            ;;
    esac
}

main "$@"
