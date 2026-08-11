const baseUrl = 'http://localhost:8000/api/v1';

async function test() {
  const email = "test_frontend@example.com";
  const password = "password123";

  // Register
  await fetch(`${baseUrl}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, name: 'Test User' })
  });

  // Login
  const loginRes = await fetch(`${baseUrl}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });

  const data = await loginRes.json();
  const token = data.access_token;
  console.log("Token:", token);

  // authenticatedFetch logic
  const headers = new Headers();
  headers.set('Authorization', `Bearer ${token}`);

  const wfRes = await fetch(`${baseUrl}/workflows/`, {
    headers
  });

  console.log("Status:", wfRes.status);
  const wfBody = await wfRes.text();
  console.log("Body:", wfBody);
}

test().catch(console.error);
