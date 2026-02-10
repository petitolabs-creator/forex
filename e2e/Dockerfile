FROM python:3.11-slim

WORKDIR /app

# Install required libraries
RUN pip install --no-cache-dir requests redis

# Copy all test scripts
COPY *.py .

# Make scripts executable
RUN chmod +x *.py

# Run all tests by default
CMD ["python3", "run_all_tests.py"]
