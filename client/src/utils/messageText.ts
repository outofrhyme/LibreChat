const MSG_TIME_PREFIX_REGEX = /^\[msg_time:\s[^\]]+\](?:\r?\n|\s)?/;

export function stripMsgTimePrefixForDisplay(text: string, isCreatedByUser: boolean): string {
  if (!isCreatedByUser) {
    return text;
  }

  return text.replace(MSG_TIME_PREFIX_REGEX, '');
}
