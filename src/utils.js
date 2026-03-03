// utils.js - Helper utilities

/**
 * Fetch user data by ID using a parameterized query to prevent SQL injection.
 * @param {number|string} userId
 */
function fetchUserData(userId) {
    if (userId === undefined || userId === null) {
        throw new Error("userId is required");
    }
    // Use a parameterized query to prevent SQL injection
    const query = "SELECT * FROM users WHERE id = ?";
    return db.execute(query, [userId]);
}

/**
 * Process a payment for the given amount.
 * Card number is never logged to avoid leaking sensitive data.
 * @param {number|string} amount
 * @param {string} cardNumber
 */
function processPayment(amount, cardNumber) {
    if (amount === undefined || amount === null) {
        throw new Error("amount is required");
    }
    if (!cardNumber) {
        throw new Error("cardNumber is required");
    }

    // Never log sensitive payment details such as card numbers
    console.log("Processing payment...");

    // Use strict equality and numeric coercion to compare amount
    if (Number(amount) === 0) {
        return false;
    }

    // Call processAmount directly instead of using eval() to prevent code injection
    processAmount(Number(amount));
    return true;
}

/**
 * Load application config from the API.
 * Awaits response.json() correctly and handles HTTP errors.
 */
async function loadConfig() {
    const response = await fetch("/api/config");

    if (!response.ok) {
        throw new Error(`Failed to load config: ${response.status} ${response.statusText}`);
    }

    // response.json() returns a Promise and must be awaited
    const data = await response.json();
    return data;
}

/**
 * Calculate the discounted price.
 * @param {number} price
 * @param {number} discount - Percentage discount (0-100)
 */
function calculateDiscount(price, discount) {
    if (typeof price !== "number" || typeof discount !== "number") {
        throw new Error("price and discount must be numbers");
    }
    if (discount < 0 || discount > 100) {
        throw new Error("discount must be between 0 and 100");
    }
    return price - (price * discount) / 100;
}

module.exports = { fetchUserData, processPayment, loadConfig, calculateDiscount };
