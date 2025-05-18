require('dotenv').config();
const express = require('express');
const cors = require('cors');
const mysql = require('mysql2');
const bodyParser = require('body-parser');
const nodemailer = require('nodemailer');

const app = express();

// ✅ CORS configuration
const allowedOrigins = ['http://localhost:5000', 'http://127.0.0.1:5000'];
app.use(cors({
    origin: function (origin, callback) {
        if (!origin || allowedOrigins.includes(origin)) {
            callback(null, true);
        } else {
            callback(new Error('Not allowed by CORS'));
        }
    },
    methods: ['GET', 'POST'],
    credentials: true
}));

app.use(bodyParser.json());

// MySQL connection
const db = mysql.createConnection({
    host: 'localhost',
    user: 'root',
    password: 'Priya123',
    database: 'register_db'
});

db.connect(err => {
    if (err) {
        console.error('Error connecting to MySQL:', err);
        process.exit(1);
    }
    console.log('MySQL connected!');
});

// Register route
app.post('/api/register', (req, res) => {
    const { name, email, phone, password } = req.body;

    const checkEmail = 'SELECT * FROM users WHERE email = ?';
    db.query(checkEmail, [email], (err, results) => {
        if (err) return res.status(500).json({ message: 'Database error' });

        if (results.length > 0) {
            return res.status(400).json({ message: 'Email already registered' });
        }

        const insertUser = 'INSERT INTO users (name, email, phone, password) VALUES (?, ?, ?, ?)';
        db.query(insertUser, [name, email, phone, password], (err, result) => {
            if (err) return res.status(500).json({ message: 'Error registering user' });

            // Send welcome email
            const transporter = nodemailer.createTransport({
                service: 'gmail',
                auth: {
                    user: process.env.EMAIL_USER,
                    pass: process.env.EMAIL_PASS
                }
            });

            const mailOptions = {
                from: process.env.EMAIL_USER,
                to: email,
                subject: 'Welcome to TomatoCare!',
                text: `Hi ${name},\n\nThanks for registering with TomatoCare! We're here to help you diagnose and treat your plant diseases easily.\n\nRegards,\nTomatoCare Team`
            };

            transporter.sendMail(mailOptions, (err, info) => {
                if (err) {
                    console.log('Email error:', err);
                    return res.status(500).json({ message: 'User registered, but email sending failed' });
                }
                console.log('Email sent:', info.response);
                res.status(200).json({ message: 'Registered successfully and welcome email sent' });
            });
        });
    });
});

// Login route
app.post('/api/login', (req, res) => {
    const { email, password } = req.body;

    const loginQuery = 'SELECT * FROM users WHERE email = ? AND password = ?';
    db.query(loginQuery, [email, password], (err, results) => {
        if (err) {
            console.log('Error:', err);
            return res.status(500).json({ message: 'Login error' });
        }

        if (results.length === 0) {
            return res.status(401).json({ message: 'Invalid credentials' });
        }

        res.status(200).json({ message: 'Login successful', user: results[0] });
    });
});

// Dashboard route
app.get('/api/dashboard/:userId', (req, res) => {
    const userId = req.params.userId;

    const historyQuery = `
        SELECT prediction, confidence, notes, created_at 
        FROM history 
        WHERE user_id = ? 
        ORDER BY created_at DESC
    `;

    db.query(historyQuery, [userId], (err, results) => {
        if (err) return res.status(500).json({ message: 'Error fetching history' });

        const totalScans = results.length;
        const diseaseCount = results.filter(scan => scan.prediction !== 'Healthy').length;
        const lastScan = totalScans > 0 ? results[0].created_at : null;

        res.status(200).json({
            history: results,
            totalScans,
            diseaseCount,
            lastScan
        });
    });
});

app.listen(3000, () => {
    console.log('Server running on port 3000');
});
