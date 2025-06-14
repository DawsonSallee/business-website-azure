/*
    Order Status Feature for Dimension Template
*/

// Wait for the entire page to load before running the script
document.addEventListener('DOMContentLoaded', function() {

    // Get references to our HTML elements
    const statusForm = document.getElementById('order-status-form');
    const nameInput = document.getElementById('customer-name');
    const resultsContainer = document.getElementById('results-container');
    
    // Make sure all elements were found before adding the event listener
    if (statusForm && nameInput && resultsContainer) {
        
        statusForm.addEventListener('submit', async (event) => {
            event.preventDefault(); // Prevent form from reloading the page

            const customerName = nameInput.value.trim();
            if (!customerName) {
                return;
            }

            // --- MAKE SURE THIS URL IS CORRECT ---
            const API_BASE_URL = 'https://my-unique-business-api.azurewebsites.net/api/order-status/';
            const encodedCustomerName = encodeURIComponent(customerName);
            const fullApiUrl = `${API_BASE_URL}${encodedCustomerName}`;
            
            // Show loading state
            resultsContainer.style.display = 'block';
            resultsContainer.innerHTML = '<p>Searching...</p>';

            try {
                const response = await fetch(fullApiUrl);
                const data = await response.json();
                
                console.log('API Response Data:', data); 


                if (!response.ok) {
                    // Handle errors from the API, like 404 Not Found
                    resultsContainer.innerHTML = `<p style="color: red;">${data.detail}</p>`;
                } else {
                    // Helper function to format dates and times nicely for the user
                    const formatDateTime = (dateTimeString) => {
                        if (!dateTimeString) return 'N/A';
                        // Use toLocaleString to get a user-friendly date and time
                        return new Date(dateTimeString).toLocaleString();
                    };

                    const formatDate = (dateString) => {
                        if (!dateString) return 'Pending';
                        // The 'T' separates date from time, we only want the date part.
                        return new Date(dateString.split('T')[0]).toLocaleDateString();
                    };

                    // Pre-calculate totals safely, handling potential nulls
                    const totalCost = (data.mountPrice || 0) + (data.boardPrice || 0);
                    const totalDeposit = (data.depositCash || 0) + (data.depositCheck || 0);
                    const subsequentPayments = (data.paymentCash || 0) + (data.paymentCheck || 0);

                    resultsContainer.innerHTML = `
                        <div class="status-receipt">
                            <div class="receipt-header">
                                <h3>Order Status for ${data.customerName}</h3>                                
                                <div class="receipt-line"><span><strong>Order Date: </strong></span><span>${formatDate(data.orderDate)}</span></div>
                                <div class="receipt-line"><span><strong>Ready for Pickup: </strong></span><span>${formatDate(data.readyDate)}</span></div>
                                <div class="receipt-line"><span><strong>Customer Called: </strong></span><span>${formatDate(data.calledDate)}</span></div>
                                <div class="receipt-line"><span><strong>Final Pickup: </strong></span><span>${formatDate(data.pickupDate)}</span></div>
                            </div>


                            <div class="receipt-section">
                                <h4> </h4>
                                <h4>---------Financial Summary---------</h4>
                                <div class="receipt-line"><span>Mount Price:</span><span> $${(data.mountPrice || 0).toFixed(2)}</span></div>
                                <div class="receipt-line"><span>Board Price:</span><span> $${(data.boardPrice || 0).toFixed(2)}</span></div>
                                <div class="receipt-total"><strong>Total Cost:</strong><strong> $${totalCost.toFixed(2)}</strong></div>
                                <br>
                                <div class="receipt-line"><span>Initial Deposit:</span><span> - $${totalDeposit.toFixed(2)}</span></div>
                                <div class="receipt-line"><span>Additional Payments:</span><span> - $${subsequentPayments.toFixed(2)}</span></div>
                            </div>
                            
                            <div class="receipt-balance">
                                <h4> </h4>
                                <strong>Balance Due:</strong>
                                <strong>$${data.balance.toFixed(2)}</strong>
                            </div>

                            <div class="receipt-footer">
                                <h4>-----------------------------------------</h4>
                                <h4>Thank you for your business!</h4>
                                <h4>-----------------------------------------</h4>
                                <p>Last Updated: ${formatDateTime(data.lastUpdatedAt)}</p>
                            </div>
                        </div>
                    `;
                }
            } catch (error) {
                console.error('Error fetching order status:', error);
                resultsContainer.innerHTML = '<p style="color: red;">Could not connect to the server. Please try again later.</p>';
            }
        });
    } else {
        console.error('Could not find one or more required elements for the order status form.');
    }
});