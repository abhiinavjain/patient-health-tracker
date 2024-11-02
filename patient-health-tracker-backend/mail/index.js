const nodemailer = require('nodemailer');

// Create a transporter object using the default SMTP transport
const transporter = nodemailer.createTransport({
    service: 'gmail', // Change this if you're using a different email service
    auth: {
        user: process.env.EMAIL_USER, // Your email address (from your .env file)
        pass: process.env.EMAIL_PASS, // Your email password (from your .env file)
    },
});

// Function to send an email
const sendEmail = (to, subject, text) => {
    const mailOptions = {
        from: process.env.EMAIL_USER, // Sender address
        to, // List of receivers
        subject, // Subject line
        text, // Plain text body
    };

    // Send mail with defined transport object
    return transporter.sendMail(mailOptions)
        .then(info => {
            console.log('Email sent: ' + info.response);
            return info; // Return info if needed
        })
        .catch(error => {
            console.error('Error sending email:', error);
            throw error; // Rethrow the error if you need to handle it elsewhere
        });
};

module.exports = { sendEmail };
