import { describe, it, expect, beforeEach } from 'vitest';
import useToaster from './use-toaster';

describe('use-toaster', () => {
  const { messages, addInfoMessage, addWarningMessage } = useToaster();

  beforeEach(() => {
    messages.splice(0, messages.length);
  });

  it('publishes an informative message as an information', () => {
    addInfoMessage('Nouveau microphone détecté');

    expect(messages[0]).toMatchObject({
      description: 'Nouveau microphone détecté',
      type: 'info',
    });
  });

  it('publishes a warning message as a warning', () => {
    addWarningMessage('Le microphone utilisé a été déconnecté');

    expect(messages[0]).toMatchObject({
      description: 'Le microphone utilisé a été déconnecté',
      type: 'warning',
    });
  });
});
