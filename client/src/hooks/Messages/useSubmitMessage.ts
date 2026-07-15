import { useCallback } from 'react';
import { useRecoilValue, useSetRecoilState } from 'recoil';
import type { TMessage } from 'librechat-data-provider';
import { buildTree, replaceSpecialVars } from 'librechat-data-provider';
import { useChatContext, useChatFormContext, useAddedChatContext } from '~/Providers';
import useBuildMessageTree from './useBuildMessageTree';
import { useLatestMessage } from '~/hooks/Messages/useLatestMessage';
import { useAuthContext } from '~/hooks/AuthContext';
import { mainTextareaId } from '~/common';
import store from '~/store';

export default function useSubmitMessage() {
  const { user } = useAuthContext();
  const methods = useChatFormContext();
  const { conversation: addedConvo } = useAddedChatContext();
  const { ask, index, getMessages, conversation } = useChatContext();
  const buildMessageTree = useBuildMessageTree();
  const latestMessage = useLatestMessage(index);
  const rootSiblingKey = conversation?.conversationId;

  const autoSendPrompts = useRecoilValue(store.autoSendPrompts);
  const setActivePrompt = useSetRecoilState(store.activePromptByIndex(index));
  const setLatestMessage = useSetRecoilState(store.latestMessageFamily(index));

  const submitMessage = useCallback(
    async (data?: { text: string }) => {
      if (!data) {
        return console.warn('No data provided to submitMessage');
      }

      const rootMessages = getMessages() ?? [];
      const dataTree = buildTree({ messages: rootMessages });
      const isLatestInRootMessages = rootMessages.some(
        (message) => message.messageId === latestMessage?.messageId,
      );
      let resolvedLatestMessage: TMessage | null = isLatestInRootMessages ? latestMessage : null;

      if (dataTree?.length) {
        const activeBranch = await buildMessageTree({
          messageId: rootSiblingKey,
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

      const submitted = ask(
        {
          text: data.text,
          parentMessageId: resolvedLatestMessage?.messageId ?? null,
        },
        {
          addedConvo: addedConvo ?? undefined,
        },
      );
      if (submitted === false) {
        return false;
      }
      methods.reset();
    },
    [
      ask,
      methods,
      addedConvo,
      getMessages,
      latestMessage,
      rootSiblingKey,
      buildMessageTree,
      setLatestMessage,
    ],
  );

  const submitPrompt = useCallback(
    (text: string) => {
      const parsedText = replaceSpecialVars({ text, user });
      if (autoSendPrompts) {
        submitMessage({ text: parsedText });
        return;
      }

      const textarea = document.getElementById(mainTextareaId) as HTMLTextAreaElement | null;
      const currentText = textarea?.value ?? methods.getValues('text');
      const newText = currentText.trim().length > 1 ? `\n${parsedText}` : parsedText;
      setActivePrompt(newText);
    },
    [autoSendPrompts, submitMessage, setActivePrompt, methods, user],
  );

  return { submitMessage, submitPrompt };
}
