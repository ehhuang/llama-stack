export interface ChatMessage {
  role: string;
  content: string;
  name?: string | null;
  tool_calls?: any | null;
}

export interface Choice {
  message: ChatMessage;
  finish_reason: string;
  index: number;
  logprobs?: any | null;
}

export interface ChatCompletion {
  id: string;
  choices: Choice[];
  object: string;
  created: number;
  model: string;
  input_messages: ChatMessage[];
}
