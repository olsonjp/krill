#!/bin/bash

# Krill Docker Build Script
# Usage: ./build.sh [development|testing|production|all]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to build a specific target
build_target() {
    local target=$1
    local tag="krill:${target}"
    
    print_status "Building ${target} image..."
    docker build --target ${target} -t ${tag} .
    
    if [ $? -eq 0 ]; then
        print_success "Successfully built ${tag}"
    else
        print_error "Failed to build ${tag}"
        exit 1
    fi
}

# Function to run tests in container
run_tests() {
    print_status "Running tests in container..."
    docker run --rm krill:testing
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [development|testing|production|all|test]"
    echo ""
    echo "Targets:"
    echo "  development  - Build development image with debug tools"
    echo "  testing      - Build testing image with test dependencies"
    echo "  production   - Build production image with security optimizations"
    echo "  all          - Build all images"
    echo "  test         - Build testing image and run tests"
    echo ""
    echo "Examples:"
    echo "  $0 development    # Build development image"
    echo "  $0 all           # Build all images"
    echo "  $0 test          # Build and run tests"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Parse command line arguments
case "${1:-all}" in
    development)
        build_target "development"
        print_success "Development image ready. Run with: docker run -p 8000:8000 krill:development"
        ;;
    testing)
        build_target "testing"
        print_success "Testing image ready. Run with: docker run --rm krill:testing"
        ;;
    production)
        build_target "production"
        print_success "Production image ready. Run with: docker run -p 8000:8000 krill:production"
        ;;
    all)
        print_status "Building all images..."
        build_target "development"
        build_target "testing"
        build_target "production"
        print_success "All images built successfully!"
        ;;
    test)
        build_target "testing"
        run_tests
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        print_error "Unknown target: $1"
        show_usage
        exit 1
        ;;
esac

print_status "Build completed successfully!"
