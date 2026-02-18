import axios from 'axios';
import { API_BASE_URL } from '@/constants/api';
import { REQUEST_TIMEOUT_MS } from '@/constants/config';
import { setupInterceptors } from './interceptors';

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: REQUEST_TIMEOUT_MS,
  headers: {
    'Content-Type': 'application/json',
  },
});

setupInterceptors(client);

export default client;
