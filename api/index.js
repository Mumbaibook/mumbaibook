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
        const { data: existingUser, error: checkError } = await supabase
            .from('users')
            .select('username')
            .eq('username', username)
            .single();

        if (checkError && checkError.code !== 'PGRST116') { // PGRST116 means no rows returned
            console.error('Check user error:', checkError);
            return res.status(500).json({ error: 'Failed to check username' });
        }

        if (existingUser) {
            return res.status(400).json({ error: 'Username already exists' });
        }

        // Hash password
        const hashedPassword = await bcrypt.hash(password, 10);

        // Insert new user
        const { data: newUser, error: insertError } = await supabase
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

        if (insertError) {
            console.error('Insert error:', insertError);
            return res.status(500).json({ error: 'Failed to register user' });
        }

        // Create initial session
        const deviceId = 'dev_' + Math.random().toString(36).substr(2, 9);
        const { error: sessionError } = await supabase
            .from('user_sessions')
            .insert([
                {
                    user_id: newUser.id,
                    device_id: deviceId
                }
            ]);

        if (sessionError) {
            console.error('Session creation error:', sessionError);
            // Don't return error here, user is still created
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

// Login endpoint
app.post('/api/login', async (req, res) => {
    try {
        const { username, password } = req.body;
        
        if (!username || !password) {
            return res.status(400).json({ error: 'Username and password are required' });
        }

        console.log('Login attempt for username:', username);

        // Get user
        const { data: user, error: userError } = await supabase
            .from('users')
            .select('*')
            .eq('username', username)
            .single();

        if (userError || !user) {
            console.error('User not found:', username);
            return res.status(401).json({ error: 'Invalid username or password' });
        }

        // Verify password
        const passwordMatch = await bcrypt.compare(password, user.password);
        if (!passwordMatch) {
            console.error('Password mismatch for user:', username);
            return res.status(401).json({ error: 'Invalid username or password' });
        }

        // Create new session
        const deviceId = 'dev_' + Math.random().toString(36).substr(2, 9);
        const { error: sessionError } = await supabase
            .from('user_sessions')
            .insert([
                {
                    user_id: user.id,
                    device_id: deviceId
                }
            ]);

        if (sessionError) {
            console.error('Session creation error:', sessionError);
            // Continue anyway as login is successful
        }

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
