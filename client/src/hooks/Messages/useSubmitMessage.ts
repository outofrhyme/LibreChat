import { useCallback } from 'react';
import { useRecoilValue, useSetRecoilState } from 'recoil';
import type { TMessage } from 'librechat-data-provider';
import { buildTree, replaceSpecialVars } from 'librechat-data-provider';
import { useChatContext, useChatFormContext, useAddedChatContext } from '~/Providers';
import useBuildMessageTree from './useBuildMessageTree';
import { useAuthContext } from '~/hooks/AuthContext';
import store from '~/store';

export default function useSubmitMessage() {
  const { user } = useAuthContext();
  const methods = useChatFormContext();
  const { conversation: addedConvo } = useAddedChatContext();
  const { ask, index, getMessages, conversation } = useChatContext();
  const buildMessageTree = useBuildMessageTree();
  const latestMessage = useRecoilValue(store.latestMessageFamily(index));
  const setLatestMessage = useSetRecoilState(store.latestMessageFamily(index));

  const autoSendPrompts = useRecoilValue(store.autoSendPrompts);
  const setActivePrompt = useSetRecoilState(store.activePromptByIndex(index));

  const submitMessage = useCallback(
    async (data?: { text: string }) => {
      if (!data) {
        return console.warn('No data provided to submitMessage');
      }
      const rootMessages = getMessages() ?? [];
      const dataTree = buildTree({ messages: rootMessages });
      const isLatestInRootMessages = rootMessages?.some(
        (message) => message.messageId === latestMessage?.messageId,
      );
      let resolvedLatestMessage: TMessage | null = isLatestInRootMessages ? latestMessage : null;
      if (dataTree?.length) {
        const activeBranch = await buildMessageTree({
          messageId: conversation?.conversationId,
          message: null,
          messages: dataTree,
          branches: false,
          recursive: false,
        });
        if (Array.isArray(activeBranch) && activeBranch.length > 0) {
          resolvedLatestMessage = activeBranch[activeBranch.length - 1] as TMessage;
        }
      }
      if (!resolvedLatestMessage) {
        resolvedLatestMessage = rootMessages[rootMessages.length - 1] ?? null;
      }
      if (!isLatestInRootMessages) {
        setLatestMessage(resolvedLatestMessage);
      }

      ask(
        {
          text: data.text,
          parentMessageId: resolvedLatestMessage?.messageId ?? null,
        },
        {
          addedConvo: addedConvo ?? undefined,
        },
      );
      methods.reset();
    },
    [
      ask,
      methods,
      addedConvo,
      getMessages,
      latestMessage,
      setLatestMessage,
      conversation?.conversationId,
      buildMessageTree,
    ],
  );

  const submitPrompt = useCallback(
    (text: string) => {
      const parsedText = replaceSpecialVars({ text, user });
      if (autoSendPrompts) {
        submitMessage({ text: parsedText });
        return;
      }

      const currentText = methods.getValues('text');
      const newText = currentText.trim().length > 1 ? `\n${parsedText}` : parsedText;
      setActivePrompt(newText);
    },
    [autoSendPrompts, submitMessage, setActivePrompt, methods, user],
  );

  return { submitMessage, submitPrompt };
}
