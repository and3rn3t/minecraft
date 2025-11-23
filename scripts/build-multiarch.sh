#!/bin/bash
# Multi-Architecture Docker Build Script
# Builds Docker images for multiple architectures (ARM64, ARM32, x86_64)

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

# Build configuration
IMAGE_NAME="${IMAGE_NAME:-minecraft-server}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
MINECRAFT_VERSION="${MINECRAFT_VERSION:-1.20.4}"

# Supported architectures
ARCHITECTURES="${ARCHITECTURES:-linux/arm64,linux/arm/v7,linux/amd64}"

# Function to print header
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

# Function to check if buildx is available
check_buildx() {
    if ! docker buildx version >/dev/null 2>&1; then
        echo -e "${RED}Error: Docker Buildx is not available${NC}"
        echo "Install Docker Buildx or update Docker to a version that includes it"
        exit 1
    fi
}

# Function to create buildx builder
setup_builder() {
    local builder_name="multiarch-builder"

    if docker buildx ls | grep -q "$builder_name"; then
        echo -e "${YELLOW}Builder '$builder_name' already exists${NC}"
        docker buildx use "$builder_name"
    else
        echo -e "${BLUE}Creating buildx builder: $builder_name${NC}"
        docker buildx create --name "$builder_name" --use --bootstrap
    fi
}

# Function to build for all architectures
build_all() {
    print_header "Building Multi-Architecture Image"

    check_buildx
    setup_builder

    echo -e "${BLUE}Building for architectures: ${ARCHITECTURES}${NC}"
    echo -e "${BLUE}Image: ${IMAGE_NAME}:${IMAGE_TAG}${NC}"
    echo -e "${BLUE}Minecraft Version: ${MINECRAFT_VERSION}${NC}"
    echo ""

    cd "$PROJECT_DIR"

    # Note: For ARM64, use arm64v8/openjdk base image
    # For ARM32, use arm32v7/openjdk base image
    # For AMD64, use openjdk base image
    # Docker buildx will handle architecture selection automatically

    docker buildx build \
        --platform "$ARCHITECTURES" \
        --build-arg MINECRAFT_VERSION="$MINECRAFT_VERSION" \
        --tag "${IMAGE_NAME}:${IMAGE_TAG}" \
        --tag "${IMAGE_NAME}:${MINECRAFT_VERSION}" \
        --push \
        --progress=plain \
        .

    echo ""
    echo -e "${GREEN}Multi-architecture build complete!${NC}"
    echo ""
    echo "To verify, inspect the manifest:"
    echo "  docker buildx imagetools inspect ${IMAGE_NAME}:${IMAGE_TAG}"
}

# Function to build for specific architecture
build_arch() {
    local arch="$1"

    if [ -z "$arch" ]; then
        echo -e "${RED}Error: Architecture not specified${NC}"
        echo "Usage: $0 arch <architecture>"
        echo "Supported: arm64, arm32, amd64"
        exit 1
    fi

    # Map architecture names to platform strings
    case "$arch" in
        arm64|aarch64)
            local platform="linux/arm64"
            ;;
        arm32|armv7|arm)
            local platform="linux/arm/v7"
            ;;
        amd64|x86_64)
            local platform="linux/amd64"
            ;;
        *)
            echo -e "${RED}Error: Unknown architecture: $arch${NC}"
            echo "Supported: arm64, arm32, amd64"
            exit 1
            ;;
    esac

    print_header "Building for $arch ($platform)"

    check_buildx
    setup_builder

    cd "$PROJECT_DIR"

    docker buildx build \
        --platform "$platform" \
        --build-arg MINECRAFT_VERSION="$MINECRAFT_VERSION" \
        --tag "${IMAGE_NAME}:${IMAGE_TAG}-${arch}" \
        --load \
        --progress=plain \
        .

    echo ""
    echo -e "${GREEN}Build complete for $arch!${NC}"
    echo "Image: ${IMAGE_NAME}:${IMAGE_TAG}-${arch}"
}

# Function to list supported architectures
list_architectures() {
    print_header "Supported Architectures"

    echo "The following architectures are supported:"
    echo ""
    echo "  arm64 (linux/arm64)"
    echo "    - Raspberry Pi 5 (64-bit)"
    echo "    - Apple Silicon (M1/M2/M3)"
    echo "    - AWS Graviton"
    echo ""
    echo "  arm32 (linux/arm/v7)"
    echo "    - Raspberry Pi 4 and earlier (32-bit)"
    echo "    - Older ARM devices"
    echo ""
    echo "  amd64 (linux/amd64)"
    echo "    - Intel/AMD x86_64 processors"
    echo "    - Most desktop and server systems"
    echo ""
}

# Function to create architecture-specific Dockerfiles
create_arch_dockerfiles() {
    print_header "Creating Architecture-Specific Dockerfiles"

    cd "$PROJECT_DIR"

    # ARM64 Dockerfile (Raspberry Pi 5)
    cat > Dockerfile.arm64 <<'EOF'
# ARM64 (Raspberry Pi 5, Apple Silicon)
FROM arm64v8/openjdk:21-jdk-slim AS base

# ... rest of Dockerfile content ...
EOF

    # ARM32 Dockerfile (Raspberry Pi 4 and earlier)
    cat > Dockerfile.arm32 <<'EOF'
# ARM32 (Raspberry Pi 4 and earlier)
FROM arm32v7/openjdk:21-jdk-slim AS base

# ... rest of Dockerfile content ...
EOF

    # AMD64 Dockerfile (x86_64)
    cat > Dockerfile.amd64 <<'EOF'
# AMD64 (Intel/AMD x86_64)
FROM openjdk:21-jdk-slim AS base

# ... rest of Dockerfile content ...
EOF

    echo -e "${GREEN}Architecture-specific Dockerfiles created${NC}"
    echo ""
    echo "Note: These are templates. Update them with the full Dockerfile content."
}

# Main function
main() {
    local command="${1:-help}"

    case "$command" in
        all)
            build_all
            ;;
        arch)
            build_arch "$2"
            ;;
        list)
            list_architectures
            ;;
        setup)
            check_buildx
            setup_builder
            echo -e "${GREEN}Buildx builder setup complete!${NC}"
            ;;
        create-dockerfiles)
            create_arch_dockerfiles
            ;;
        help|*)
            echo -e "${BLUE}Multi-Architecture Docker Build Script${NC}"
            echo ""
            echo "Usage: $0 {all|arch|list|setup|create-dockerfiles|help}"
            echo ""
            echo "Commands:"
            echo "  all                - Build for all architectures and push to registry"
            echo "  arch <architecture> - Build for specific architecture (arm64|arm32|amd64)"
            echo "  list               - List supported architectures"
            echo "  setup              - Setup buildx builder"
            echo "  create-dockerfiles - Create architecture-specific Dockerfile templates"
            echo "  help               - Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  IMAGE_NAME=${IMAGE_NAME} - Docker image name"
            echo "  IMAGE_TAG=${IMAGE_TAG} - Docker image tag"
            echo "  MINECRAFT_VERSION=${MINECRAFT_VERSION} - Minecraft version"
            echo "  ARCHITECTURES=${ARCHITECTURES} - Comma-separated list of platforms"
            echo ""
            echo "Examples:"
            echo "  $0 all                    # Build for all architectures"
            echo "  $0 arch arm64             # Build for ARM64 only"
            echo "  $0 arch amd64             # Build for x86_64 only"
            echo "  IMAGE_TAG=1.21.0 $0 all   # Build with custom tag"
            echo ""
            exit 1
            ;;
    esac
}

# Run main function
main "$@"

