#!/bin/bash
# Universal Server Download Script
# Downloads server jars for different server types (Vanilla, Paper, Spigot, Fabric)

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

# Default values
SERVER_TYPE=${SERVER_TYPE:-vanilla}
MINECRAFT_VERSION=${MINECRAFT_VERSION:-1.20.4}
DOWNLOAD_DIR="${PROJECT_DIR}/data"
TEMP_DIR="${PROJECT_DIR}/.tmp"

# Function to get vanilla server download URL
get_vanilla_url() {
    local version="$1"
    local api_url="https://launchermeta.mojang.com/mc/game/version_manifest.json"
    local manifest=$(curl -s "$api_url" 2>/dev/null)

    if [ -z "$manifest" ]; then
        echo "ERROR: Failed to fetch version manifest" >&2
        return 1
    fi

    # Find version entry
    local version_url=$(echo "$manifest" | grep -oP "\"id\"\s*:\s*\"$version\"[^}]*\"url\"\s*:\s*\"\K[^\"]+" | head -1)

    if [ -z "$version_url" ]; then
        echo "ERROR: Version $version not found" >&2
        return 1
    fi

    # Get version details
    local version_details=$(curl -s "$version_url" 2>/dev/null)

    if [ -z "$version_details" ]; then
        echo "ERROR: Failed to fetch version details" >&2
        return 1
    fi

    # Extract server jar URL
    local server_url=$(echo "$version_details" | grep -oP '"server"\s*:\s*\{[^}]*"url"\s*:\s*"\K[^"]+' | head -1)
    echo "$server_url"
}

# Function to get Paper server download URL
get_paper_url() {
    local version="$1"
    # Paper API: https://api.papermc.io/v2/projects/paper/versions/{version}/builds/{build}/downloads/paper-{version}-{build}.jar
    # First, get latest build for version
    local api_url="https://api.papermc.io/v2/projects/paper/versions/$version"
    local version_info=$(curl -s "$api_url" 2>/dev/null)

    if [ -z "$version_info" ]; then
        echo "ERROR: Failed to fetch Paper version info" >&2
        return 1
    fi

    # Get latest build number
    local build=$(echo "$version_info" | grep -oP '"builds"\s*:\s*\[[^\]]*' | grep -oP '\d+' | tail -1)

    if [ -z "$build" ]; then
        echo "ERROR: No builds found for Paper version $version" >&2
        return 1
    fi

    # Construct download URL
    local download_url="https://api.papermc.io/v2/projects/paper/versions/$version/builds/$build/downloads/paper-$version-$build.jar"
    echo "$download_url"
}

# Function to get Spigot download URL (requires BuildTools)
get_spigot_url() {
    local version="$1"
    # Spigot doesn't have a direct download API, requires BuildTools
    # For now, return a note that BuildTools is needed
    echo "BUILDTOOLS_REQUIRED"
}

# Function to get Fabric installer URL
get_fabric_url() {
    local version="$1"
    # Fabric uses an installer that downloads the server
    # Get installer version
    local installer_api="https://meta.fabricmc.net/v2/versions/installer"
    local installer_info=$(curl -s "$installer_api" 2>/dev/null)

    if [ -z "$installer_info" ]; then
        echo "ERROR: Failed to fetch Fabric installer info" >&2
        return 1
    fi

    # Get latest installer version
    local installer_version=$(echo "$installer_info" | grep -oP '"version"\s*:\s*"\K[^"]+' | head -1)

    # Fabric installer URL
    local installer_url="https://maven.fabricmc.net/net/fabricmc/fabric-installer/$installer_version/fabric-installer-$installer_version.jar"
    echo "$installer_url|$version"
}

# Function to download file with verification
download_file() {
    local url="$1"
    local output="$2"
    local expected_size="${3:-0}"

    echo -e "${BLUE}Downloading from: $url${NC}"

    # Create temp directory
    mkdir -p "$TEMP_DIR"

    # Download with wget or curl
    if command -v wget >/dev/null 2>&1; then
        wget --progress=bar:force -O "$output" "$url" 2>&1 || {
            echo -e "${RED}Download failed${NC}"
            return 1
        }
    elif command -v curl >/dev/null 2>&1; then
        curl -L -o "$output" "$url" || {
            echo -e "${RED}Download failed${NC}"
            return 1
        }
    else
        echo -e "${RED}Neither wget nor curl is available${NC}"
        return 1
    fi

    # Verify file exists and has content
    if [ ! -f "$output" ] || [ ! -s "$output" ]; then
        echo -e "${RED}Downloaded file is empty or missing${NC}"
        return 1
    fi

    echo -e "${GREEN}Download complete${NC}"
    return 0
}

# Function to download vanilla server
download_vanilla() {
    local version="$1"
    local output_file="$2"

    echo -e "${BLUE}Downloading Vanilla Minecraft server $version...${NC}"

    local url=$(get_vanilla_url "$version")
    if [ $? -ne 0 ] || [ -z "$url" ]; then
        echo -e "${RED}Failed to get download URL for version $version${NC}"
        return 1
    fi

    download_file "$url" "$output_file"
}

# Function to download Paper server
download_paper() {
    local version="$1"
    local output_file="$2"

    echo -e "${BLUE}Downloading Paper server $version...${NC}"

    local url=$(get_paper_url "$version")
    if [ $? -ne 0 ] || [ -z "$url" ]; then
        echo -e "${RED}Failed to get download URL for Paper version $version${NC}"
        return 1
    fi

    download_file "$url" "$output_file"
}

# Function to download Fabric server
download_fabric() {
    local version="$1"
    local output_file="$2"

    echo -e "${BLUE}Downloading Fabric server $version...${NC}"

    local fabric_info=$(get_fabric_url "$version")
    if [ $? -ne 0 ] || [ -z "$fabric_info" ]; then
        echo -e "${RED}Failed to get Fabric installer URL${NC}"
        return 1
    fi

    local installer_url=$(echo "$fabric_info" | cut -d'|' -f1)
    local mc_version=$(echo "$fabric_info" | cut -d'|' -f2)

    # Download installer
    local installer_jar="${TEMP_DIR}/fabric-installer.jar"
    download_file "$installer_url" "$installer_jar"

    if [ $? -ne 0 ]; then
        return 1
    fi

    # Run installer
    echo -e "${BLUE}Running Fabric installer...${NC}"
    mkdir -p "$DOWNLOAD_DIR"
    cd "$DOWNLOAD_DIR"

    java -jar "$installer_jar" server -mcversion "$mc_version" -downloadMinecraft || {
        echo -e "${RED}Fabric installer failed${NC}"
        return 1
    }

    # Find the generated server jar
    local fabric_jar=$(find "$DOWNLOAD_DIR" -name "fabric-server-launch.jar" -o -name "server.jar" | head -1)
    if [ -n "$fabric_jar" ] && [ "$fabric_jar" != "$output_file" ]; then
        mv "$fabric_jar" "$output_file"
    fi

    echo -e "${GREEN}Fabric server downloaded${NC}"
}

# Main function
main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --type)
                SERVER_TYPE="$2"
                shift 2
                ;;
            --version)
                MINECRAFT_VERSION="$2"
                shift 2
                ;;
            --output)
                DOWNLOAD_DIR="$2"
                shift 2
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Determine output filename
    case "$SERVER_TYPE" in
        vanilla)
            OUTPUT_FILE="${DOWNLOAD_DIR}/server.jar"
            download_vanilla "$MINECRAFT_VERSION" "$OUTPUT_FILE"
            ;;
        paper)
            OUTPUT_FILE="${DOWNLOAD_DIR}/paper-${MINECRAFT_VERSION}.jar"
            download_paper "$MINECRAFT_VERSION" "$OUTPUT_FILE"
            ;;
        spigot)
            echo -e "${YELLOW}Spigot requires BuildTools. Use BuildTools to build Spigot.${NC}"
            echo -e "${YELLOW}See: https://www.spigotmc.org/wiki/buildtools/${NC}"
            exit 1
            ;;
        fabric)
            OUTPUT_FILE="${DOWNLOAD_DIR}/fabric-server.jar"
            download_fabric "$MINECRAFT_VERSION" "$OUTPUT_FILE"
            ;;
        *)
            echo -e "${RED}Unknown server type: $SERVER_TYPE${NC}"
            echo -e "${YELLOW}Supported types: vanilla, paper, fabric${NC}"
            exit 1
            ;;
    esac

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Server jar downloaded: $OUTPUT_FILE${NC}"
        # Set executable permission
        chmod +x "$OUTPUT_FILE" 2>/dev/null || true
    else
        echo -e "${RED}Failed to download server${NC}"
        exit 1
    fi
}

# Run main function
main "$@"

