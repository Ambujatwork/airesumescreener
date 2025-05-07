import streamlit as st
import requests
import json
from typing import Dict, List, Optional, Any
import os
import base64
from datetime import datetime

# Configure the application
st.set_page_config(
    page_title="ResumeMatch Pro",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ======= Services =======
class APIService:
    """Base service for API interactions"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authentication token"""
        token = st.session_state.get("access_token", "")
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle API response and errors"""
        if response.status_code >= 400:
            try:
                error_data = response.json()
                error_message = error_data.get("detail", "Unknown error")
            except:
                error_message = f"Error: {response.status_code}"
            
            st.error(error_message)
            raise Exception(error_message)
        
        return response.json()


class AuthService(APIService):
    """Service for authentication operations"""
    
    def login(self, username: str, password: str) -> bool:
        """Login user and store token"""
        try:
            response = requests.post(
                f"{self.base_url}/login",
                data={"username": username, "password": password}
            )
            data = self._handle_response(response)
            
            if "access_token" in data:
                st.session_state.access_token = data["access_token"]
                st.session_state.logged_in = True
                return True
            return False
        except Exception as e:
            st.error(f"Login failed: {str(e)}")
            return False
    
    def signup(self, email: str, username: str, password: str, full_name: str) -> bool:
        """Register a new user"""
        try:
            response = requests.post(
                f"{self.base_url}/signup",
                json={
                    "email": email,
                    "username": username,
                    "password": password,
                    "full_name": full_name
                }
            )
            data = self._handle_response(response)
            return True
        except Exception as e:
            st.error(f"Signup failed: {str(e)}")
            return False
            
    def logout(self) -> None:
        """Clear user session"""
        if "access_token" in st.session_state:
            del st.session_state.access_token
        if "logged_in" in st.session_state:
            del st.session_state.logged_in
            

class FolderService(APIService):
    """Service for folder operations"""
    
    def get_folders(self) -> List[Dict[str, Any]]:
        """Get all folders for current user"""
        try:
            response = requests.get(
                f"{self.base_url}/folders/",
                headers=self._get_headers()
            )
            return self._handle_response(response)
        except Exception as e:
            st.error(f"Failed to get folders: {str(e)}")
            return []
    
    def create_folder(self, name: str, description: str = "") -> Dict[str, Any]:
        """Create a new folder"""
        try:
            response = requests.post(
                f"{self.base_url}/folders/",
                headers=self._get_headers(),
                json={"name": name, "description": description}
            )
            return self._handle_response(response)
        except Exception as e:
            st.error(f"Failed to create folder: {str(e)}")
            return {}
    
    def delete_folder(self, folder_id: int) -> bool:
        """Delete a folder"""
        try:
            response = requests.delete(
                f"{self.base_url}/folders/{folder_id}",
                headers=self._get_headers()
            )
            self._handle_response(response)
            return True
        except Exception as e:
            st.error(f"Failed to delete folder: {str(e)}")
            return False
    
    def get_folder(self, folder_id: int) -> Dict[str, Any]:
        """Get folder details"""
        try:
            response = requests.get(
                f"{self.base_url}/folders/{folder_id}",
                headers=self._get_headers()
            )
            return self._handle_response(response)
        except Exception as e:
            st.error(f"Failed to get folder details: {str(e)}")
            return {}


class ResumeService(APIService):
    """Service for resume operations"""
    
    def upload_resumes(self, folder_id: int, files) -> List[Dict[str, Any]]:
        """Upload resumes to a folder"""
        try:
            files_data = [("files", (f.name, f.getvalue(), f"application/{f.type}")) for f in files]
            
            response = requests.post(
                f"{self.base_url}/folders/{folder_id}/upload_resumes",
                headers=self._get_headers(),
                files=files_data
            )
            return self._handle_response(response)
        except Exception as e:
            st.error(f"Failed to upload resumes: {str(e)}")
            return []
    
    def get_resumes_by_folder(self, folder_id: int) -> List[Dict[str, Any]]:
        """Get all resumes in a folder"""
        try:
            response = requests.get(
                f"{self.base_url}/folders/{folder_id}/resumes",
                headers=self._get_headers()
            )
            return self._handle_response(response)
        except Exception as e:
            st.error(f"Failed to get resumes: {str(e)}")
            return []


class JobService(APIService):
    """Service for job operations"""
    
    def get_jobs(self) -> List[Dict[str, Any]]:
        """Get all jobs for current user"""
        try:
            response = requests.get(
                f"{self.base_url}/jobs/",
                headers=self._get_headers()
            )
            return self._handle_response(response)
        except Exception as e:
            st.error(f"Failed to get jobs: {str(e)}")
            return []
    
    def create_job(self, title: str, description: str, required_skills: List[str]) -> Dict[str, Any]:
        """Create a new job"""
        try:
            response = requests.post(
                f"{self.base_url}/jobs/",
                headers=self._get_headers(),
                json={
                    "title": title, 
                    "description": description,
                    "required_skills": required_skills
                }
            )
            return self._handle_response(response)
        except Exception as e:
            st.error(f"Failed to create job: {str(e)}")
            return {}
    
    def delete_job(self, job_id: int) -> bool:
        """Delete a job"""
        try:
            response = requests.delete(
                f"{self.base_url}/jobs/{job_id}",
                headers=self._get_headers()
            )
            self._handle_response(response)
            return True
        except Exception as e:
            st.error(f"Failed to delete job: {str(e)}")
            return False
    
    def get_job(self, job_id: int) -> Dict[str, Any]:
        """Get job details"""
        try:
            response = requests.get(
                f"{self.base_url}/jobs/{job_id}",
                headers=self._get_headers()
            )
            return self._handle_response(response)
        except Exception as e:
            st.error(f"Failed to get job details: {str(e)}")
            return {}
    
    def rank_candidates(self, job_id: int, folder_id: Optional[int] = None, top_n: Optional[int] = None) -> List[Dict[str, Any]]:
        """Rank candidates for a job"""
        try:
            params = {"job_id": job_id}
            if folder_id:
                params["folder_id"] = folder_id
            if top_n:
                params["top_n"] = top_n
                
            response = requests.get(
                f"{self.base_url}/jobs/candidates/rank",
                headers=self._get_headers(),
                params=params
            )
            return self._handle_response(response)
        except Exception as e:
            st.error(f"Failed to rank candidates: {str(e)}")
            return []


class SearchService(APIService):
    """Service for search operations"""
    
    def search_resumes(self, query: str, folder_id: Optional[int] = None, limit: int = 10) -> Dict[str, Any]:
        """Search for resumes"""
        try:
            params = {"query": query, "limit": limit}
            if folder_id:
                params["folder_id"] = folder_id
                
            response = requests.get(
                f"{self.base_url}/search/resumes",
                headers=self._get_headers(),
                params=params
            )
            return self._handle_response(response)
        except Exception as e:
            st.error(f"Search failed: {str(e)}")
            return {"results": [], "total": 0}


# ======= UI Components =======
class BaseUI:
    """Base class for UI components"""
    
    @staticmethod
    def show_header(title: str, description: str = None):
        """Display a header with optional description"""
        st.title(title)
        if description:
            st.markdown(description)
        st.divider()


class AuthUI(BaseUI):
    """UI components for authentication"""
    
    def __init__(self, auth_service: AuthService):
        self.auth_service = auth_service
    
    def show_login_form(self):
        """Display login form"""
        self.show_header("Login")
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                if username and password:
                    success = self.auth_service.login(username, password)
                    if success:
                        st.success("Login successful!")
                        st.rerun()
                else:
                    st.error("Please fill in all fields")
    
    def show_signup_form(self):
        """Display signup form"""
        self.show_header("Create Account")
        
        with st.form("signup_form"):
            full_name = st.text_input("Full Name")
            email = st.text_input("Email")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submit = st.form_submit_button("Sign Up")
            
            if submit:
                if full_name and email and username and password and confirm_password:
                    if password != confirm_password:
                        st.error("Passwords do not match")
                    else:
                        success = self.auth_service.signup(email, username, password, full_name)
                        if success:
                            st.success("Account created successfully! Please login.")
                            st.session_state.auth_page = "login"
                            st.rerun()
                else:
                    st.error("Please fill in all fields")
    
    def show_auth_switcher(self):
        """Display authentication page switcher"""
        if st.session_state.get("auth_page") == "signup":
            self.show_signup_form()
            st.markdown("Already have an account? [Login](javascript:void(0))")
            if st.button("Back to Login"):
                st.session_state.auth_page = "login"
                st.rerun()
        else:
            self.show_login_form()
            st.markdown("Don't have an account? [Sign Up](javascript:void(0))")
            if st.button("Create Account"):
                st.session_state.auth_page = "signup"
                st.rerun()


class FolderUI(BaseUI):
    """UI components for folder management"""
    
    def __init__(self, folder_service: FolderService):
        self.folder_service = folder_service
    
    def show_folders_list(self):
        """Display list of folders"""
        self.show_header("Resume Folders")
        
        # Create new folder button
        with st.expander("Create New Folder"):
            with st.form("new_folder_form"):
                name = st.text_input("Folder Name")
                description = st.text_area("Description")
                submit = st.form_submit_button("Create Folder")
                
                if submit and name:
                    new_folder = self.folder_service.create_folder(name, description)
                    if new_folder:
                        st.success(f"Folder '{name}' created successfully!")
                        st.rerun()
        
        # List folders
        folders = self.folder_service.get_folders()
        
        if not folders:
            st.info("No folders found. Create one to get started!")
            return
        
        for folder in folders:
            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                st.markdown(f"### {folder['name']}")
                st.markdown(folder.get('description', ''))
            
            with col2:
                if st.button("Open", key=f"open_{folder['id']}"):
                    st.session_state.current_folder = folder['id']
                    st.session_state.current_page = "folder_details"
                    st.rerun()
            
            with col3:
                if st.button("Delete", key=f"delete_{folder['id']}"):
                    if self.folder_service.delete_folder(folder['id']):
                        st.success(f"Folder '{folder['name']}' deleted successfully!")
                        st.rerun()
            
            st.divider()
    
    def show_folder_details(self, folder_id: int, resume_service: ResumeService):
        """Display folder details with resumes"""
        folder = self.folder_service.get_folder(folder_id)
        
        if not folder:
            st.error("Folder not found")
            if st.button("Back to Folders"):
                st.session_state.current_page = "folders"
                st.rerun()
            return
        
        self.show_header(f"Folder: {folder['name']}", folder.get('description', ''))
        
        # Back button
        if st.button("← Back to Folders"):
            st.session_state.current_page = "folders"
            st.rerun()
        
        # Upload resumes section
        with st.expander("Upload Resumes"):
            uploaded_files = st.file_uploader(
                "Upload PDF or DOCX resumes", 
                type=["pdf", "docx"], 
                accept_multiple_files=True
            )
            
            if uploaded_files and st.button("Upload Selected Files"):
                with st.spinner("Uploading and parsing resumes..."):
                    uploaded = resume_service.upload_resumes(folder_id, uploaded_files)
                    if uploaded:
                        st.success(f"Successfully uploaded {len(uploaded)} resume(s)!")
                        st.rerun()
        
        # Resumes list
        st.subheader("Resumes")
        resumes = resume_service.get_resumes_by_folder(folder_id)
        
        if not resumes:
            st.info("No resumes in this folder. Upload some to get started!")
            return
        
        # DEBUG: Display raw data structure of the first resume
        if resumes:
            st.expander("Debug: Resume Data Structure", expanded=False).json(resumes[0])
        
        # Display resumes in a table
        resume_data = []
        for resume in resumes:
            candidate_name = resume.get('candidate_name', 'Unknown')
            candidate_email = resume.get('candidate_email', '-')

            # Try parsed_metadata if direct fields are not available
            parsed_metadata = resume.get('parsed_metadata', {})
            if isinstance(parsed_metadata, dict):
                personal_info = parsed_metadata.get('personal_info', {})
                if isinstance(personal_info, dict):
                    if personal_info.get('name') and candidate_name == 'Unknown':
                        candidate_name = personal_info.get('name')
                    if personal_info.get('email') and candidate_email == '-':
                        candidate_email = personal_info.get('email')

            # Get skills from various possible locations
            skills = []
            if isinstance(resume.get('skills', None), list):
                skills = resume.get('skills', [])
            elif parsed_metadata and isinstance(parsed_metadata.get('skills', None), list):
                skills = parsed_metadata.get('skills', [])

            skills_str = ", ".join(skills[:3]) + (f" +{len(skills)-3} more" if len(skills) > 3 else "")

            resume_data.append({
                "ID": resume['id'],
                "Name": candidate_name,
                "Email": candidate_email,
                "Skills": skills_str,
                "Filename": resume['filename']
            })

        # Display the table
        st.write("---")
        st.write("Resume Data Table:")
        st.dataframe(resume_data, use_container_width=True)

class JobUI(BaseUI):
    """UI components for job management"""
    
    def __init__(self, job_service: JobService):
        self.job_service = job_service
    
    def show_jobs_list(self):
        """Display list of jobs"""
        self.show_header("Job Listings")
        
        # Create new job button
        with st.expander("Create New Job"):
            with st.form("new_job_form"):
                title = st.text_input("Job Title")
                description = st.text_area("Job Description")
                skills_input = st.text_input("Required Skills (comma separated)")
                submit = st.form_submit_button("Create Job")
                
                if submit and title and description:
                    skills = [skill.strip() for skill in skills_input.split(",") if skill.strip()]
                    new_job = self.job_service.create_job(title, description, skills)
                    if new_job:
                        st.success(f"Job '{title}' created successfully!")
                        st.rerun()
        
        # List jobs
        jobs = self.job_service.get_jobs()
        
        if not jobs:
            st.info("No jobs found. Create one to get started!")
            return
        
        for job in jobs:
            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                st.markdown(f"### {job['title']}")
                st.markdown(job.get('description', '')[:100] + "..." if len(job.get('description', '')) > 100 else job.get('description', ''))
                skills = job.get('required_skills', [])
                if skills:
                    st.markdown(f"**Skills:** {', '.join(skills)}")
            
            with col2:
                if st.button("View", key=f"view_{job['id']}"):
                    st.session_state.current_job = job['id']
                    st.session_state.current_page = "job_details"
                    st.rerun()
            
            with col3:
                if st.button("Delete", key=f"delete_{job['id']}"):
                    if self.job_service.delete_job(job['id']):
                        st.success(f"Job '{job['title']}' deleted successfully!")
                        st.rerun()
            
            st.divider()
    
    def show_job_details(self, job_id: int, folder_service: FolderService):
        """Display job details with ranking options"""
        job = self.job_service.get_job(job_id)
        
        if not job:
            st.error("Job not found")
            if st.button("Back to Jobs"):
                st.session_state.current_page = "jobs"
                st.rerun()
            return
        
        self.show_header(f"Job: {job['title']}")
        
        # Back button
        if st.button("← Back to Jobs"):
            st.session_state.current_page = "jobs"
            st.rerun()
        
        # Job details
        st.subheader("Description")
        st.markdown(job.get('description', ''))
        
        if job.get('required_skills'):
            st.subheader("Required Skills")
            skills_cols = st.columns(3)
            for i, skill in enumerate(job['required_skills']):
                skills_cols[i % 3].markdown(f"- {skill}")
        
        # Ranking section
        st.subheader("Rank Candidates")
        
        # Get folders for selection
        folders = folder_service.get_folders()
        folder_options = {f"{folder['name']} (ID: {folder['id']})": folder['id'] for folder in folders}
        
        if not folder_options:
            st.warning("No resume folders available. Create a folder and upload resumes first.")
            return
        
        col1, col2 = st.columns([3, 1])
        with col1:
            selected_folder = st.selectbox(
                "Select Resume Folder", 
                options=list(folder_options.keys()),
                key="rank_folder_select"
            )
        
        with col2:
            top_n = st.number_input("Top N Candidates", min_value=1, value=10)
        
        if st.button("Rank Candidates"):
            if selected_folder:
                folder_id = folder_options[selected_folder]
                with st.spinner("Ranking candidates..."):
                    ranked_candidates = self.job_service.rank_candidates(
                        job_id, folder_id, top_n
                    )
                    
                    if ranked_candidates:
                        st.success(f"Found {len(ranked_candidates)} matching candidates!")
                        self._display_ranked_candidates(ranked_candidates)
                    else:
                        st.info("No matching candidates found.")
    
    def _display_ranked_candidates(self, candidates: List[Dict[str, Any]]):
        """Display ranked candidates without showing the match score"""
        for i, candidate in enumerate(candidates):
            col1, col2 = st.columns([1, 3])
            
            with col1:
                st.markdown(f"### #{i+1}")
            
            with col2:
                st.markdown(f"### {candidate.get('candidate_name', 'Unknown')}")
                st.markdown(f"**Email:** {candidate.get('candidate_email', '-')}")

                skills = candidate.get('skills', [])
                if skills:
                    st.markdown("**Skills:**")
                    skills_text = ", ".join(skills[:10])
                    if len(skills) > 10:
                        skills_text += f" +{len(skills)-10} more"
                    st.markdown(skills_text)
            
            st.divider()


class SearchUI(BaseUI):
    """UI components for search functionality"""
    
    def __init__(self, search_service: SearchService, folder_service: FolderService):
        self.search_service = search_service
        self.folder_service = folder_service
    
    def show_search_page(self):
        """Display search page"""
        self.show_header("Search Resumes")
        
        # Get folders for filtering
        folders = self.folder_service.get_folders()
        folder_options = {"All Folders": None}
        folder_options.update({f"{folder['name']}": folder['id'] for folder in folders})
        
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            query = st.text_input("Search for skills, experience, or keywords")
        
        with col2:
            selected_folder = st.selectbox(
                "Filter by Folder", 
                options=list(folder_options.keys()),
                key="search_folder_select"
            )
        
        with col3:
            limit = st.number_input("Results Limit", min_value=1, max_value=100, value=10)
        
        if st.button("Search") and query:
            folder_id = folder_options[selected_folder]
            with st.spinner("Searching..."):
                results = self.search_service.search_resumes(query, folder_id, limit)
                
                if results and results.get("results"):
                    st.success(f"Found {results['total']} results!")
                    self._display_search_results(results['results'])
                else:
                    st.info("No matching resumes found.")
    
    def _display_search_results(self, results: List[Dict[str, Any]]):
        """Display search results"""
        for result in results:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"### {result.get('candidate_name', 'Unknown')}")
                st.markdown(f"**Email:** {result.get('candidate_email', '-')}")
                st.markdown(f"**File:** {result.get('filename', '-')}")

                skills = result.get('skills', [])
                if skills:
                    st.markdown("**Skills:**")
                    skills_text = ", ".join(skills[:10])
                    if len(skills) > 10:
                        skills_text += f" +{len(skills)-10} more"
                    st.markdown(skills_text)
            
            with col2:
                st.markdown("### Score")
                score = result.get('search_score', 0) / 100  # Normalize score to [0.0, 1.0]
                st.progress(score)
                st.markdown(f"**{score * 100:.2f}%**")  # Display as a percentage
            
            st.divider()


class DashboardUI(BaseUI):
    """UI components for dashboard"""
    
    def __init__(self, folder_service: FolderService, job_service: JobService):
        self.folder_service = folder_service
        self.job_service = job_service
    
    def show_dashboard(self):
        """Display dashboard with overview"""
        self.show_header("Dashboard")
        
        col1, col2 = st.columns(2)
        
        with col1:
            folders = self.folder_service.get_folders()
            st.metric("Resume Folders", len(folders))
            
            if folders:
                with st.expander("Quick Access Folders"):
                    for folder in folders[:3]:
                        if st.button(folder['name'], key=f"dash_folder_{folder['id']}"):
                            st.session_state.current_folder = folder['id']
                            st.session_state.current_page = "folder_details"
                            st.rerun()
        
        with col2:
            jobs = self.job_service.get_jobs()
            st.metric("Active Jobs", len(jobs))
            
            if jobs:
                with st.expander("Quick Access Jobs"):
                    for job in jobs[:3]:
                        if st.button(job['title'], key=f"dash_job_{job['id']}"):
                            st.session_state.current_job = job['id']
                            st.session_state.current_page = "job_details"
                            st.rerun()
        
        # Actions section
        st.subheader("Quick Actions")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📁 Create New Folder"):
                st.session_state.current_page = "folders"
                st.rerun()
        
        with col2:
            if st.button("📝 Post New Job"):
                st.session_state.current_page = "jobs"
                st.rerun()
        
        with col3:
            if st.button("🔍 Search Resumes"):
                st.session_state.current_page = "search"
                st.rerun()


# ======= Application Controller =======
class AppController:
    """Main application controller"""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        # Initialize services
        self.auth_service = AuthService(api_url)
        self.folder_service = FolderService(api_url)
        self.resume_service = ResumeService(api_url)
        self.job_service = JobService(api_url)
        self.search_service = SearchService(api_url)
        
        # Initialize UI components
        self.auth_ui = AuthUI(self.auth_service)
        self.folder_ui = FolderUI(self.folder_service)
        self.job_ui = JobUI(self.job_service)
        self.search_ui = SearchUI(self.search_service, self.folder_service)
        self.dashboard_ui = DashboardUI(self.folder_service, self.job_service)
        
        # Set default session state values
        if "current_page" not in st.session_state:
            st.session_state.current_page = "dashboard"
        
        if "auth_page" not in st.session_state:
            st.session_state.auth_page = "login"
    
    def render_sidebar(self):
        """Render the sidebar navigation"""
        st.sidebar.title("ResumeMatch Pro")
        
        if st.session_state.get("logged_in"):
            st.sidebar.markdown("---")
            
            # Navigation
            if st.sidebar.button("📊 Dashboard"):
                st.session_state.current_page = "dashboard"
                st.rerun()
            
            if st.sidebar.button("📁 Resume Folders"):
                st.session_state.current_page = "folders"
                st.rerun()
            
            if st.sidebar.button("🏢 Job Listings"):
                st.session_state.current_page = "jobs"
                st.rerun()
            
            if st.sidebar.button("🔍 Search"):
                st.session_state.current_page = "search"
                st.rerun()
            
            st.sidebar.markdown("---")
            
            # Logout button
            if st.sidebar.button("🚪 Logout"):
                self.auth_service.logout()
                st.rerun()
    
    def run(self):
        """Run the application"""
        self.render_sidebar()
        
        if not st.session_state.get("logged_in"):
            self.auth_ui.show_auth_switcher()
            return
        
        # Route to appropriate page
        if st.session_state.current_page == "dashboard":
            self.dashboard_ui.show_dashboard()
        
        elif st.session_state.current_page == "folders":
            self.folder_ui.show_folders_list()
        
        elif st.session_state.current_page == "folder_details" and "current_folder" in st.session_state:
            self.folder_ui.show_folder_details(st.session_state.current_folder, self.resume_service)
        
        elif st.session_state.current_page == "jobs":
            self.job_ui.show_jobs_list()
        
        elif st.session_state.current_page == "job_details" and "current_job" in st.session_state:
            self.job_ui.show_job_details(st.session_state.current_job, self.folder_service)
        
        elif st.session_state.current_page == "search":
            self.search_ui.show_search_page()
        
        else:
            st.error("Page not found")
            st.session_state.current_page = "dashboard"
            st.rerun()


# ======= Main Execution =======
if __name__ == "__main__":
    # Set up environment variables
    api_url = os.environ.get("API_URL", "http://localhost:8000")
    
    # Initialize and run the application
    app = AppController(api_url)
    app.run()