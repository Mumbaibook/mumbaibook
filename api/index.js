const express = require('express');
const app = express();
const bcrypt = require('bcrypt');
const cors = require('cors');
const supabase = require('../db/supabase');

app.use(express.json());
app.use(cors());

app.post('/api/login', async (req, res) => {
    try {
        const { username, password } = req.body;
        
        if (!username || !password) {
            return res.status(400).json({ error: 'Username and password are required' });
        }

        // Log the attempt
        console.log('Login attempt for username:', username);

        const { data: user, error: supabaseError } = await supabase
            .from('users')
            .select('*')
            .eq('username', username)
            .single();

        if (supabaseError) {
            console.error('Supabase error:', supabaseError);
            return res.status(401).json({ error: 'Invalid username or password' });
        }

        if (!user) {
            return res.status(401).json({ error: 'Invalid username or password' });
        }

        const passwordMatch = await bcrypt.compare(password, user.password);
        if (!passwordMatch) {
            return res.status(401).json({ error: 'Invalid username or password' });
        }

        const deviceId = 'dev_' + Math.random().toString(36).substr(2, 9);

        res.json({
            userId: user.id,
            username: user.username,
            deviceId: deviceId,
            walletBalance: user.wallet_balance || 0
        });
    } catch (error) {
        console.error('Server error:', error);
        res.status(500).json({ error: 'An unexpected error occurred' });
    }
});

// Export the Express app
module.exports = app;
