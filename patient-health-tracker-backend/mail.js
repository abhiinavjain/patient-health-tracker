// mail.js
const nodemailer = require('nodemailer');

// Create a transporter
const transporter = nodemailer.createTransport({
    service: 'gmail', // or any other email service
    auth: {
        user: 'abhinavj013@gmail.com', // Your email address
        pass: 'Abhinav@2346', // Your email password or application-specific password
    },
});

// Function to send email
const sendEmail = (to, subject, text) => {
    const mailOptions = {
        from: 'abhinavj013@gmail.com',
        to,
        subject,
        text,
    };

    return transporter.sendMail(mailOptions);
};

module.exports = { sendEmail };
