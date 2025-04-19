const { createClient } = require('@supabase/supabase-js');

// Use the same values as in public/config.js
const supabaseUrl = 'https://eghyeniuubkgbumuhlbq.supabase.co';
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVnaHllbml1dWJrZ2J1bXVobGJxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQ5NzM1NzMsImV4cCI6MjA2MDU0OTU3M30.qFfsZTh_r9vX0mQl-6Am2R5vo2HdCFPWjZVjU6wiwSg';

const supabase = createClient(supabaseUrl, supabaseKey);

module.exports = supabase;


