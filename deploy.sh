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

# Function to check if a command exists
check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 is required but not installed. Please install it first."
        exit 1
    fi
}

# Function to check environment
check_environment() {
    print_status "Checking environment..."
    
    # Check required commands
    check_command docker
    check_command curl
    
    # Check if .env file exists
    if [ ! -f .env ]; then
        print_error ".env file not found. Please create it from .env.example"
        exit 1
    fi
    
    # Check if .env file has required variables
    required_vars=(
        "API_URL" 
        "API_KEY" 
        "STREAMLIT_SERVER_PORT" 
        "STREAMLIT_SERVER_ADDRESS"
        "DB_HOST"
        "DB_PORT"
        "DB_NAME"
        "DB_USER"
        "DB_PASSWORD"
    )
    for var in "${required_vars[@]}"; do
        if ! grep -q "^$var=" .env; then
            print_error "Required variable $var not found in .env file"
            exit 1
        fi
    done
    
    print_status "Environment check passed"
}

# Function to backup current version
backup_current_version() {
    print_status "Backing up current version..."
    
    if docker ps -q --filter "name=texas-treasury-query" | grep -q .; then
        CURRENT_VERSION=$(docker inspect texas-treasury-query --format='{{.Config.Image}}')
        BACKUP_TAG="backup-$(date +%Y%m%d-%H%M%S)"
        
        if [ ! -z "$CURRENT_VERSION" ]; then
            docker tag $CURRENT_VERSION texas-treasury-query:$BACKUP_TAG
            print_status "Current version backed up as texas-treasury-query:$BACKUP_TAG"
        fi
    fi
}

# Function to build and deploy
deploy() {
    print_status "Building new Docker image..."
    
    # Build the image
    docker build -t texas-treasury-query:latest .
    if [ $? -ne 0 ]; then
        print_error "Docker build failed"
        exit 1
    fi
    
    # Stop and remove existing container if it exists
    if docker ps -q --filter "name=texas-treasury-query" | grep -q .; then
        print_status "Stopping existing container..."
        docker stop texas-treasury-query
        docker rm texas-treasury-query
    fi
    
    # Run new container
    print_status "Starting new container..."
    docker run -d \
        --name texas-treasury-query \
        -p 8501:8501 \
        --env-file .env \
        --restart unless-stopped \
        texas-treasury-query:latest
    
    if [ $? -ne 0 ]; then
        print_error "Failed to start container"
        exit 1
    fi
}

# Function to verify deployment
verify_deployment() {
    print_status "Verifying deployment..."
    
    # Wait for container to start
    sleep 5
    
    # Check if container is running
    if ! docker ps -q --filter "name=texas-treasury-query" | grep -q .; then
        print_error "Container failed to start"
        exit 1
    fi
    
    # Check health endpoint
    HEALTH_CHECK_RETRIES=5
    HEALTH_CHECK_DELAY=10
    
    for i in $(seq 1 $HEALTH_CHECK_RETRIES); do
        print_status "Checking health endpoint (attempt $i/$HEALTH_CHECK_RETRIES)..."
        
        HEALTH_STATUS=$(curl -s "http://localhost:8501/?health=check")
        if echo $HEALTH_STATUS | grep -q '"status":"healthy"'; then
            print_status "Health check passed"
            break
        fi
        
        if [ $i -eq $HEALTH_CHECK_RETRIES ]; then
            print_error "Health check failed after $HEALTH_CHECK_RETRIES attempts"
            exit 1
        fi
        
        print_warning "Health check failed, retrying in $HEALTH_CHECK_DELAY seconds..."
        sleep $HEALTH_CHECK_DELAY
    done
    
    # Check system status
    print_status "Checking system status..."
    SYSTEM_STATUS=$(curl -s "http://localhost:8501/?status=check")
    if echo $SYSTEM_STATUS | grep -q '"status":"healthy"'; then
        print_status "System status check passed"
    else
        print_warning "System status check returned warnings or errors"
        echo $SYSTEM_STATUS
    fi
}

# Main deployment process
main() {
    print_status "Starting deployment process..."
    
    # Check environment
    check_environment
    
    # Backup current version
    backup_current_version
    
    # Deploy new version
    deploy
    
    # Verify deployment
    verify_deployment
    
    print_status "Deployment completed successfully!"
    print_status "Application is available at http://localhost:8501"
}

# Run main function
main 