const express = require('express');
const app = express();
const bcrypt = require('bcrypt');
const cors = require('cors');
const supabase = require('../db/supabase');
const path = require('path');

// Middleware
app.use(cors({
    origin: process.env.NODE_ENV === 'production' 
        ? ['https://mumbai-book.vercel.app']
        : ['http://localhost:3000'],
    credentials: true
}));

app.use(express.json());

// Serve static files from the public directory
app.use(express.static('public'));

// Root route to serve index.html
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, '../public/index.html'));
});

// Login endpoint
app.post('/api/login', async (req, res) => {
    try {
        const { username, password } = req.body;
        
        if (!username || !password) {
            return res.status(400).json({ error: 'Username and password are required' });
        }

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

        return res.status(200).json({
            userId: user.id,
            username: user.username,
            deviceId: deviceId,
            walletBalance: user.wallet_balance || 0
        });
    } catch (error) {
        console.error('Server error:', error);
        return res.status(500).json({ error: 'An unexpected error occurred. Please try again.' });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});

module.exports = app;
