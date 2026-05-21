import { renderWithPlugins } from '@/vitest.setup';
import { screen } from '@testing-library/vue';
import userEvent from '@testing-library/user-event';
import CustomReportModal from './CustomReportModal.vue';

vi.mock('vue-final-modal', () => ({
  useVfm: () => ({ close: vi.fn() }),
  VueFinalModal: { template: '<div><slot /></div>' },
}));

vi.mock('@/components/core/BaseModal.vue', () => ({
  default: {
    template: '<div><slot /><slot name="footer" /></div>',
    props: ['modalId', 'title', 'size', 'noActions', 'disableCloseOnOutsideClick'],
  },
}));

function renderModal(props: Record<string, unknown> = {}) {
  return renderWithPlugins(CustomReportModal as any, {
    props: {
      initialPrompt: '',
      onGenerate: vi.fn(),
      onUpdatePrompt: vi.fn(),
      ...props,
    } as any,
  });
}

describe('CustomReportModal', () => {
  it('disables generate button when prompt is empty', () => {
    renderModal();
    const generateBtn = screen.getByRole('button', { name: /générer/i });
    expect(generateBtn).toBeDisabled();
  });

  it('enables generate button when prompt is non-empty', async () => {
    renderModal();
    const textarea = screen.getByPlaceholderText(/génère un compte-rendu/i);
    await userEvent.type(textarea, 'Mon prompt');
    const generateBtn = screen.getByRole('button', { name: /générer/i });
    expect(generateBtn).not.toBeDisabled();
  });

  it('fills textarea when clicking a suggestion', async () => {
    renderModal();
    await userEvent.click(screen.getByText("Plan d'actions"));
    const textarea = screen.getByPlaceholderText(/génère un compte-rendu/i) as HTMLTextAreaElement;
    expect(textarea.value).not.toBe('');
  });

  it('calls onGenerate with prompt value when generate is clicked', async () => {
    const onGenerate = vi.fn();
    renderModal({ onGenerate });
    const textarea = screen.getByPlaceholderText(/génère un compte-rendu/i);
    await userEvent.type(textarea, 'Analyse les risques');
    const generateBtn = screen.getByRole('button', { name: /générer/i });
    await userEvent.click(generateBtn);
    expect(onGenerate).toHaveBeenCalledWith('Analyse les risques');
  });

  it('calls onUpdatePrompt with current value when cancel is clicked', async () => {
    const onUpdatePrompt = vi.fn();
    const { unmount } = renderModal({ onUpdatePrompt });
    const textarea = screen.getByPlaceholderText(/génère un compte-rendu/i);
    await userEvent.type(textarea, 'brouillon');
    const cancelBtn = screen.getByRole('button', { name: /annuler/i });
    await userEvent.click(cancelBtn);
    unmount();
    expect(onUpdatePrompt).toHaveBeenCalledWith('brouillon');
  });

  it('pre-fills textarea with initialPrompt', () => {
    renderModal({ initialPrompt: 'Mon brouillon' });
    const textarea = screen.getByPlaceholderText(/génère un compte-rendu/i) as HTMLTextAreaElement;
    expect(textarea.value).toBe('Mon brouillon');
  });
});
