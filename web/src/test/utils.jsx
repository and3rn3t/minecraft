import { render } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '../contexts/AuthContext';

// Custom render function that includes Router and optionally AuthProvider
export const renderWithRouter = (ui, { route = '/', withAuth = true } = {}) => {
  window.history.pushState({}, 'Test page', route);
  const content = withAuth ? <AuthProvider>{ui}</AuthProvider> : ui;
  return render(<BrowserRouter>{content}</BrowserRouter>);
};

// Mock API responses
export const mockApiResponse = (data, status = 200) => ({
  data,
  status,
  statusText: 'OK',
  headers: {},
  config: {},
});
