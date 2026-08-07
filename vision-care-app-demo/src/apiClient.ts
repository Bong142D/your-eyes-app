import { router } from 'expo-router';
import { Alert } from 'react-native';

import { API_BASE_URL } from './apiConfig';
import { getToken, deleteToken } from './auth';

interface AuthedFetchOptions extends RequestInit {
  headers?: HeadersInit & {
    Authorization?: string;
  };
}

export async function authedFetch(endpoint: string, options: AuthedFetchOptions = {}): Promise<Response> {
  const token = await getToken();

  if (!token) {
    // This should not happen in flows that require authentication.
    // Redirect to login screen.
    Alert.alert('Phiên đăng nhập hết hạn', 'Vui lòng đăng nhập lại.');
    router.replace('/auth');
    // Return a mock response to prevent further processing
    return new Response(JSON.stringify({ error: 'Not authenticated' }), { status: 401 });
  }

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
    Authorization: `Bearer ${token}`,
  };

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    // Unauthorized, token might be expired or invalid.
    // Clear the token and redirect to login.
    await deleteToken();
    Alert.alert('Phiên đăng nhập hết hạn', 'Vui lòng đăng nhập lại.');
    router.replace('/auth');
  }

  return response;
}
