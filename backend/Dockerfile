# Stage 1: Use an official Python runtime as a parent image
# We use a "slim" version because it's smaller and more secure.
FROM python:3.11-slim

# Stage 2: Set the working directory inside the container
# All subsequent commands will run from this path.
WORKDIR /app

# Stage 3: Copy only the requirements file first
# This is a Docker caching optimization. If requirements.txt doesn't change,
# Docker won't re-run the pip install step on subsequent builds, making them much faster.
COPY requirements.txt .

# Stage 4: Install the Python dependencies
# --no-cache-dir makes the image smaller.
RUN pip install --no-cache-dir -r requirements.txt

# Stage 5: Copy the rest of your application code into the container
# This includes main.py, .env, and any other files.
COPY . .

# Stage 6: Expose the port the app runs on
# Our app inside the container will listen on port 80.
EXPOSE 80

# Stage 7: Define the command to run your app
# This is the command that will be executed when the container starts.
# We use "--host 0.0.0.0" to make the server accessible from outside the container.
# Azure App Service expects applications to listen on port 80 by default.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]