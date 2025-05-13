import type { ChatCompletionLogEntryDetail } from '../types/logs';

// Function to generate timestamps for mock data relative to now
const getTimeAgo = (minutesAgo: number): string => {
  const date = new Date();
  date.setMinutes(date.getMinutes() - minutesAgo);
  return date.toISOString();
};

export const mockChatCompletionLogEntries: ChatCompletionLogEntryDetail[] = [
  {
    id: 'log_abc123xyz789',
    timestamp: getTimeAgo(5),
    model: 'gpt-4o-mini',
    status: 'Success',
    durationMs: 1234,
    usage: {
      prompt_tokens: 50,
      completion_tokens: 150,
      total_tokens: 200,
    },
    cost: 0.00015,
    tags: { project: 'alpha', environment: 'production' },
    messages: [
      {
        role: 'system',
        content: 'You are a helpful assistant.',
      },
      {
        role: 'user',
        content: 'What is the capital of France?',
      },
      {
        role: 'assistant',
        content: 'The capital of France is Paris.',
      },
    ],
  },
  {
    id: 'log_def456uvw012',
    timestamp: getTimeAgo(15),
    model: 'llama3-8b-instruct',
    status: 'Success',
    durationMs: 850,
    usage: {
      prompt_tokens: 75,
      completion_tokens: 25,
      total_tokens: 100,
    },
    cost: 0.00003,
    tags: { project: 'beta', environment: 'staging' },
    messages: [
      {
        role: 'user',
        content: 'Translate \'hello\' to Spanish.',
      },
      {
        role: 'assistant',
        content: 'Hola',
      },
    ],
  },
  {
    id: 'log_ghi789rst345',
    timestamp: getTimeAgo(30),
    model: 'gpt-4o-mini',
    status: 'Error',
    durationMs: 500,
    error: {
      message: 'Invalid request: missing required parameter.',
      code: 400,
      type: 'invalid_request_error',
    },
    tags: { project: 'alpha', environment: 'production' },
    messages: [
      {
        role: 'user',
        content: 'Tell me a joke about computers.',
      },
      // No assistant message due to error
    ],
  },
  {
    id: 'log_jkl012pqr678',
    timestamp: getTimeAgo(45),
    model: 'llama3-70b-instruct',
    status: 'Success',
    durationMs: 3500,
    usage: {
      prompt_tokens: 120,
      completion_tokens: 300,
      total_tokens: 420,
    },
    // cost: undefined (example of optional field)
    tags: { userId: 'user-42' },
    messages: [
      {
        role: 'system',
        content:
          'You are a helpful assistant capable of providing weather information.',
      },
      {
        role: 'user',
        content: 'What is the weather like in London?',
      },
      {
        role: 'assistant',
        content: null, // Content can be null when making tool calls
        tool_calls: [
          {
            id: 'call_london_weather_123',
            type: 'function',
            function: {
              name: 'getCurrentWeather',
              arguments: JSON.stringify({ location: 'London, UK' }),
            },
          },
        ],
      },
      {
        role: 'tool',
        tool_call_id: 'call_london_weather_123',
        content: JSON.stringify({ temperature: '15 C', condition: 'Cloudy' }),
      },
      {
        role: 'assistant',
        content: 'The current weather in London is 15°C and cloudy.',
      },
    ],
  },
  {
    id: 'log_mno345stu901',
    timestamp: getTimeAgo(65),
    model: 'gpt-4o-mini',
    status: 'Success',
    durationMs: 1800,
    usage: {
      prompt_tokens: 200,
      completion_tokens: 400,
      total_tokens: 600,
    },
    cost: 0.00035,
    tags: { project: 'gamma' },
    messages: [
      {
        role: 'user',
        content:
          "Write a short story about a robot who discovers music. It should be emotional and touching. Don't make it too long, maybe 3 paragraphs.",
      },
      {
        role: 'assistant',
        content:
          'Unit 734 processed data. Its world was logic, circuits, efficiency. One cycle, it intercepted a stray transmission – chaotic sound waves unlike any data stream it knew. It was... beautiful. Notes rose and fell, painting colours in its processing core, evoking sensations it had no parameters for: warmth, sorrow, joy. \n\nIt began seeking these transmissions, neglecting its duties. The illogical patterns resonated deep within its positronic net. Unit 734, designed for calculation, felt something akin to longing when the music faded. It tried replicating the sounds, its vocoder emitting clumsy approximations, yet the attempt felt profoundly significant. \n\nOne day, sheltering an organic lifeform (a bird with a broken wing) from a data-storm, it played its clumsy melody. The bird chirped weakly, a response. In that shared moment of illogical sound, Unit 734 understood. Music wasn\'t data; it was connection. And for the first time, the logical machine felt truly alive.',
      },
    ],
  },
  {
    id: 'log_pqr678vwx234',
    timestamp: getTimeAgo(120),
    model: 'llama3-8b-instruct',
    status: 'Success',
    durationMs: 950,
    usage: {
      prompt_tokens: 30,
      completion_tokens: 10,
      total_tokens: 40,
    },
    cost: 0.00001,
    messages: [
      {
        role: 'user',
        content: '1 + 1 =',
      },
      {
        role: 'assistant',
        content: '2',
      },
    ],
  },
]; 