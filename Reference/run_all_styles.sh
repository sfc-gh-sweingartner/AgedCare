#!/bin/bash

# Healthcare AI Demo - Multi-Style Runner
# =====================================
# 
# This script launches all three UI styles simultaneously for comparison
# Each style runs on a different port for side-by-side evaluation

echo "🏥 Healthcare AI Demo - Multi-Style Launcher"
echo "============================================="

# Check if src directory exists
if [ ! -d "src" ]; then
    echo "❌ Error: src directory not found. Please run from project root."
    exit 1
fi

# Function to check if port is in use
check_port() {
    lsof -i :$1 > /dev/null 2>&1
    return $?
}

# Function to kill existing processes on our ports
cleanup_ports() {
    echo "🧹 Cleaning up existing processes..."
    
    for port in 8501 8502 8503; do
        if check_port $port; then
            echo "   Stopping process on port $port"
            lsof -ti :$port | xargs kill -9 2>/dev/null || true
        fi
    done
    
    sleep 2
}

# Function to start a Streamlit app with error handling
start_app() {
    local app_name=$1
    local port=$2
    local style_name=$3
    
    if [ ! -f "src/$app_name" ]; then
        echo "⚠️  Warning: $app_name not found, skipping $style_name style"
        return 1
    fi
    
    echo "🚀 Starting $style_name style on port $port..."
    
    # Start in background with output redirection
    nohup streamlit run "src/$app_name" \
        --server.port $port \
        --server.headless true \
        --server.runOnSave true \
        --theme.base "light" \
        > "logs/${style_name}_${port}.log" 2>&1 &
    
    local pid=$!
    echo "   PID: $pid"
    
    return 0
}

# Create logs directory
mkdir -p logs

# Cleanup existing processes
cleanup_ports

echo ""
echo "📊 Launching applications..."
echo ""

# Track successful launches
successful_launches=0

# Launch Corporate Standard (Port 8501)
if start_app "streamlit_corporate.py" 8501 "corporate"; then
    ((successful_launches++))
fi

# Launch Modern Minimalist (Port 8502)  
if start_app "streamlit_minimalist.py" 8502 "minimalist"; then
    ((successful_launches++))
fi

# Launch Data-Dense Powerhouse (Port 8503)
if start_app "streamlit_powerhouse.py" 8503 "powerhouse"; then
    ((successful_launches++))
fi

# Give apps time to start
echo ""
echo "⏳ Waiting for applications to initialize..."
sleep 8

echo ""
echo "🎯 Application Status:"
echo "====================="

# Check which apps are actually running
declare -A app_status
app_status[8501]="Corporate Standard"
app_status[8502]="Modern Minimalist" 
app_status[8503]="Data-Dense Powerhouse"

running_count=0
for port in 8501 8502 8503; do
    if check_port $port; then
        echo "✅ ${app_status[$port]}: http://localhost:$port"
        ((running_count++))
    else
        echo "❌ ${app_status[$port]}: Failed to start on port $port"
    fi
done

echo ""
echo "📈 Summary:"
echo "==========="
echo "   Successfully launched: $running_count out of 3 applications"

if [ $running_count -gt 0 ]; then
    echo ""
    echo "🔗 Quick Access Links:"
    echo "====================="
    
    if check_port 8501; then
        echo "   Corporate Standard:   http://localhost:8501"
    fi
    
    if check_port 8502; then
        echo "   Modern Minimalist:    http://localhost:8502"
    fi
    
    if check_port 8503; then
        echo "   Data-Dense Powerhouse: http://localhost:8503"
    fi
    
    echo ""
    echo "📋 Usage Instructions:"
    echo "====================="
    echo "   • Open multiple browser tabs to compare styles side-by-side"
    echo "   • Each style uses the same backend data and functionality"
    echo "   • Use Ctrl+C to stop this script and all applications"
    echo ""
    echo "📝 Logs available in: ./logs/"
    echo ""
    echo "🔄 Applications are running... Press Ctrl+C to stop all"
    
    # Wait for user interrupt
    trap 'echo; echo "🛑 Stopping all applications..."; cleanup_ports; echo "✅ All applications stopped."; exit 0' INT
    
    while true; do
        sleep 5
        # Check if any apps died unexpectedly
        dead_count=0
        for port in 8501 8502 8503; do
            if ! check_port $port; then
                ((dead_count++))
            fi
        done
        
        if [ $dead_count -eq 3 ]; then
            echo ""
            echo "❌ All applications have stopped unexpectedly."
            echo "   Check logs in ./logs/ for error details."
            exit 1
        fi
    done
    
else
    echo ""
    echo "❌ No applications started successfully."
    echo "   Please check that the required files exist:"
    echo "   • src/streamlit_corporate.py"
    echo "   • src/streamlit_minimalist.py"
    echo "   • src/streamlit_powerhouse.py"
    echo ""
    echo "   Check logs in ./logs/ for error details."
    exit 1
fi
