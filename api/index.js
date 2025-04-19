const express = require('express');
const app = express();
const bcrypt = require('bcrypt');
const cors = require('cors');
const supabase = require('../db/supabase');

app.use(express.json());
app.use(cors());

// Registration endpoint
app.post('/api/register', async (req, res) => {
    try {
        const { username, password, mobile } = req.body;
        
        if (!username || !password || !mobile) {
            return res.status(400).json({ error: 'All fields are required' });
        }

        // Check if username already exists
        const { data: existingUser } = await supabase
            .from('users')
            .select('username')
            .eq('username', username)
            .single();

        if (existingUser) {
            return res.status(400).json({ error: 'Username already exists' });
        }

        // Hash password
        const hashedPassword = await bcrypt.hash(password, 10);

        // Insert new user
        const { data: newUser, error } = await supabase
            .from('users')
            .insert([
                {
                    username,
                    password: hashedPassword,
                    mobile,
                    wallet_balance: 0
                }
            ])
            .select()
            .single();

        if (error) {
            console.error('Registration error:', error);
            return res.status(500).json({ error: 'Failed to register user' });
        }

        res.status(201).json({ 
            message: 'Registration successful',
            userId: newUser.id
        });

    } catch (error) {
        console.error('Server error:', error);
        res.status(500).json({ error: 'An unexpected error occurred' });
    }
});

// Existing login endpoint
app.post('/api/login', async (req, res) => {
    try {
        const { username, password } = req.body;
        
        if (!username || !password) {
            return res.status(400).json({ error: 'Username and password are required' });
        }

        console.log('Login attempt for username:', username);

        const { data: user, error: supabaseError } = await supabase
            .from('users')
            .select('*')
            .eq('username', username)
            .single();

        if (supabaseError || !user) {
            console.error('User not found:', username);
            return res.status(401).json({ error: 'Invalid username or password' });
        }

        const passwordMatch = await bcrypt.compare(password, user.password);
        if (!passwordMatch) {
            console.error('Password mismatch for user:', username);
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

module.exports = app;
