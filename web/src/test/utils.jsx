import { render } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ToastProvider } from '../components/ToastContainer';
import { AuthProvider } from '../contexts/AuthContext';

// Custom render function that includes Router, AuthProvider, and ToastProvider
export const renderWithRouter = (ui, { route = '/', withAuth = true, withToast = true } = {}) => {
  window.history.pushState({}, 'Test page', route);
  let content = ui;
  if (withAuth) {
    content = <AuthProvider>{content}</AuthProvider>;
  }
  if (withToast) {
    content = <ToastProvider>{content}</ToastProvider>;
  }
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
