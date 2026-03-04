# Workout Data Pipeline

## Project Overview 🏃‍♂️
This project implements a modern, automated data pipeline for processing workout data using AWS Lambda. The system automatically versions workout data files and identifies new records for processing.

## Core Features 🌟
- Automated file processing via AWS Lambda
- File versioning with timestamp tracking
- New record identification
- Dual-mode operation (local/S3) for development
- Infrastructure as Code with Terraform

## Project Structure 📁
```
workout-tracker/
├── terraform/               # Infrastructure as Code
│   ├── main.tf             # Main Terraform configuration
│   ├── variables.tf        # Variable declarations
│   └── outputs.tf          # Output definitions
└── lambda/
    ├── src/                # Lambda function source code
    │   ├── __init__.py
    │   ├── enhanced_workout_processor.py
    │   └── storage.py
    ├── tests/              # Test suite
    │   ├── __init__.py
    │   ├── conftest.py
    │   ├── mocks.py
    │   └── test_enhanced_workout_processor.py
    ├── local_testing/      # Local development environment
    │   ├── current/        # Current version of files
    │   └── archive/        # Archived versions
    ├── requirements/       # Dependencies
    │   ├── dev.txt        # Development dependencies
    │   └── prod.txt       # Production dependencies
    └── test_locally.py    # Local testing script
```

## Testing Strategy 🧪

Our testing approach has three complementary layers:

### 1. Unit Tests (pytest)
- **Why**: Ensures individual components work correctly
- **What**: Tests individual functions and classes
- **Location**: `lambda/tests/`
- **Run with**: `pytest -v`

### 2. Local Integration Testing
- **Why**: Tests the entire workflow without AWS services
- **What**: Processes actual workout files using local filesystem
- **Location**: `lambda/test_locally.py`
- **Run with**: `python test_locally.py`

### 3. Production Testing (Coming Soon)
- **Why**: Validates behavior in AWS environment
- **What**: Tests with actual S3 buckets and SNS notifications
- **Location**: To be implemented in AWS

### Why This Approach?
1. **Fast Feedback**: Unit tests provide immediate feedback during development
2. **Realistic Testing**: Local integration tests with real files catch practical issues
3. **Cost Effective**: Minimize AWS usage during development
4. **CI/CD Ready**: Tests can run in automated pipelines

## Quick Start 🚀

### Local Development Setup

1. Create Python virtual environment:
```bash
cd workout-tracker/lambda
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.\.venv\Scripts\activate  # Windows
```

2. Install dependencies:
```bash
pip install -r requirements/dev.txt
```

3. Set up local testing environment:
```bash
mkdir -p local_testing/{current,archive}
```

4. Add test data:
```bash
# Copy your workout file
cp path/to/user2632022_workout_history.csv local_testing/current/
```

### Running Tests

1. Run unit tests:
```bash
pytest -v
```

2. Run local integration test:
```bash
python test_locally.py
```

## Next Steps 📝

### 1. Complete Testing Implementation (Current Priority)
- [ ] Add more unit tests for storage handlers
- [ ] Implement end-to-end test with mocked AWS services
- [ ] Add data validation tests

### 2. CI/CD Pipeline Setup
- [ ] Create GitHub Actions workflow
- [ ] Set up automated testing
- [ ] Configure deployment to AWS

### 3. AWS Infrastructure
- [ ] Finalize Terraform configuration
- [ ] Set up monitoring and alerting
- [ ] Configure production environment

### 4. Documentation
- [ ] Add API documentation
- [ ] Create deployment guide
- [ ] Write troubleshooting guide

## Contributing 🤝

### Development Workflow
1. Create feature branch:
```bash
git checkout -b feature/your-feature-name
```

2. Make changes and test:
```bash
# Run unit tests
pytest -v

# Test locally
python test_locally.py
```

3. Commit changes:
```bash
git commit -m "feat: your feature description"
```

4. Push and create pull request:
```bash
git push origin feature/your-feature-name
```

## Troubleshooting 🔧

### Common Test Issues
1. **Import Errors**
   - Ensure virtual environment is activated
   - Verify all dependencies are installed
   - Check Python path includes src directory

2. **File Not Found**
   - Verify file exists in correct location
   - Check LOCAL_STORAGE_PATH setting
   - Ensure proper file permissions

3. **AWS Credentials** (for production testing)
   - Run `aws configure`
   - Check IAM permissions
   - Verify environment variables

## License 📜
MIT License