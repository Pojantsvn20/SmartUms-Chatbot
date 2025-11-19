import { initializeApp } from "https://www.gstatic.com/firebasejs/11.0.1/firebase-app.js";
import { getFirestore, collection, addDoc, serverTimestamp } from "https://www.gstatic.com/firebasejs/11.0.1/firebase-firestore.js";

const firebaseConfig = {
    apiKey: "AIzaSyCfK4nCoo-DVH_K5zLspglcnFjvLK1CL2A",
    authDomain: "smartums-feedback.firebaseapp.com",
    projectId: "smartums-feedback",
    storageBucket: "smartums-feedback.firebasestorage.app",
    messagingSenderId: "814627859215",
    appId: "1:814627859215:web:92b919f7ac350fae6e2c7a",
    measurementId: "G-372D93YSL0"
};
const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

const GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzrExaldwikulUW8uKlXvq_Bkypytf3vsTcli_Q3cyiBWAplXmx8ObGluM85UY8PumD/exec";

const feedbackForm = document.getElementById('feedbackForm');
const ratingStars = document.querySelectorAll('#ratingStars .star');
const fbRatingInput = document.getElementById('fbRating');

function updateStars(rating) {
    ratingStars.forEach(star => {
        if (parseInt(star.dataset.rating) <= rating) {
            star.classList.add('active');
        } else {
            star.classList.remove('active');
        }
    });
}

ratingStars.forEach(star => {
    star.addEventListener('click', () => {
        fbRatingInput.value = star.dataset.rating;
        updateStars(parseInt(star.dataset.rating));
    });
});


feedbackForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const submitBtn = e.target.querySelector('.feedback-submit-btn');
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = '⏳ Submitting...';
    const feedback = {
        name: document.getElementById('fbName').value,
        email: document.getElementById('fbEmail').value,
        rating: parseInt(document.getElementById('fbRating').value),
        category: document.getElementById('fbCategory').value,
        message: document.getElementById('fbMessage').value,
        recommend: document.getElementById('fbRecommend').checked,
        timestamp: serverTimestamp(),
        submittedAt: new Date().toISOString()
    };
    try {
        // 1. Save to Firestore
        await addDoc(collection(db, "feedbacks"), feedback);

        // 2. Save to Flask/MySQL
        const mysqlRes = await fetch('/submit-feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: feedback.name,
                email: feedback.email,
                rating: feedback.rating,
                category: feedback.category,
                message: feedback.message,
                recommend: feedback.recommend,
                submittedAt: feedback.submittedAt
            })
        });
        const mysqlData = await mysqlRes.json();
        if (!mysqlData.success) throw new Error('MySQL: ' + (mysqlData.error || 'Unknown error'));

        // 3. Send email notification via Google Apps Script
        const emailData = {
            name: feedback.name,
            email: feedback.email,
            rating: feedback.rating,
            category: feedback.category,
            message: feedback.message,
            recommend: feedback.recommend ? 'Yes' : 'No',
            submittedAt: feedback.submittedAt
        };
        await fetch(GOOGLE_SCRIPT_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'text/plain' },
            body: JSON.stringify(emailData)
        });

        const successMsg = document.getElementById('successMessage');
        successMsg.textContent = '✅ Thank you! Your feedback has been saved and sent to our team.';
        successMsg.classList.add('show');
        feedbackForm.reset();
        updateStars(5);
        setTimeout(() => {
            window.location.href = '/';
        }, 2500);
    } catch (error) {
        const successMsg = document.getElementById('successMessage');
        successMsg.style.background = '#f8d7da';
        successMsg.style.color = '#721c24';
        successMsg.textContent = '⚠️ Error: ' + error.message;
        successMsg.classList.add('show');
        setTimeout(() => {
            successMsg.classList.remove('show');
            successMsg.style.background = '#d4edda';
            successMsg.style.color = '#155724';
        }, 5000);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
});

// Initialize
updateStars(5);
