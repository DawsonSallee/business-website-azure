# Use a specific and common base image
FROM python:3.11-slim-bullseye

# Install prerequisites for adding new repositories and for the driver
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    apt-transport-https \
    unixodbc-dev

# Add Microsoft's GPG key
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -

# Add the Microsoft products repository for Debian 11 (Bullseye)
RUN curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list

# Update the package list again to include the new repository
RUN apt-get update

# Install the ODBC driver, accepting the EULA automatically
RUN ACCEPT_EULA=Y apt-get install -y msodbcsql18

# --- The rest of the Dockerfile is the same ---

# Set the working directory
WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the port
EXPOSE 80

# Define the run command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]