import LlamaStackClient from "llama-stack-client";
import OpenAI from "openai";

// export const llamaStackClient = new LlamaStackClient({
//   baseURL: process.env.NEXT_PUBLIC_LLAMA_STACK_BASE_URL,
// });

export const llamaStackClient = new OpenAI({
  apiKey: process.env.NEXT_PUBLIC_OPENAI_API_KEY,
  dangerouslyAllowBrowser: true,
});
