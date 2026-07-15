import { useCallback, useMemo } from 'react';
import { useRecoilValue, useSetRecoilState } from 'recoil';
import throttle from 'lodash/throttle';
import { isAssistantsEndpoint, isAgentsEndpoint } from 'librechat-data-provider';
import type { TMessageProps } from '~/common';
import { useMessagesViewContext, useAssistantsMapContext, useAgentsMapContext } from '~/Providers';
import { useDeleteMessageMutation } from '~/data-provider';
import useCopyToClipboard from './useCopyToClipboard';
import { useGetAddedConvo } from '~/hooks/Chat';
import { logger } from '~/utils';
import store from '~/store';

export default function useMessageHelpers(props: TMessageProps) {
  const { message, currentEditId, setCurrentEditId } = props;

  const {
    ask,
    index,
    regenerate,
    isSubmitting,
    conversation,
    setAbortScroll,
    handleContinue,
    latestMessageId,
  } = useMessagesViewContext();
  const agentsMap = useAgentsMapContext();
  const assistantMap = useAssistantsMapContext();

  const getAddedConvo = useGetAddedConvo();

  const { text, content, children, messageId = null, isCreatedByUser } = message ?? {};
  const edit = messageId === currentEditId;
  const isLast = children?.length === 0 || children?.length === undefined;

  const enterEdit = useCallback(
    (cancel?: boolean) => setCurrentEditId && setCurrentEditId(cancel === true ? -1 : messageId),
    [messageId, setCurrentEditId],
  );

  const handleScroll = useCallback(
    (event: unknown) => {
      throttle(() => {
        logger.log(
          'message_scrolling',
          `useMessageHelpers: setting abort scroll to ${isSubmitting}, handleScroll event`,
          event,
        );
        if (isSubmitting) {
          setAbortScroll(true);
        } else {
          setAbortScroll(false);
        }
      }, 500)();
    },
    [isSubmitting, setAbortScroll],
  );

  const assistant = useMemo(() => {
    if (!isAssistantsEndpoint(conversation?.endpoint)) {
      return undefined;
    }

    const endpointKey = conversation?.endpoint ?? '';
    const modelKey = message?.model ?? '';

    return assistantMap?.[endpointKey] ? assistantMap[endpointKey][modelKey] : undefined;
  }, [conversation?.endpoint, message?.model, assistantMap]);

  const agent = useMemo(() => {
    if (!isAgentsEndpoint(conversation?.endpoint)) {
      return undefined;
    }

    const modelKey = message?.model ?? '';

    return agentsMap ? agentsMap[modelKey] : undefined;
  }, [agentsMap, conversation?.endpoint, message?.model]);

  const regenerateMessage = () => {
    if ((isSubmitting && isCreatedByUser === true) || !message) {
      return;
    }

    regenerate(message, { addedConvo: getAddedConvo() });
  };

  const copyToClipboard = useCopyToClipboard({ text, content });
  const latestMessage = useRecoilValue(store.latestMessageFamily(index));
  const setLatestMessage = useSetRecoilState(store.latestMessageFamily(index));
  const deleteMessageMutation = useDeleteMessageMutation({
    onMutate: () => ({ previousLatestMessage: latestMessage }),
    onSuccess: (_data, vars, context) => {
      if (!context || latestMessageId !== vars.messageId) {
        return;
      }
      setLatestMessage(context.fallbackMessage);
    },
    onError: (_error, _vars, context) => {
      if (context?.previousLatestMessage === undefined) {
        return;
      }
      setLatestMessage(context.previousLatestMessage);
    },
  });

  const deleteMessage = useCallback(() => {
    if (!conversation?.conversationId || !messageId) {
      return;
    }

    deleteMessageMutation.mutate({
      conversationId: conversation.conversationId,
      messageId,
    });
  }, [conversation?.conversationId, deleteMessageMutation, messageId]);

  return {
    ask,
    edit,
    agent,
    index,
    isLast,
    assistant,
    enterEdit,
    conversation,
    isSubmitting,
    handleScroll,
    handleContinue,
    latestMessageId,
    deleteMessage,
    copyToClipboard,
    regenerateMessage,
  };
}
