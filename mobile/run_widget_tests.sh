#!/bin/bash

# Flutter Widget Tests Runner for DocAssist Practice Manager
# This script provides convenient commands to run widget tests

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Change to mobile directory
cd "$(dirname "$0")"

# Main menu
show_menu() {
    echo ""
    print_header "DocAssist Widget Tests"
    echo "1. Run all widget tests"
    echo "2. Run appointment card tests"
    echo "3. Run patient card tests"
    echo "4. Run appointment list screen tests"
    echo "5. Run patient list screen tests"
    echo "6. Run all tests with coverage"
    echo "7. Run tests in watch mode"
    echo "8. Run specific test by name"
    echo "9. View coverage report"
    echo "0. Exit"
    echo ""
    read -p "Choose an option: " choice

    case $choice in
        1) run_all_tests ;;
        2) run_appointment_card_tests ;;
        3) run_patient_card_tests ;;
        4) run_appointment_list_tests ;;
        5) run_patient_list_tests ;;
        6) run_tests_with_coverage ;;
        7) run_watch_mode ;;
        8) run_specific_test ;;
        9) view_coverage ;;
        0) exit 0 ;;
        *) print_error "Invalid option"; show_menu ;;
    esac
}

# Function to run all widget tests
run_all_tests() {
    print_header "Running All Widget Tests"
    flutter test test/core/widgets/ test/features/appointments/presentation/appointment_list_screen_test.dart test/features/patients/presentation/patient_list_screen_test.dart
    print_success "All widget tests completed!"
    show_menu
}

# Function to run appointment card tests
run_appointment_card_tests() {
    print_header "Running Appointment Card Tests"
    flutter test test/core/widgets/appointment_card_test.dart
    print_success "Appointment card tests completed!"
    show_menu
}

# Function to run patient card tests
run_patient_card_tests() {
    print_header "Running Patient Card Tests"
    flutter test test/core/widgets/patient_card_test.dart
    print_success "Patient card tests completed!"
    show_menu
}

# Function to run appointment list screen tests
run_appointment_list_tests() {
    print_header "Running Appointment List Screen Tests"
    flutter test test/features/appointments/presentation/appointment_list_screen_test.dart
    print_success "Appointment list screen tests completed!"
    show_menu
}

# Function to run patient list screen tests
run_patient_list_tests() {
    print_header "Running Patient List Screen Tests"
    flutter test test/features/patients/presentation/patient_list_screen_test.dart
    print_success "Patient list screen tests completed!"
    show_menu
}

# Function to run tests with coverage
run_tests_with_coverage() {
    print_header "Running Tests with Coverage"
    flutter test --coverage test/core/widgets/ test/features/appointments/presentation/appointment_list_screen_test.dart test/features/patients/presentation/patient_list_screen_test.dart

    print_info "Coverage report generated at: coverage/lcov.info"

    # Check if genhtml is available
    if command -v genhtml &> /dev/null; then
        print_info "Generating HTML coverage report..."
        genhtml coverage/lcov.info -o coverage/html
        print_success "HTML coverage report generated at: coverage/html/index.html"

        # Ask if user wants to open the report
        read -p "Open coverage report in browser? (y/n): " open_report
        if [ "$open_report" = "y" ]; then
            if command -v xdg-open &> /dev/null; then
                xdg-open coverage/html/index.html
            elif command -v open &> /dev/null; then
                open coverage/html/index.html
            else
                print_info "Please open coverage/html/index.html manually"
            fi
        fi
    else
        print_info "Install lcov to generate HTML coverage reports: sudo apt-get install lcov"
    fi

    show_menu
}

# Function to run tests in watch mode
run_watch_mode() {
    print_header "Running Tests in Watch Mode"
    print_info "Tests will re-run on file changes. Press Ctrl+C to exit."
    flutter test --watch test/core/widgets/ test/features/appointments/presentation/appointment_list_screen_test.dart test/features/patients/presentation/patient_list_screen_test.dart
    show_menu
}

# Function to run specific test by name
run_specific_test() {
    print_header "Run Specific Test"
    echo "Enter test name pattern (e.g., 'displays patient name'):"
    read -p "Pattern: " pattern

    if [ -n "$pattern" ]; then
        print_info "Running tests matching: $pattern"
        flutter test --name "$pattern"
        print_success "Tests completed!"
    else
        print_error "No pattern provided"
    fi

    show_menu
}

# Function to view coverage report
view_coverage() {
    print_header "View Coverage Report"

    if [ -f "coverage/lcov.info" ]; then
        print_info "Coverage file found. Generating summary..."

        # Show basic coverage stats
        if command -v lcov &> /dev/null; then
            lcov --summary coverage/lcov.info
        else
            print_info "Coverage file exists at: coverage/lcov.info"
            print_info "Install lcov for detailed reports: sudo apt-get install lcov"
        fi

        # Open HTML report if it exists
        if [ -f "coverage/html/index.html" ]; then
            read -p "Open HTML coverage report? (y/n): " open_report
            if [ "$open_report" = "y" ]; then
                if command -v xdg-open &> /dev/null; then
                    xdg-open coverage/html/index.html
                elif command -v open &> /dev/null; then
                    open coverage/html/index.html
                else
                    print_info "Please open coverage/html/index.html manually"
                fi
            fi
        else
            print_info "Run option 6 first to generate HTML coverage report"
        fi
    else
        print_error "No coverage data found. Run tests with coverage first (option 6)."
    fi

    show_menu
}

# Check if Flutter is installed
if ! command -v flutter &> /dev/null; then
    print_error "Flutter is not installed or not in PATH"
    exit 1
fi

# Check Flutter version
print_info "Flutter version:"
flutter --version | head -1

# Start the menu
show_menu
