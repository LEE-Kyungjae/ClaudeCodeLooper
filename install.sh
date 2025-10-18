#!/bin/bash

# ClaudeCodeLooper Installation Script
# For macOS and Linux

set -e  # Exit on error

echo "================================================"
echo "  ClaudeCodeLooper Installation"
echo "================================================"
echo ""

# Check Python version
echo "🔍 Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]; }; then
    echo "❌ Error: Python 3.11 or higher is required"
    echo "   Current version: $PYTHON_VERSION"
    echo "   Please upgrade Python and try again"
    exit 1
fi

echo "✅ Python $PYTHON_VERSION detected"
echo ""

# Ask for installation type
echo "📦 Installation Options:"
echo "  1) User installation (recommended)"
echo "  2) Development installation"
echo "  3) System-wide installation (requires sudo)"
echo ""
read -p "Select option [1-3]: " INSTALL_TYPE

case $INSTALL_TYPE in
    1)
        echo ""
        echo "📦 Installing ClaudeCodeLooper (user mode)..."
        pip3 install --user -e .
        ;;
    2)
        echo ""
        echo "📦 Installing ClaudeCodeLooper (development mode)..."
        pip3 install -e ".[dev]"
        ;;
    3)
        echo ""
        echo "📦 Installing ClaudeCodeLooper (system-wide)..."
        sudo pip3 install -e .
        ;;
    *)
        echo "❌ Invalid option. Exiting."
        exit 1
        ;;
esac

echo ""
echo "✅ Installation complete!"
echo ""

# Verify installation
echo "🔍 Verifying installation..."
if command -v claude-looper &> /dev/null; then
    echo "✅ claude-looper command is available"
    claude-looper --version
else
    echo "⚠️  claude-looper command not found in PATH"
    echo "   You may need to add ~/.local/bin to your PATH"
    echo "   Add this to your ~/.bashrc or ~/.zshrc:"
    echo "   export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo ""
echo "================================================"
echo "  Quick Start"
echo "================================================"
echo ""
echo "To start using ClaudeCodeLooper:"
echo ""
echo "  # Start monitoring"
echo "  claude-looper start --daemon"
echo ""
echo "  # Check status"
echo "  claude-looper status"
echo ""
echo "  # View logs"
echo "  claude-looper logs"
echo ""
echo "  # Stop monitoring"
echo "  claude-looper stop --all"
echo ""
echo "Or use Claude Code slash commands:"
echo "  /cl:on, /cl:status, /cl:logs, /cl:off"
echo ""
echo "================================================"
echo "For more information, see README.md"
echo "================================================"
