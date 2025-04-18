const { createClient } = require('@supabase/supabase-js');

// Use environment variables or fallback to the values from config.js
const supabaseUrl = process.env.SUPABASE_URL || 'https://eghyeniuubkgbumuhlbq.supabase.co';
const supabaseKey = process.env.SUPABASE_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVnaHllbml1dWJrZ2J1bXVobGJxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQ5NzM1NzMsImV4cCI6MjA2MDU0OTU3M30.qFfsZTh_r9vX0mQl-6Am2R5vo2HdCFPWjZVjU6wiwSg';

const supabase = createClient(supabaseUrl, supabaseKey, {
    auth: {
        autoRefreshToken: false,
        persistSession: false
    }
});

module.exports = supabase;




