const CONFIG = {
    API_URL: window.location.hostname === 'localhost' 
        ? 'http://localhost:3000' 
        : 'https://mumbaibook-git-main-mumbai-books-projects.vercel.app',
    SUPABASE_URL: 'https://eghyeniuubkgbumuhlbq.supabase.co',
    SUPABASE_ANON_KEY: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVnaHllbml1dWJrZ2J1bXVobGJxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQ5NzM1NzMsImV4cCI6MjA2MDU0OTU3M30.qFfsZTh_r9vX0mQl-6Am2R5vo2HdCFPWjZVjU6wiwSg'
};

// Add error handling utility
const handleApiError = (error) => {
    console.error('API Error:', error);
    if (error.message === 'Failed to fetch') {
        alert('Network error. Please check your internet connection.');
    } else {
        alert(error.message || 'An error occurred. Please try again.');
    }
};

// Add authentication check utility
const checkAuth = () => {
    const user = JSON.parse(sessionStorage.getItem('currentUser'));
    if (!user) {
        window.location.href = 'index.html';
        return false;
    }
    return true;
};
