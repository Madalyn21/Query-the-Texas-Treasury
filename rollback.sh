#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status messages
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to list available backups
list_backups() {
    print_status "Available backup versions:"
    docker images texas-treasury-query --format "{{.Tag}}" | grep "^backup-" | sort -r
}

# Function to perform rollback
rollback() {
    local version=$1
    
    if [ -z "$version" ]; then
        print_error "No version specified for rollback"
        print_status "Usage: ./rollback.sh <version>"
        print_status "Run './rollback.sh list' to see available versions"
        exit 1
    fi
    
    if [ "$version" = "list" ]; then
        list_backups
        exit 0
    fi
    
    # Check if specified version exists
    if ! docker images texas-treasury-query:$version --format "{{.Tag}}" | grep -q "^$version$"; then
        print_error "Version $version not found"
        list_backups
        exit 1
    fi
    
    print_status "Starting rollback to version $version..."
    
    # Stop and remove current container if it exists
    if docker ps -q --filter "name=texas-treasury-query" | grep -q .; then
        print_status "Stopping current container..."
        docker stop texas-treasury-query
        docker rm texas-treasury-query
    fi
    
    # Create backup of current version before rollback
    if docker images texas-treasury-query:latest --format "{{.Tag}}" | grep -q "^latest$"; then
        BACKUP_TAG="pre-rollback-$(date +%Y%m%d-%H%M%S)"
        docker tag texas-treasury-query:latest texas-treasury-query:$BACKUP_TAG
        print_status "Current version backed up as texas-treasury-query:$BACKUP_TAG"
    fi
    
    # Tag the rollback version as latest
    docker tag texas-treasury-query:$version texas-treasury-query:latest
    
    # Start container with rolled back version
    print_status "Starting container with rolled back version..."
    docker run -d \
        --name texas-treasury-query \
        -p 8501:8501 \
        --env-file .env \
        --restart unless-stopped \
        texas-treasury-query:latest
    
    if [ $? -ne 0 ]; then
        print_error "Failed to start container with rolled back version"
        exit 1
    fi
    
    # Verify rollback
    print_status "Verifying rollback..."
    sleep 5
    
    # Check if container is running
    if ! docker ps -q --filter "name=texas-treasury-query" | grep -q .; then
        print_error "Container failed to start after rollback"
        exit 1
    fi
    
    # Check health endpoint
    HEALTH_STATUS=$(curl -s "http://localhost:8501/?health=check")
    if echo $HEALTH_STATUS | grep -q '"status":"healthy"'; then
        print_status "Rollback completed successfully!"
        print_status "Application is available at http://localhost:8501"
    else
        print_warning "Health check after rollback returned warnings or errors"
        echo $HEALTH_STATUS
    fi
}

# Main rollback process
main() {
    # Check if docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is required but not installed"
        exit 1
    fi
    
    # Check if .env file exists
    if [ ! -f .env ]; then
        print_error ".env file not found"
        exit 1
    fi
    
    # Process command line argument
    if [ $# -eq 0 ]; then
        print_error "No version specified for rollback"
        print_status "Usage: ./rollback.sh <version>"
        print_status "Run './rollback.sh list' to see available versions"
        exit 1
    fi
    
    rollback "$1"
}

# Run main function with all arguments
main "$@" 