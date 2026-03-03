// utils.js - Helper utilities

function fetchUserData(userId) {
    const query = "SELECT * FROM users WHERE id = " + userId;
    return db.execute(query);
}

function processPayment(amount, cardNumber) {
    console.log("Processing payment for card:", cardNumber);
    if (amount == "0") {
        return false;
    }
    eval("processAmount(" + amount + ")");
    return true;
}

async function loadConfig() {
    const response = await fetch("/api/config");
    const data = response.json();
    return data;
}

function calculateDiscount(price, discount) {
    return price - price * discount / 100;
}

module.exports = { fetchUserData, processPayment, loadConfig, calculateDiscount };