# OCT Smart Tutor

OCT Smart Tutor is an AI-powered educational application designed to help doctors and medical students practice classifying Optical Coherence Tomography (OCT) retinal scans. The system features a responsive React frontend and a FastAPI backend that uses a machine-learning model alongside a dynamic bandit augmentation curriculum for fair and adaptive training.

## Prerequisites

Before running the application, ensure you have the following installed:
- Python 3.10+
- A Kaggle account (for fetching the image dataset)

### Installing Node.js and npm
The frontend requires Node.js 18+ and npm. To install:
- **Windows / macOS**: Download and install the official installer from [nodejs.org](https://nodejs.org/). We recommend the LTS (Long Term Support) version. npm is included automatically.
- **Linux (Debian/Ubuntu)**: 
  ```bash
  curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
  sudo apt-get install -y nodejs
  ```
- **Verify Installation**: Open your terminal and run `node -v` and `npm -v` to ensure they were installed correctly.

## 1. Setup Instructions

### Clone the Repository
Open your terminal and run the following command to download the project:
```bash
git clone <your-repository-url>
cd oct-smart-tutor
```

### Environment Variables
You must provide your Kaggle credentials to stream images dynamically.
1. Create a `.env` file in the root directory (`oct-smart-tutor/`).
2. Add your Kaggle API credentials:
   ```env
   KAGGLE_USERNAME=your_kaggle_username
   KAGGLE_KEY=your_kaggle_api_key
   ```
*(You can obtain these from the "Account" tab on Kaggle by clicking "Create New API Token")*

### The Machine Learning Model
Ensure the pre-trained Keras model (`UGP-final-model.keras`) is located in the directory directly above the main project folder.

### Backend Setup
1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```
2. (Optional but recommended) Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On macOS/Linux
   ```
3. Install the required Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Frontend Setup & Build
The application uses Vite for the frontend. For a production-ready setup, the frontend is built and served directly by the backend.
1. Navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```
2. Install the Node modules:
   ```bash
   npm install
   ```
3. Build the frontend for production:
   ```bash
   npm run build
   ```



## 2. Running the Application

If you wish to run the app in development mode with Hot Module Replacement (HMR) for the frontend:

1. **Start the Backend:**
   ```bash
   cd backend
   python main.py
   ```
   *(Runs on http://localhost:8000)*

2. **Start the Frontend (in a new terminal):**
   ```bash
   cd frontend
   npm run dev
   ```
   *(Runs on http://localhost:5173)*

The frontend is configured to automatically proxy `/api` requests to the backend at port 8000.
