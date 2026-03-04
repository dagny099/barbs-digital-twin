# 🦖 CareerCraft: Resume and Cover Letter Customization App

Thanks for visiting the GitHub repository for **CareerCraft**, an interactive assistant for crafting tailored resumes and cover letters. Read more details at my [main project page here](https://www.barbhs.com/portfolio/JobAppApp/).

### 🌟 About This Project
CareerCraft is a publicly available **Streamlit web application** that leverages advanced language models (LLMs), including 
OpenAI's GPT-3.5 and GPT-4, to help job seekers customize their resumes and cover letters effectively. Originally hosted on 
[Streamlit Community Cloud](https://streamlit.io/cloud), the app is now deployed on a **custom EC2 server** for enhanced performance, 
reliability, and full control over the hosting environment. 

### 🌐 Visit the Application
- **Primary (EC2)**: [https://careercraft.barbhs.com](https://careercraft.barbhs.com)
- **Backup (Streamlit Cloud)**: [https://barbsassistant.streamlit.app](https://barbsassistant.streamlit.app)


## 🚀 Quickstart Guide (EC2 Deployment)

### **Prerequisites**
- Python 3.8+
- Streamlit
- OpenAI Python library
- PyPDF2
- pickle
- json
- AWS EC2 instance with Ubuntu/Linux
- Nginx or Apache web server
- SSL certificate for HTTPS

### **Installation Steps**
1. **Clone the repository:**
   ```bash
   git clone https://github.com/dagny099/assistant_author.git
   cd assistant_author
   ```

2. **Install required Python packages:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set your OpenAI API key as environment variable:**
   ```bash
   export OPENAI_API_KEY="your_openai_api_key_here"
   # Add to ~/.bashrc or ~/.profile for persistence
   echo 'export OPENAI_API_KEY="your_openai_api_key_here"' >> ~/.bashrc
   ```

### **Deploying to EC2**
Ensure your EC2 instance has:
- Streamlit application files
- Nginx configuration for reverse proxy
- SSL certificate configured
- Process manager (PM2 or systemd) for application persistence

Deploy via SSH:
```bash
# Clone repository on EC2 instance
git clone https://github.com/dagny099/assistant_author.git
cd assistant_author

# Install dependencies
pip install -r requirements.txt

# Start application (with process manager)
pm2 start "streamlit run main.py --server.port=8501" --name careercraft
```

### 🗃️ **Important Note on Persistence:**
EC2 deployment provides persistent storage for uploaded files and generated documents. The application can maintain state across restarts, and all user data is preserved on the server's local filesystem. For enhanced reliability, consider implementing automated backups to AWS S3.

---

## 📂 Project Structure
- `main.py`: Core Streamlit application logic.
- `requirements.txt`: Dependencies.
- `Procfile`: Legacy Heroku deployment instructions (deprecated).
- `setup.sh`: Legacy Streamlit server configuration (deprecated).
- `nginx.conf`: Nginx reverse proxy configuration for EC2.
- `ec2-deploy.sh`: EC2 deployment and setup script.

### 🦕 Architecture Overview
- Add a visual architecture diagram here to illustrate user workflow, integration with OpenAI APIs, and interaction with external cloud storage.
<p align="center">
  <img src="https://www.barbhs.com/assets/images/portfolio/OverallArchitecture-CareerCraft-v1.png" alt="Architecture Diagram" width="70%">
  <br>
  <em>Figure: System architecture diagram showing how different components interact</em>
</p>


## 🌟 Usage Instructions
<p align="center">
  <img src="https://www.barbhs.com/assets/images/portfolio/UserSteps_CareerCraft_v2.png" alt="Architecture Diagram" width="70%">
  <br>
</p>

✅ **1. Upload Your Resume**  
* Go to the Ingest Resume section.  
* Choose between:  *Manual text entry* or *Upload PDF or TXT file*  
* Click "Ingest Information" to process.

✅ **2. Input Job Details**  
* Use the sidebar to provide:  
Company Name | Position Title | Job Description

✅ **3. Generate First Draft**  
- In the Build First Draft section, click "Generate Cover Letter".  
- A first draft of your tailored cover letter appears immediately.  

✅ **4. Interactive Editing**  
- To modify the draft: Describe changes clearly in the text box (e.g., "make the tone more formal", "highlight leadership experience").  
- Click "Modify Cover Letter".  

✅ **5. ATS Keyword Optimization**  
* Click "Scan resume with ATS" or "Scan cover letter with ATS".
* Results show a percentage match and common keywords, highlighting any gaps.

✅ **6. Download Final Documents**  
* Use the provided download buttons to immediately save your finalized resume and cover letter.


## 🎯 Roadmap: Q4 2024

1. **Enhanced ATS Scanning:**
   - NLP-based keyword analysis (SpaCy, transformers)
2. **Additional Format Support:**
   - Microsoft Word document handling
3. **Expanded LLM Guidance:**
   - Advanced user interactions and editing suggestions


## 📜 License
Licensed under the MIT License.
