#!/bin/bash
# Quick launcher script for Verba testing

set -e

echo "🧪 Verba Testing Suite Launcher"
echo "================================"

# Check if we're in the right directory
if [ ! -f "run_complete_verification.py" ]; then
    echo "❌ Error: Please run this script from the Verba directory"
    exit 1
fi

# Show options
echo ""
echo "Available test options:"
echo "  1) Complete verification (recommended)"
echo "  2) Quick verification (fast)"
echo "  3) Unit tests only (containerized)"
echo "  4) Integration tests only (live services)"
echo "  5) Individual test file"
echo "  6) Cleanup only"
echo ""

# Get user choice
read -p "Select option (1-6): " choice

case $choice in
    1)
        echo "🚀 Running complete verification suite..."
        python run_complete_verification.py --verbose
        ;;
    2)
        echo "⚡ Running quick verification..."
        python run_complete_verification.py --quick --verbose
        ;;
    3)
        echo "📦 Running containerized unit tests..."
        python run_containerized_tests.py --verbose
        ;;
    4)
        echo "🔗 Running live integration tests..."
        python run_full_deployment_tests.py --verbose
        ;;
    5)
        echo "Available test files:"
        ls test_*.py | nl
        echo ""
        read -p "Enter test file name: " testfile
        if [ -f "$testfile" ]; then
            echo "🧪 Running $testfile..."
            python "$testfile"
        else
            echo "❌ Test file not found: $testfile"
            exit 1
        fi
        ;;
    6)
        echo "🧹 Cleaning up deployment..."
        python run_full_deployment_tests.py --cleanup-only
        ;;
    *)
        echo "❌ Invalid option: $choice"
        exit 1
        ;;
esac

echo ""
echo "✅ Test execution completed!"