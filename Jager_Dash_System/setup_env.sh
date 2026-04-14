#!/bin/bash
echo "Creating virtual environment (venv)..."
python3 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

echo "========================================="
echo "Environment setup complete!"
echo "To activate the environment in the future, run:"
echo "source venv/bin/activate"
echo "Then start the application with:"
echo "python3 app.py"
echo "========================================="
