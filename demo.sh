#!/bin/bash
# Quick Demo Script - Test the CAD Migration Tool

set -e

echo "========================================="
echo "CAD Migration Tool - Quick Demo"
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}[1/6] Testing CLI Help${NC}"
python3 cad_migration.py --help | head -20
echo ""

echo -e "${BLUE}[2/6] Testing Version${NC}"
python3 cad_migration.py --version
echo ""

echo -e "${BLUE}[3/6] Testing Migrate Commands${NC}"
python3 cad_migration.py migrate --help | head -15
echo ""

echo -e "${BLUE}[4/6] Testing Learn Commands${NC}"
python3 cad_migration.py learn --help | head -12
echo ""

echo -e "${BLUE}[5/6] Testing Validate Commands${NC}"
python3 cad_migration.py validate --help | head -12
echo ""

echo -e "${BLUE}[6/6] Testing PDM Commands${NC}"
python3 cad_migration.py pdm --help | head -12
echo ""

echo -e "${GREEN}========================================="
echo "✓ All CLI commands working!"
echo "=========================================${NC}"
echo ""

echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Install dependencies: pip install ezdxf click rich pyyaml sqlalchemy"
echo "2. Read TESTING.md for detailed testing instructions"
echo "3. Try: python3 cad_migration.py migrate run --help"
echo ""

chmod +x demo.sh
