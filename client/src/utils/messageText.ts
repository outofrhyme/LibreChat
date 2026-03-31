const MSG_TIME_PREFIX_REGEX = /^\[msg_time:\s[^\]]+\]\s/;

export const stripMsgTimePrefixForDisplay = (text: string, isCreatedByUser: boolean) => {
  if (!isCreatedByUser) {
    return text;
  }

  return text.replace(MSG_TIME_PREFIX_REGEX, '');
};
