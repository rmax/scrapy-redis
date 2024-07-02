FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install tox and dependencies (replace 'your-requirements.txt' with your actual file)
COPY requirements.txt .
COPY requirements-tests.txt .
RUN pip install -r requirements.txt -r requirements-tests.txt

# Copy your project code
COPY . .

# Run Tox tests
CMD ["tox"]

