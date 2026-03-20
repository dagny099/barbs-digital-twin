# Workout Analytics Dashboard: A Learning Journey with pytest


## Project Overview
This project is both a practical workout analytics dashboard and a learning exercise in Python testing methodologies. It demonstrates how to build a data-driven web application while maintaining good testing practices using pytest.

### Current Functionality
- Interactive Streamlit dashboard displaying workout metrics
- MySQL database connection with error handling
- Basic statistical analysis of workout data
- Configurable date ranges and metric selection
- Distribution visualization using Plotly

## Learning Focus: Testing with pytest

I embarked on this project because I want to expand my understanding of application testing principles and hands-on implementation. Hence, I found a practical example of how to implement pytests in a real-world application (my workout dashboard!). Key testing concepts demonstrated include:

### 1. Test Structure and Organization
```
workout_dashboard/
├── src/
│   ├── database.py      # Database connection handling
│   ├── analytics.py     # Data processing
│   └── app.py          # Streamlit interface
├── tests/
│   ├── conftest.py     # Shared test fixtures
│   ├── test_database.py
│   ├── test_analytics.py
│   └── test_app.py
```

### 2. Testing Patterns Demonstrated
- Database connection mocking
- Error handling verification
- Data transformation testing
- Edge case handling
- Fixture usage for test data

### 3. Key Testing Concepts Learned
- Using fixtures for test setup
- Mocking external dependencies
- Error case testing
- Test parameterization
- Coverage reporting


## Project Setup & Installation  
Currently, this project uses a simple `requirements.txt` for dependency management to maintain focus on learning testing practices. Future versions will explore more sophisticated approaches (see Next Milestones below)

1. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install package in development mode:
```bash
pip install -e .
```

4. Run tests:
```bash
pytest tests/
```

5. Start the dashboard:
```bash
streamlit run src/app.py
```

### Project Documentation

This project maintains detailed documentation in the `docs/` directory:

- `testing_guide.md`: Introduction to the theory and practice of testing web applications, python flavor
- `testing_cheatsheet.md`: Comprehensive guide to testing data science applications
- `setup_guide.md`: In-depth explanation of Python project setup approaches


## Analytical Capabilities

The dashboard is also designed to answer important questions about workout patterns:

### Current Analysis
- Basic statistical summaries
- Metric distributions
- Weekly/Monthly aggregations

### Planned Analysis
1. Day of Week Patterns
   - Do workout intensities vary by day?
   - Are weekend workouts consistently different?
   - Which days show highest/lowest variation?

2. Time Series Analysis
   - Trend identification
   - Seasonal patterns
   - Performance forecasting
   - Anomaly detection for data cleaning

3. Performance Analysis
   - Activity type comparisons
   - Progress tracking
   - Recovery pattern analysis



## Next Milestones

### 1. Cloud Deployment
- Deploy dashboard on Google Cloud Platform
- Set up CI/CD pipeline
- Implement secure database connections

### 2. Testing Improvements
- Increase test coverage
- Add integration tests
- Implement property-based testing
- Add performance tests

### 3. Analytics Enhancement
- Implement time series analysis
- Add anomaly detection
- Create more sophisticated visualizations
- Add predictive analytics

### 4. Future Plans for Setup. 
- Implement Poetry for dependency management
- Add Docker containerization
- Explore cloud deployment options

See `docs/setup_guide.md` for a detailed discussion of these choices and future directions.



## Learning Resources

If you're using this project to learn about testing, here are some key concepts to focus on:

1. Test Organization
   - Understanding test discovery
   - Fixture scoping
   - Test parameterization

2. Mocking Strategies
   - When to mock
   - Different types of test doubles
   - Mocking best practices

3. Database Testing
   - Using test databases
   - Transaction management
   - Data fixtures

4. Coverage Analysis
   - Running coverage reports
   - Identifying untested code
   - Making coverage decisions


## Contributing

This project is primarily a learning exercise, but contributions are welcome! Particularly interested in:
- Additional test cases
- New analytical features
- Documentation improvements
- Performance optimizations


## License
MIT


## In Summary
This project was developed as a learning exercise in software testing, with particular focus on:
- pytest framework usage
- Database interaction testing
- Data analysis validation
- Web application testing

## Project Status
Currently in active development with focus on testing methodology and analytical capabilities.
