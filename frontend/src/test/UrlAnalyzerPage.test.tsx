import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { vi } from 'vitest';

import UrlAnalyzerPage from '../pages/UrlAnalyzerPage';
import { ApiError, api } from '../services/api';
import { highRiskScan } from './fixtures';

function renderPage() {
  return render(
    <MemoryRouter>
      <UrlAnalyzerPage />
    </MemoryRouter>,
  );
}

afterEach(() => vi.restoreAllMocks());

describe('UrlAnalyzerPage', () => {
  it('asks for a URL instead of calling the API when the box is empty', async () => {
    const spy = vi.spyOn(api, 'analyzeUrl');
    renderPage();
    await userEvent.click(screen.getByRole('button', { name: /analyze url/i }));
    expect(screen.getByRole('alert')).toHaveTextContent(/enter a url/i);
    expect(spy).not.toHaveBeenCalled();
  });

  it('shows the result returned by the backend', async () => {
    vi.spyOn(api, 'analyzeUrl').mockResolvedValue(highRiskScan);
    renderPage();
    await userEvent.type(screen.getByLabelText(/url to analyze/i), 'http://192.168.0.1/login');
    await userEvent.click(screen.getByRole('button', { name: /analyze url/i }));
    expect(await screen.findByText('Host is an IP address')).toBeInTheDocument();
  });

  it('shows the backend error message when validation fails', async () => {
    vi.spyOn(api, 'analyzeUrl').mockRejectedValue(new ApiError('Only http and https URLs are supported.', 422, 'invalid_url'));
    renderPage();
    await userEvent.type(screen.getByLabelText(/url to analyze/i), 'ftp://example.com');
    await userEvent.click(screen.getByRole('button', { name: /analyze url/i }));
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent(/only http and https/i));
  });
});
