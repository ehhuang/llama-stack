import LlamaStackClient from "llama-stack-client";

export const llamaStackClient = new LlamaStackClient({
  baseURL: process.env.NEXT_PUBLIC_LLAMA_STACK_BASE_URL,
});
