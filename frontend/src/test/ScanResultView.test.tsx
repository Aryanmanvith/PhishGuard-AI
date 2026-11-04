import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import ScanResultView from '../components/ScanResultView';
import { highRiskScan } from './fixtures';

describe('ScanResultView', () => {
  it('shows score, indicator evidence, limitations and the not-a-probability notice', () => {
    render(
      <MemoryRouter>
        <ScanResultView scan={highRiskScan} />
      </MemoryRouter>,
    );
    expect(screen.getByText('Host is an IP address')).toBeInTheDocument();
    expect(screen.getByText('192.168.0.1')).toBeInTheDocument();
    expect(screen.getByText(/not a probability/i)).toBeInTheDocument();
    expect(screen.getByText(/cannot see page content/i)).toBeInTheDocument();
    expect(screen.getByText('No trained model found.')).toBeInTheDocument();
  });

  it('marks demo scans clearly', () => {
    render(
      <MemoryRouter>
        <ScanResultView scan={{ ...highRiskScan, is_demo: true }} />
      </MemoryRouter>,
    );
    expect(screen.getByText('Demo')).toBeInTheDocument();
  });
});
