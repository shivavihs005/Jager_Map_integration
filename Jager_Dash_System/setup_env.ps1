Write-Host "Creating virtual environment (venv)..."
python -m venv venv

Write-Host "Activating virtual environment..."
# Using the ampersand dot-source or direct call depending on PS version, but calling it directly usually works in standard scripts if execution policy permits.
# We'll invoke it and then run pip
& .\venv\Scripts\Activate.ps1

Write-Host "Upgrading pip..."
python -m pip install --upgrade pip

Write-Host "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

Write-Host "========================================="
Write-Host "Environment setup complete!"
Write-Host "To activate the environment in the future, run:"
Write-Host ".\venv\Scripts\Activate.ps1"
Write-Host "Then you can start the application with:"
Write-Host "python app.py"
Write-Host "========================================="
