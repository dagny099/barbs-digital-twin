# Recetas Inteligentes (Intelligent Recipes)
Resources for my PoC AI-based culinary assistant using a multimodal Gemini model that generates personalized recipes based on user preferences and available ingredients. Powered by Google Cloud and Gemini multimodal AI.

## Overview

This application was developed as a proof-of-concept to demonstrate how Google Cloud's Gemini AI model can be used to create intelligent recipe recommendations. The app generates customized recipes based on:

- Cuisine preferences
- Dietary restrictions
- Food allergies
FUTURE- Available ingredients
FUTURE- Wine pairing preferences

## Features

- **Customized Recipe Generation**: Get personalized recipes based on your specific preferences and dietary needs
- **Allergy-Aware**: Safely excludes ingredients associated with specified allergies
- **Wine Pairing**: Includes appropriate wine pairings for each recipe
- **Nutritional Information**: Provides calorie counts and nutritional facts for all recipes
- **Cloud Deployment**: Fully deployed on Google Cloud Run for scalability and reliability

## Technologies Used

- **Google Cloud Platform**
  - Cloud Run
  - Artifact Registry
  - Gemini AI API
- **Streamlit**: Interactive web application framework
- **Python**: Backend application logic
- **Docker**: Containerization for deployment

## Getting Started

### Prerequisites

- Google Cloud account with necessary APIs enabled:
  - Vertex AI API
  - Cloud Run API
  - Artifact Registry API

### Local Development

1. Clone the repository
2. Set up environment variables:
   ```
   export GCP_PROJECT=your-project-id
   export GCP_REGION=your-region
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Run the application locally:
   ```
   streamlit run chef.py --browser.serverAddress=localhost --server.enableCORS=false --server.enableXsrfProtection=false --server.port 8080
   ```

### Deployment

1. Build the Docker image:
   ```
   gcloud artifacts repositories create chef-repo --location=your-region --repository-format=Docker
   gcloud builds submit --tag your-region-docker.pkg.dev/your-project/chef-repo/chef-streamlit-app
   ```

2. Deploy to Cloud Run:
   ```
   gcloud run deploy chef-streamlit-app --port=8080 --image=your-region-docker.pkg.dev/your-project/chef-repo/chef-streamlit-app --allow-unauthenticated --region=your-region --platform=managed --project=your-project --set-env-vars=GCP_PROJECT=your-project,GCP_REGION=your-region
   ```

## Example Usage

The application provides a simple web interface where users can:

1. Select cuisine type (Japanese, Italian, Mexican, etc.)
2. Specify dietary preferences (low sodium, vegetarian, etc.)
3. Indicate any food allergies
4. List available ingredients
5. Choose wine preference
6. Generate recipe recommendations

## Project Structure

```
recetas-inteligentes/
├── chef.py                # Main application with Streamlit UI
├── Dockerfile             # Docker configuration for deployment
├── requirements.txt       # Python dependencies
├── README.md              # This file
└── tests/                 # Test scripts
```

## Future Enhancements

- Mobile application integration
- User accounts for saving favorite recipes
- Image recognition for available ingredients
- Voice-enabled recipe instructions
- Social sharing capabilities

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Google Cloud Platform for providing the infrastructure and AI capabilities
- Streamlit for the intuitive web application framework
- The open-source community for various libraries used in this project
