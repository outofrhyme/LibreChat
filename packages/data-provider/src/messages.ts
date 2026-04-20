import type { TFile } from './types/files';
import type { TMessage } from './types';

export type ParentMessage = TMessage & { children: TMessage[]; depth: number };
export function buildTree({
  messages,
  fileMap,
}: {
  messages: (TMessage | undefined)[] | null;
  fileMap?: Record<string, TFile>;
}) {
  if (messages === null) {
    return null;
  }

  const messageMap: Record<string, ParentMessage> = {};
  const rootMessages: TMessage[] = [];
  const childrenCount: Record<string, number> = {};
  const malformedMessages: Array<{ index: number; reason: string }> = [];
  const orphanedParentIds = new Set<string>();
  const isPerfDebug =
    typeof globalThis === 'object' &&
    globalThis != null &&
    '__LIBRECHAT_PERF_DEBUG' in globalThis &&
    Boolean((globalThis as { __LIBRECHAT_PERF_DEBUG?: unknown }).__LIBRECHAT_PERF_DEBUG);

  messages.forEach((message, index) => {
    if (!message) {
      malformedMessages.push({ index, reason: 'empty_message' });
      return;
    }
    if (!message.messageId) {
      malformedMessages.push({ index, reason: 'missing_message_id' });
    }
    const parentId = message.parentMessageId ?? '';
    childrenCount[parentId] = (childrenCount[parentId] || 0) + 1;

    const extendedMessage: ParentMessage = {
      ...message,
      children: [],
      depth: 0,
      siblingIndex: childrenCount[parentId] - 1,
    };

    if (message.files && fileMap) {
      extendedMessage.files = message.files.map((file) => fileMap[file.file_id ?? ''] ?? file);
    }

    messageMap[message.messageId] = extendedMessage;

    const parentMessage = messageMap[parentId];
    if (parentMessage) {
      parentMessage.children.push(extendedMessage);
      extendedMessage.depth = parentMessage.depth + 1;
    } else {
      if (parentId) {
        orphanedParentIds.add(parentId);
      }
      rootMessages.push(extendedMessage);
    }
  });

  if (isPerfDebug) {
    console.debug('[perf] tree.build', {
      inputCount: messages.length,
      rootCount: rootMessages.length,
      malformedCount: malformedMessages.length,
      orphanedParentCount: orphanedParentIds.size,
      malformedMessages: malformedMessages.slice(0, 10),
    });
  }

  return rootMessages;
}
