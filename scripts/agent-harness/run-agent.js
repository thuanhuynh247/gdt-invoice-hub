import { Agent } from "../../scratch/skawld-sdk/dist/sdk.js";
import {
  OpenAIChatCompletionsProvider,
  AnthropicProvider,
} from "../../scratch/skawld-sdk/dist/providers/index.js";
import { InMemorySessionStore } from "../../scratch/skawld-sdk/dist/sessions/memory.js";
import { defaultTools } from "../../scratch/skawld-sdk/dist/tools/index.js";

async function main() {
  const providerType = process.env.AGENT_PROVIDER || "gemini";
  const modelName = process.env.AGENT_MODEL || "gemini-2.5-flash";
  const goal = process.env.AGENT_GOAL || "Hello agent, what is your model name?";
  const storyId = process.env.AGENT_STORY_ID || "";

  console.log(JSON.stringify({
    type: "status",
    message: `Starting Agent Harness run... Provider: ${providerType}, Model: ${modelName}`
  }));

  let provider;

  try {
    if (providerType === "gemini") {
      const apiKey = process.env.GEMINI_API_KEY;
      if (!apiKey) {
        throw new Error("GEMINI_API_KEY environment variable is not set.");
      }
      provider = new OpenAIChatCompletionsProvider({
        apiKey,
        baseURL: "https://generativelanguage.googleapis.com/v1beta/openai/",
      });
    } else if (providerType === "openai") {
      const apiKey = process.env.OPENAI_API_KEY;
      if (!apiKey) {
        throw new Error("OPENAI_API_KEY environment variable is not set.");
      }
      provider = new OpenAIChatCompletionsProvider({ apiKey });
    } else if (providerType === "anthropic") {
      const apiKey = process.env.ANTHROPIC_API_KEY;
      if (!apiKey) {
        throw new Error("ANTHROPIC_API_KEY environment variable is not set.");
      }
      provider = new AnthropicProvider({ apiKey });
    } else {
      throw new Error(`Unsupported provider: ${providerType}`);
    }

    const agent = new Agent({
      provider,
      model: modelName,
      sessionStore: new InMemorySessionStore(),
      tools: defaultTools(),
      permissions: { mode: "yolo" },
    });

    console.log(JSON.stringify({
      type: "status",
      message: "Agent instance created. Starting session..."
    }));

    const session = await agent.session();

    console.log(JSON.stringify({
      type: "status",
      message: "Session started. Running goal..."
    }));

    for await (const event of session.run(goal)) {
      // Print event as structured JSON line
      console.log(JSON.stringify({
        type: "event",
        event: event
      }));
    }

    console.log(JSON.stringify({
      type: "status",
      message: "Agent run completed successfully."
    }));

    await agent.close();
  } catch (error) {
    console.error(JSON.stringify({
      type: "error",
      message: error.message,
      stack: error.stack
    }));
    process.exit(1);
  }
}

main();
