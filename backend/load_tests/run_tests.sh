#!/bin/bash

# DocAssist Practice Manager - Load Test Runner
#
# Usage:
#   ./run_tests.sh [test_type] [users] [environment]
#
# Examples:
#   ./run_tests.sh mixed 100 dev
#   ./run_tests.sh booking 50 staging
#   ./run_tests.sh search 200 prod

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
TEST_TYPE="${1:-mixed}"
USERS="${2:-100}"
ENVIRONMENT="${3:-dev}"
SPAWN_RATE="${4:-10}"
RUN_TIME="${5:-5m}"

# Validate test type
valid_tests=("mixed" "booking" "search" "receptionist" "doctor" "analytics")
if [[ ! " ${valid_tests[@]} " =~ " ${TEST_TYPE} " ]]; then
    echo -e "${RED}Error: Invalid test type '${TEST_TYPE}'${NC}"
    echo "Valid types: ${valid_tests[@]}"
    exit 1
fi

# Set environment variables
export TEST_ENV="${ENVIRONMENT}"

# Determine which locustfile to use
case "${TEST_TYPE}" in
    "mixed")
        LOCUSTFILE="scenarios/mixed_load.py"
        USER_CLASS="RealisticClinicUser"
        ;;
    "booking")
        LOCUSTFILE="scenarios/booking_flow.py"
        USER_CLASS="BookingFlowUser"
        ;;
    "search")
        LOCUSTFILE="scenarios/search_heavy.py"
        USER_CLASS="SearchHeavyUser"
        ;;
    "receptionist")
        LOCUSTFILE="locustfile.py"
        USER_CLASS="ReceptionistUser"
        ;;
    "doctor")
        LOCUSTFILE="locustfile.py"
        USER_CLASS="DoctorUser"
        ;;
    "analytics")
        LOCUSTFILE="locustfile.py"
        USER_CLASS="AnalyticsUser"
        ;;
esac

# Create reports directory
REPORTS_DIR="reports/$(date +%Y%m%d_%H%M%S)_${TEST_TYPE}_${USERS}users"
mkdir -p "${REPORTS_DIR}"

echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  DocAssist Practice Manager - Load Test${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Test Configuration:${NC}"
echo "  Test Type:     ${TEST_TYPE}"
echo "  Users:         ${USERS}"
echo "  Spawn Rate:    ${SPAWN_RATE} users/sec"
echo "  Run Time:      ${RUN_TIME}"
echo "  Environment:   ${ENVIRONMENT}"
echo "  User Class:    ${USER_CLASS}"
echo "  Reports Dir:   ${REPORTS_DIR}"
echo ""

# Check if backend is running
HOST_URL=$(python3 -c "from config import get_config; print(get_config('${ENVIRONMENT}').host)")
echo -e "${YELLOW}Checking backend at ${HOST_URL}...${NC}"

if curl -s -o /dev/null -w "%{http_code}" "${HOST_URL}/docs" | grep -q "200"; then
    echo -e "${GREEN}✓ Backend is running${NC}"
else
    echo -e "${RED}✗ Backend is not accessible at ${HOST_URL}${NC}"
    echo "  Please start the backend first"
    exit 1
fi

echo ""
echo -e "${GREEN}Starting load test...${NC}"
echo ""

# Run Locust
locust \
    -f "${LOCUSTFILE}" \
    --users "${USERS}" \
    --spawn-rate "${SPAWN_RATE}" \
    --run-time "${RUN_TIME}" \
    --host "${HOST_URL}" \
    --html "${REPORTS_DIR}/report.html" \
    --csv "${REPORTS_DIR}/stats" \
    --logfile "${REPORTS_DIR}/locust.log" \
    --headless \
    --only-summary

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Load Test Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Reports generated:${NC}"
echo "  HTML Report:   ${REPORTS_DIR}/report.html"
echo "  CSV Stats:     ${REPORTS_DIR}/stats_stats.csv"
echo "  Failures:      ${REPORTS_DIR}/stats_failures.csv"
echo "  Log File:      ${REPORTS_DIR}/locust.log"
echo ""

# Generate performance summary
echo -e "${YELLOW}Generating performance summary...${NC}"
python3 generate_report.py "${REPORTS_DIR}"

echo ""
echo -e "${GREEN}Done!${NC}"
echo ""
echo "To view the HTML report, run:"
echo "  open ${REPORTS_DIR}/report.html    # macOS"
echo "  xdg-open ${REPORTS_DIR}/report.html    # Linux"
echo "  start ${REPORTS_DIR}/report.html   # Windows"
