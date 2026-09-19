#!/bin/bash
# Serve API Documentation
# Starts a local server to view OpenAPI/Swagger documentation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
OPENAPI_FILE="${PROJECT_DIR}/api/openapi.yaml"
PORT=${PORT:-8081}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to serve with Python
serve_python() {
    if command_exists python3; then
        echo -e "${BLUE}Serving API docs with Python...${NC}"
        cd "$PROJECT_DIR"
        python3 -m http.server "$PORT" &
        SERVER_PID=$!
        echo -e "${GREEN}Server started on http://localhost:${PORT}${NC}"
        echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
        wait $SERVER_PID
    else
        echo -e "${RED}Python 3 not found${NC}"
        return 1
    fi
}

# Function to serve with Swagger UI (if available)
serve_swagger() {
    if command_exists docker; then
        echo -e "${BLUE}Serving API docs with Swagger UI (Docker)...${NC}"
        docker run -d \
            --name swagger-ui \
            -p "$PORT:8080" \
            -e SWAGGER_JSON=/openapi.yaml \
            -v "$OPENAPI_FILE:/openapi.yaml:ro" \
            swaggerapi/swagger-ui
        echo -e "${GREEN}Swagger UI started on http://localhost:${PORT}${NC}"
        echo -e "${YELLOW}Stop with: docker stop swagger-ui && docker rm swagger-ui${NC}"
    else
        echo -e "${YELLOW}Docker not found, using Python server${NC}"
        serve_python
    fi
}

# Function to open in browser
open_browser() {
    local url="$1"
    if command_exists xdg-open; then
        xdg-open "$url"
    elif command_exists open; then
        open "$url"
    elif command_exists start; then
        start "$url"
    fi
}

# Main function
main() {
    if [ ! -f "$OPENAPI_FILE" ]; then
        echo -e "${RED}Error: OpenAPI file not found: $OPENAPI_FILE${NC}"
        exit 1
    fi

    echo -e "${BLUE}API Documentation Server${NC}"
    echo ""
    echo "OpenAPI file: $OPENAPI_FILE"
    echo "Port: $PORT"
    echo ""

    # Try Swagger UI first, fallback to Python
    if command_exists docker; then
        serve_swagger
    else
        echo -e "${YELLOW}Docker not available. Install Docker for Swagger UI, or use online viewer:${NC}"
        echo "https://editor.swagger.io/"
        echo ""
        echo "Or copy openapi.yaml to: https://editor.swagger.io/"
        serve_python
    fi
}

# Run main function
main "$@"

