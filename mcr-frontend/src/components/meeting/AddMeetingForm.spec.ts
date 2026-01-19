import { screen } from '@testing-library/vue';
import userEvent from '@testing-library/user-event';
import AddMeetingForm from '@/components/meeting/AddMeetingForm.vue';

import { renderWithPlugins } from '@/vitest.setup';

describe('AddMeetingForm', () => {
  it('url selector is shown by default', () => {
    // Arrange
    renderWithPlugins(AddMeetingForm);

    // Act
    // (No user actions needed for this test)

    // Assert
    const urlInput = screen.getByRole('textbox', { name: /url/i });
    expect(urlInput).toBeInTheDocument();

    const toggle = screen.getByRole('checkbox', { name: /Ajouter avec l'url/i });
    expect(toggle).toBeChecked();
  });

  it('password selector is shown on toggle click', async () => {
    // Arrange
    renderWithPlugins(AddMeetingForm);

    // Act
    const toggle = screen.getByRole('checkbox', { name: /Ajouter avec l'url/i });
    await userEvent.click(toggle);

    // Assert
    // the interactions with the DOM (click) introduces asynchrony so we must use findBy selector and not getBy
    const idInput = await screen.findByRole('textbox', { name: /ID/i });
    expect(idInput).toBeInTheDocument();
    expect(toggle).not.toBeChecked();
  });

  it('password selector to be shown if editing a meeting', async () => {
    // Arrange
    renderWithPlugins(AddMeetingForm, {
      props: {
        initialValues: {
          meeting_platform_id: '12345',
          meeting_password: 'password',
        },
      },
    });

    // Act
    // (No user actions needed for this test)

    // Assert
    const idInput = await screen.findByRole('textbox', { name: /ID/i });
    expect(idInput).toBeInTheDocument();

    const toggle = screen.getByRole('checkbox', { name: /Ajouter avec l'url/i });
    expect(toggle).not.toBeChecked();
  });
});
