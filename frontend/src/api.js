/**
 * Fetch wrapper that adds JWT authentication header if token is available
 * @param {string} url - The request URL
 * @param {Object} [options] - Fetch options (method, headers, body, etc.)
 * @returns {Promise<Response>} - Fetch promise
 */
export function fetchWithAuth(url, options = {}) {
  const token = localStorage.getItem('access_token');

  // If token exists, prepare Authorization header
  if (token) {
    // Ensure options.headers exists
    const headers = new Headers(options.headers);
    headers.set('Authorization', `Bearer ${token}`);

    // Return fetch with updated headers
    return fetch(url, { ...options, headers });
  }

  // No token, proceed with original options
  return fetch(url, options);
}