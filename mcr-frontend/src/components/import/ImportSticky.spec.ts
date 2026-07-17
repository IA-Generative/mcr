import ImportSticky from '@/components/import/ImportSticky.vue';
import { useUploadBatchWriter, type UploadDraft } from '@/composables/use-upload-batch';
import { renderWithPlugins } from '@/vitest.setup';
import { screen, within } from '@testing-library/vue';
import { beforeEach, describe, expect, it } from 'vitest';
import { createMemoryHistory, createRouter } from 'vue-router';

function draft(overrides: Partial<UploadDraft> = {}): UploadDraft {
  return {
    title: 'enregistrement',
    kind: 'audio',
    durationSeconds: 60,
    totalBytes: 1_000,
    ...overrides,
  };
}

const writer = useUploadBatchWriter();

function enqueueWithMeetings(drafts: UploadDraft[]): number[] {
  const itemIds = writer.enqueue(drafts);
  itemIds.forEach((id) => writer.attachMeeting(id, 100 + id));
  return itemIds;
}

async function findRowByTitle(title: string): Promise<HTMLElement> {
  const rows = await screen.findAllByRole('listitem');
  const row = rows.find((candidate) => candidate.textContent?.includes(title));
  if (!row) {
    throw new Error(`no sticky row titled "${title}"`);
  }
  return row;
}

describe('ImportSticky', () => {
  beforeEach(() => {
    writer.clearAll();
  });

  it('stays hidden while no import has been started', () => {
    renderWithPlugins(ImportSticky);

    expect(screen.queryByRole('region', { name: 'Suivi des importations' })).toBeNull();
  });

  it('appears with one line per selected file, identified by its title', async () => {
    renderWithPlugins(ImportSticky);
    enqueueWithMeetings([draft({ title: 'Réunion COMU 12-03' }), draft({ title: 'Daily équipe' })]);

    expect(
      await screen.findByRole('region', { name: 'Suivi des importations' }),
    ).toBeInTheDocument();
    expect(await screen.findAllByRole('listitem')).toHaveLength(2);
    expect(await findRowByTitle('Réunion COMU 12-03')).toBeTruthy();
    expect(await findRowByTitle('Daily équipe')).toBeTruthy();
  });

  it('shows a paused status for a file waiting its turn', async () => {
    renderWithPlugins(ImportSticky);
    enqueueWithMeetings([draft({ title: 'premier' }), draft({ title: 'en attente' })]);

    expect(
      within(await findRowByTitle('en attente')).getByRole('img', { name: 'En attente' }),
    ).toBeInTheDocument();
  });

  it('shows an in-progress status while a file uploads', async () => {
    renderWithPlugins(ImportSticky);
    enqueueWithMeetings([draft({ title: 'en cours' })]);

    expect(
      within(await findRowByTitle('en cours')).getByRole('img', { name: 'Importation en cours' }),
    ).toBeInTheDocument();
  });

  it('shows an in-progress status while a video transcodes', async () => {
    renderWithPlugins(ImportSticky);
    writer.enqueue([draft({ title: 'vidéo', kind: 'video' })]);

    expect(
      within(await findRowByTitle('vidéo')).getByRole('img', { name: 'Importation en cours' }),
    ).toBeInTheDocument();
  });

  it('shows a success status once a file is imported', async () => {
    renderWithPlugins(ImportSticky);
    const [id] = enqueueWithMeetings([draft({ title: 'fini' })]);
    writer.complete(id);

    expect(
      within(await findRowByTitle('fini')).getByRole('img', { name: 'Importation terminée' }),
    ).toBeInTheDocument();
  });

  it('shows an error status when a file fails', async () => {
    renderWithPlugins(ImportSticky);
    const [id] = enqueueWithMeetings([draft({ title: 'raté' })]);
    writer.fail(id, 'timeout');

    expect(
      within(await findRowByTitle('raté')).getByRole('img', { name: 'Importation échouée' }),
    ).toBeInTheDocument();
  });

  it('keeps every line visible once the batch is settled', async () => {
    renderWithPlugins(ImportSticky);
    const [first, second] = enqueueWithMeetings([
      draft({ title: 'réussi' }),
      draft({ title: 'échoué' }),
    ]);
    writer.complete(first);
    writer.fail(second, 'http-server');

    expect(await screen.findAllByRole('listitem')).toHaveLength(2);
  });

  it('displays the most recent batch on top, shortest duration first within a batch', async () => {
    renderWithPlugins(ImportSticky);
    enqueueWithMeetings([
      draft({ title: 'lot1-long', durationSeconds: 3_600 }),
      draft({ title: 'lot1-court', durationSeconds: 60 }),
    ]);
    enqueueWithMeetings([
      draft({ title: 'lot2-moyen', durationSeconds: 600 }),
      draft({ title: 'lot2-mini', durationSeconds: 10 }),
    ]);

    const rows = await screen.findAllByRole('listitem');
    const titles = rows.map((row) => row.textContent);
    expect(titles[0]).toContain('lot2-mini');
    expect(titles[1]).toContain('lot2-moyen');
    expect(titles[2]).toContain('lot1-court');
    expect(titles[3]).toContain('lot1-long');
  });

  it('titles the sticky with the number of items while work is in progress', async () => {
    renderWithPlugins(ImportSticky);
    enqueueWithMeetings([draft(), draft(), draft()]);

    expect(await screen.findByText('Importation de 3 élément(s)')).toBeInTheDocument();
  });

  it('titles the sticky with the success count once every file is imported', async () => {
    renderWithPlugins(ImportSticky);
    const itemIds = enqueueWithMeetings([draft(), draft()]);
    itemIds.forEach((id) => writer.complete(id));

    expect(await screen.findByText('2 importation(s) réussie(s)')).toBeInTheDocument();
  });

  it('titles the sticky with the failure count when the settled batch has errors', async () => {
    renderWithPlugins(ImportSticky);
    const [first, second, third] = enqueueWithMeetings([draft(), draft(), draft()]);
    writer.complete(first);
    writer.complete(second);
    writer.fail(third, 'offline');

    expect(await screen.findByText('2 importation(s) réussie(s), 1 en erreur')).toBeInTheDocument();
  });

  it('survives an internal navigation without losing its lines', async () => {
    const pageStub = { template: '<div />' };
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', component: pageStub },
        { path: '/ailleurs', component: pageStub },
      ],
    });
    const appShell = {
      components: { ImportSticky },
      template: '<div><router-view /><ImportSticky /></div>',
    };
    renderWithPlugins(appShell, { global: { plugins: [router] } });
    enqueueWithMeetings([draft({ title: 'persistant' })]);
    expect(await screen.findByText('persistant')).toBeInTheDocument();

    await router.push('/ailleurs');

    expect(screen.getByText('persistant')).toBeInTheDocument();
  });
});
