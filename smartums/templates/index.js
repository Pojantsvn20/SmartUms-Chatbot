const functions = require('firebase-functions');
const admin = require('firebase-admin');
const sgMail = require('@sendgrid/mail');

admin.initializeApp();
sgMail.setApiKey('YOUR_SENDGRID_API_KEY'); // Replace with your key

exports.sendFeedbackEmail = functions.firestore
  .document('feedbacks/{feedbackId}')
  .onCreate(async (snap, context) => {
    const feedback = snap.data();
    
    const msg = {
      to: 'universitusmart9@gmail.com',
      from: 'noreply@yourdomain.com', // Must be verified in SendGrid
      subject: `🔔 New Feedback from ${feedback.name}`,
      html: `
        <h2>New Feedback Received</h2>
        <p><strong>Name:</strong> ${feedback.name}</p>
        <p><strong>Email:</strong> ${feedback.email}</p>
        <p><strong>Rating:</strong> ${'⭐'.repeat(feedback.rating)}</p>
        <p><strong>Category:</strong> ${feedback.category}</p>
        <p><strong>Message:</strong></p>
        <p>${feedback.message}</p>
        <p><strong>Recommend:</strong> ${feedback.recommend ? 'Yes ✅' : 'No ❌'}</p>
        <p><strong>Time:</strong> ${new Date().toLocaleString()}</p>
      `
    };

    try {
      await sgMail.send(msg);
      console.log('Email sent successfully');
    } catch (error) {
      console.error('Error sending email:', error);
    }
  });