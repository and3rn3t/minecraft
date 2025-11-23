#!/bin/bash
# Fix Image File Size Alignment
# This script ensures a disk image file size is a multiple of 512 bytes
# Required for proper block device operations when writing to SD cards
#
# Usage: ./fix-image-alignment.sh <image-file> [output-file]
#   If output-file is not specified, the original file will be modified in-place

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Block size (512 bytes is standard for block devices)
BLOCK_SIZE=512

# Function to print usage
usage() {
    echo -e "${BLUE}Usage:${NC} $0 <image-file> [output-file]"
    echo ""
    echo "  image-file   : Path to the disk image file to fix"
    echo "  output-file  : Optional output file path (default: modifies in-place)"
    echo ""
    echo "Examples:"
    echo "  $0 raspberry-pi.img"
    echo "  $0 raspberry-pi.img raspberry-pi-fixed.img"
    exit 1
}

# Function to check if a number is a multiple of another
is_multiple_of() {
    local num=$1
    local divisor=$2
    if [ $((num % divisor)) -eq 0 ]; then
        return 0
    else
        return 1
    fi
}

# Function to round up to nearest multiple
round_up_to_multiple() {
    local num=$1
    local divisor=$2
    echo $((((num + divisor - 1) / divisor) * divisor))
}

# Main function
main() {
    # Check arguments
    if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
        usage
    fi

    local input_file="$1"
    local output_file="${2:-$input_file}"

    # Check if input file exists
    if [ ! -f "$input_file" ]; then
        echo -e "${RED}Error: Input file not found: $input_file${NC}"
        exit 1
    fi

    # Get current file size
    local current_size
    current_size=$(stat -f%z "$input_file" 2>/dev/null || stat -c%s "$input_file" 2>/dev/null)

    if [ -z "$current_size" ]; then
        echo -e "${RED}Error: Could not determine file size${NC}"
        exit 1
    fi

    echo -e "${BLUE}Checking image alignment: $input_file${NC}"
    echo -e "${BLUE}Current file size: $current_size bytes${NC}"

    # Check if already aligned
    if is_multiple_of "$current_size" "$BLOCK_SIZE"; then
        echo -e "${GREEN}File size is already a multiple of $BLOCK_SIZE bytes${NC}"

        # If output is different from input, copy the file
        if [ "$input_file" != "$output_file" ]; then
            echo -e "${BLUE}Copying to: $output_file${NC}"
            cp "$input_file" "$output_file"
            echo -e "${GREEN}File copied successfully${NC}"
        fi

        exit 0
    fi

    # Calculate required size
    local required_size
    required_size=$(round_up_to_multiple "$current_size" "$BLOCK_SIZE")
    local padding_needed
    padding_needed=$((required_size - current_size))

    echo -e "${YELLOW}File size is not a multiple of $BLOCK_SIZE bytes${NC}"
    echo -e "${BLUE}Required size: $required_size bytes${NC}"
    echo -e "${BLUE}Padding needed: $padding_needed bytes${NC}"

    # Create output file
    if [ "$input_file" == "$output_file" ]; then
        echo -e "${BLUE}Modifying file in-place...${NC}"
        # Append padding zeros to the file
        dd if=/dev/zero bs=1 count="$padding_needed" >> "$input_file" 2>/dev/null
        echo -e "${GREEN}File aligned successfully${NC}"
    else
        echo -e "${BLUE}Creating aligned copy: $output_file${NC}"
        # Copy original file
        cp "$input_file" "$output_file"
        # Append padding zeros
        dd if=/dev/zero bs=1 count="$padding_needed" >> "$output_file" 2>/dev/null
        echo -e "${GREEN}Aligned file created successfully${NC}"
    fi

    # Verify the result
    local final_size
    final_size=$(stat -f%z "$output_file" 2>/dev/null || stat -c%s "$output_file" 2>/dev/null)

    if is_multiple_of "$final_size" "$BLOCK_SIZE"; then
        echo -e "${GREEN}Verification: File size is now $final_size bytes (multiple of $BLOCK_SIZE)${NC}"
    else
        echo -e "${RED}Error: Verification failed - file size is still not aligned${NC}"
        exit 1
    fi

    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Image alignment complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${BLUE}Original size: $current_size bytes${NC}"
    echo -e "${BLUE}Final size:    $final_size bytes${NC}"
    echo -e "${BLUE}Padding added:  $padding_needed bytes${NC}"
    echo ""
}

# Run main function
main "$@"

