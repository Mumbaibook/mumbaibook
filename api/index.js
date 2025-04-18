const express = require('express');
const app = express();
const bcrypt = require('bcrypt');
const cors = require('cors');
const supabase = require('../db/supabase');

// Update CORS configuration
app.use(cors({
    origin: process.env.NODE_ENV === 'production' 
        ? ['https://mumbaibook.vercel.app/']
        : ['http://localhost:3000'],
    credentials: true
}));

app.use(express.json());
app.use(express.static('public'));

// Add error handling middleware
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).json({ error: 'Something went wrong!' });
});

// Registration endpoint
app.post('/api/register', async (req, res) => {
    const { username, password, mobile } = req.body;
    
    try {
        const hashedPassword = await bcrypt.hash(password, 10);
        
        const { data, error } = await supabase
            .from('users')
            .insert([
                { 
                    username, 
                    password: hashedPassword, 
                    mobile,
                    wallet_balance: 0
                }
            ]);

        if (error) {
            if (error.code === '23505') { // unique violation
                res.status(400).json({ error: 'Username or mobile already exists' });
            } else {
                res.status(500).json({ error: 'Registration failed' });
            }
            return;
        }
        
        res.json({ message: 'Registration successful' });
    } catch (error) {
        res.status(500).json({ error: 'Registration failed' });
    }
});

// Login endpoint
app.post('/api/login', async (req, res) => {
    const { username, password } = req.body;
    
    try {
        const { data: user, error } = await supabase
            .from('users')
            .select('*')
            .eq('username', username)
            .single();

        if (error || !user) {
            res.status(401).json({ error: 'Invalid credentials' });
            return;
        }

        const passwordMatch = await bcrypt.compare(password, user.password);
        if (!passwordMatch) {
            res.status(401).json({ error: 'Invalid credentials' });
            return;
        }

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
            res.status(500).json({ error: 'Session creation failed' });
            return;
        }

        res.json({
            userId: user.id,
            username: user.username,
            deviceId: deviceId,
            walletBalance: user.wallet_balance
        });
    } catch (error) {
        res.status(500).json({ error: 'Login failed' });
    }
});

// Add these endpoints
app.post('/api/place-bet', async (req, res) => {
    const { userId, deviceId, gameId, numbers, amount, totalBet } = req.body;
    
    // Verify session
    db.get(`SELECT * FROM user_sessions WHERE user_id = ? AND device_id = ?`,
        [userId, deviceId],
        (err, session) => {
            if (err || !session) {
                res.status(401).json({ error: 'Invalid session' });
                return;
            }
            
            // Process bet in transaction
            db.serialize(() => {
                db.run('BEGIN TRANSACTION');
                
                // Update wallet
                db.run(`UPDATE users SET wallet_balance = wallet_balance - ? WHERE id = ?`,
                    [totalBet, userId],
                    function(err) {
                        if (err) {
                            db.run('ROLLBACK');
                            res.status(500).json({ error: 'Failed to process bet' });
                            return;
                        }
                        
                        // Insert bet record
                        db.run(`INSERT INTO bets (user_id, game_id, numbers, amount, total_amount)
                            VALUES (?, ?, ?, ?, ?)`,
                            [userId, gameId, JSON.stringify(numbers), amount, totalBet],
                            function(err) {
                                if (err) {
                                    db.run('ROLLBACK');
                                    res.status(500).json({ error: 'Failed to save bet' });
                                    return;
                                }
                                
                                db.run('COMMIT');
                                
                                // Get updated balance
                                db.get(`SELECT wallet_balance FROM users WHERE id = ?`,
                                    [userId],
                                    (err, user) => {
                                        if (err) {
                                            res.status(500).json({ error: 'Failed to get updated balance' });
                                            return;
                                        }
                                        
                                        res.json({ 
                                            success: true,
                                            newBalance: user.wallet_balance
                                        });
                                    }
                                );
                            }
                        );
                    }
                );
            });
        }
    );
});

app.get('/api/wallet/:userId', (req, res) => {
    const userId = req.params.userId;
    
    db.get(`SELECT wallet_balance FROM users WHERE id = ?`,
        [userId],
        (err, user) => {
            if (err || !user) {
                res.status(404).json({ error: 'User not found' });
                return;
            }
            res.json({ balance: user.wallet_balance });
        }
    );
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running on port ${PORT}`);
});

module.exports = app;
