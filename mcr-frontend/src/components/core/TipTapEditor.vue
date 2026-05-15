<template>
  <div class="tiptap-editor border border-grey-900 rounded">
    <div
      v-if="editor"
      class="flex gap-1 p-1 border-b border-grey-900"
    >
      <button
        v-for="action in toolbarActions"
        :key="action.name"
        type="button"
        class="fr-btn fr-btn--tertiary-no-outline fr-btn--sm"
        :aria-label="t(action.labelKey)"
        :aria-pressed="action.isActive()"
        @click="action.command()"
      >
        <span
          :class="action.icon"
          aria-hidden="true"
        />
      </button>
    </div>
    <EditorContent
      class="p-3"
      :editor="editor"
    />
  </div>
</template>

<script setup lang="ts">
import { useEditor, EditorContent } from '@tiptap/vue-3';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import { Markdown } from 'tiptap-markdown';
import { t } from '@/plugins/i18n';

const props = defineProps<{
  modelValue: string;
  placeholder?: string;
}>();
const emit = defineEmits<{
  'update:modelValue': [value: string];
}>();

const editor = useEditor({
  content: props.modelValue,
  extensions: [
    StarterKit,
    Placeholder.configure({ placeholder: props.placeholder ?? '' }),
    Markdown.configure({ transformPastedText: true }),
  ],
  onUpdate: ({ editor }) => {
    emit('update:modelValue', editor.storage.markdown.getMarkdown());
  },
});

const toolbarActions = [
  {
    name: 'bold',
    labelKey: 'common.editor.bold',
    icon: 'fr-icon-bold',
    command: () => editor.value?.chain().focus().toggleBold().run(),
    isActive: () => editor.value?.isActive('bold') ?? false,
  },
  {
    name: 'italic',
    labelKey: 'common.editor.italic',
    icon: 'fr-icon-italic',
    command: () => editor.value?.chain().focus().toggleItalic().run(),
    isActive: () => editor.value?.isActive('italic') ?? false,
  },
  {
    name: 'bulletList',
    labelKey: 'common.editor.bullet-list',
    icon: 'fr-icon-list-unordered',
    command: () => editor.value?.chain().focus().toggleBulletList().run(),
    isActive: () => editor.value?.isActive('bulletList') ?? false,
  },
  {
    name: 'orderedList',
    labelKey: 'common.editor.ordered-list',
    icon: 'fr-icon-list-ordered',
    command: () => editor.value?.chain().focus().toggleOrderedList().run(),
    isActive: () => editor.value?.isActive('orderedList') ?? false,
  },
];

onBeforeUnmount(() => {
  editor.value?.destroy();
});
</script>

<style>
.tiptap-editor .ProseMirror {
  min-height: 120px;
  max-height: 400px;
  overflow-y: auto;
  outline: none;
}
.tiptap-editor .ProseMirror p.is-editor-empty:first-child::before {
  content: attr(data-placeholder);
  color: var(--grey-625-425);
  pointer-events: none;
  float: left;
  height: 0;
}
/* Active state for toolbar toggle buttons */
.tiptap-editor button[aria-pressed='true'] {
  background-color: var(--background-action-low-blue-france);
  color: var(--text-action-high-blue-france);
}
/* Restore list styles reset by Tailwind preflight */
.tiptap-editor .ProseMirror ul {
  list-style-type: disc;
  padding-left: 1.5rem;
  margin: 0.5rem 0;
}
.tiptap-editor .ProseMirror ol {
  list-style-type: decimal;
  padding-left: 1.5rem;
  margin: 0.5rem 0;
}
</style>
